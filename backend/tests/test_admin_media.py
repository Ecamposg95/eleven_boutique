"""The image pipeline, /media serving, gallery operations and photo matching."""

import io
import struct
import zlib
from pathlib import Path

import pytest
from PIL import Image
from PIL.ExifTags import Base as ExifTag
from sqlalchemy import select

from app.models import MediaAsset, Product, ProductVariant
from app.services.admin.images import MAX_SIDE, sanitize_filename
from tests.admin_helpers import BASE, ORIGIN, image_bytes, login, make_user, upload, upload_one
from tests.factories import make_brand, make_category, make_product


@pytest.fixture
def client(db, public_client):
    login(public_client, make_user(db))
    return public_client


def media_root(client) -> Path:
    return client.app.state.settings.resolved_media_root


def stored_files(client) -> list[Path]:
    root = media_root(client)
    return list(root.iterdir()) if root.exists() else []


def bomb_png(width: int, height: int) -> bytes:
    """A valid PNG header declaring huge dimensions: rejected without decoding any pixel."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00" * 1024))
        + chunk(b"IEND", b"")
    )


# --- Accepted formats ------------------------------------------------------------------


@pytest.mark.parametrize(
    "fmt,suffix,content_type",
    [("JPEG", ".jpg", "image/jpeg"), ("PNG", ".png", "image/png"), ("WEBP", ".webp", "image/webp")],
)
def test_valid_images_are_stored_under_a_random_name(client, fmt, suffix, content_type):
    response = upload(client, ("foto original.bin", image_bytes(fmt)))
    assert response.status_code == 201, response.text
    item = response.json()["items"][0]
    assert item["content_type"] == content_type
    assert item["url"].startswith("/media/") and item["url"].endswith(suffix)
    assert "original" not in item["url"]
    assert item["filename"] == "foto original.bin"
    served = client.get(item["url"])
    assert served.status_code == 200
    assert served.headers["content-type"] == content_type
    assert served.headers["x-content-type-options"] == "nosniff"


def test_multi_picture_jpeg_is_accepted_as_jpeg(client):
    source = io.BytesIO()
    frames = [Image.new("RGB", (16, 16), color) for color in ("red", "blue")]
    frames[0].save(source, format="MPO", save_all=True, append_images=frames[1:])
    item = upload(client, ("camara.jpg", source.getvalue())).json()["items"][0]
    assert item["content_type"] == "image/jpeg"
    image, _ = read_stored(client, item["url"])
    assert image.format == "JPEG"


def test_several_files_in_one_request_with_a_partial_failure(client):
    response = upload(client, ("a.jpg", image_bytes()), ("b.jpg", b"not an image"))
    assert response.status_code == 201
    body = response.json()
    assert [item["filename"] for item in body["items"]] == ["a.jpg"]
    assert body["errors"][0]["filename"] == "b.jpg"
    assert body["errors"][0]["code"] == "invalid_image"


# --- Rejections ------------------------------------------------------------------------


def assert_rejected(client, name, data, status, code):
    response = upload(client, (name, data))
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    assert stored_files(client) == []


def test_non_image_with_a_jpg_name_is_rejected(client):
    assert_rejected(client, "foto.jpg", b"#!/bin/sh\necho hola\n" * 20, 422, "invalid_image")


def test_svg_is_rejected_whatever_its_name(client):
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert_rejected(client, "foto.svg", svg, 422, "invalid_image")
    assert_rejected(client, "foto.jpg", svg, 422, "invalid_image")


@pytest.mark.parametrize("fmt", ["GIF", "BMP", "TIFF"])
def test_other_real_image_formats_are_rejected(client, fmt):
    assert_rejected(client, "foto.jpg", image_bytes(fmt), 422, "invalid_image")


def test_truncated_image_is_rejected(client):
    data = image_bytes(size=(400, 400))
    assert_rejected(client, "foto.jpg", data[: len(data) // 2], 422, "invalid_image")


def test_oversized_file_is_rejected(client):
    data = image_bytes() + b"\x00" * (20 * 1024 * 1024)
    assert_rejected(client, "foto.jpg", data, 413, "file_too_large")


def test_image_over_60_megapixels_is_rejected(client):
    assert_rejected(client, "foto.png", bomb_png(8000, 8000), 413, "image_too_large")


def test_decompression_bomb_is_rejected_without_decoding(client):
    assert_rejected(client, "foto.png", bomb_png(60000, 60000), 413, "image_too_large")


def test_no_file_is_rejected(client):
    response = client.post(f"{BASE}/media", data={"a": "b"}, headers=ORIGIN)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "no_files"


# --- Paths -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("../../etc/passwd.jpg", "passwd.jpg"),
        ("..\\..\\windows\\system32\\foto.jpg", "foto.jpg"),
        ("/etc/shadow", "shadow"),
        ("....", "imagen"),
        ("", "imagen"),
        (None, "imagen"),
        (".htaccess", "htaccess"),
        ("fo\x00to\n.jpg", "fo_to_.jpg"),
        ('<img src=x onerror="a">.jpg', "_img src_x onerror__a__.jpg"),
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


def test_path_traversal_in_the_filename_stays_inside_media_root(client, tmp_path):
    response = upload(client, ("../../../escapa.jpg", image_bytes()))
    assert response.status_code == 201
    item = response.json()["items"][0]
    assert item["filename"] == "escapa.jpg"
    assert ".." not in item["url"]
    files = stored_files(client)
    assert len(files) == 1 and files[0].name == item["url"].removeprefix("/media/")
    assert not list(tmp_path.parent.glob("escapa*")) and not list(tmp_path.glob("escapa*"))


@pytest.mark.parametrize(
    "path",
    ["/media/../eleven.db", "/media/..%2f..%2feleven.db", "/media/%2e%2e/%2e%2e/.env", "/media/.env"],
)
def test_static_serving_does_not_escape_the_folder(client, path):
    upload_one(client)
    assert client.get(path).status_code == 404


def test_static_serving_ignores_files_the_pipeline_did_not_write(client):
    upload_one(client)
    (media_root(client) / "nota.html").write_text("<script></script>")
    assert client.get("/media/nota.html").status_code == 404


def test_storage_refuses_keys_it_did_not_generate(tmp_path):
    from app.services.admin.storage import LocalStorage

    storage = LocalStorage(tmp_path)
    for key in ("../x.jpg", "a/b.jpg", "x.svg", "0" * 32 + ".html"):
        with pytest.raises(ValueError):
            storage.save(key, b"x", "image/jpeg")


# --- Rewriting -------------------------------------------------------------------------


def exif_image(orientation: int = 6) -> bytes:
    exif = Image.Exif()
    exif[ExifTag.Orientation] = orientation
    exif[ExifTag.Make] = "CamaraSecreta"
    exif[ExifTag.Artist] = "PersonaSecreta"
    gps = exif.get_ifd(ExifTag.GPSInfo)
    gps[1] = "N"
    return image_bytes(size=(64, 32), exif=exif)


def read_stored(client, url: str) -> tuple[Image.Image, bytes]:
    raw = client.get(url).content
    return Image.open(io.BytesIO(raw)), raw


def test_exif_is_stripped_and_orientation_applied(client):
    source = exif_image()
    assert b"CamaraSecreta" in source
    item = upload(client, ("foto.jpg", source)).json()["items"][0]
    image, raw = read_stored(client, item["url"])
    assert b"CamaraSecreta" not in raw and b"PersonaSecreta" not in raw
    assert not dict(image.getexif())
    assert "exif" not in image.info
    # Orientation 6 rotates the 64x32 source a quarter turn.
    assert image.size == (32, 64)
    assert (item["width"], item["height"]) == (32, 64)


def test_png_text_metadata_is_stripped(client):
    from PIL.PngImagePlugin import PngInfo

    info = PngInfo()
    info.add_text("Comment", "NotaSecreta")
    item = upload(client, ("a.png", image_bytes("PNG", pnginfo=info))).json()["items"][0]
    image, raw = read_stored(client, item["url"])
    assert b"NotaSecreta" not in raw
    assert "Comment" not in image.info


def test_large_image_is_reduced_to_the_maximum_side(client):
    item = upload(client, ("a.jpg", image_bytes(size=(3000, 1500)))).json()["items"][0]
    assert (item["width"], item["height"]) == (MAX_SIDE, 1200)


def test_transparency_survives_in_png(client):
    source = io.BytesIO()
    Image.new("RGBA", (8, 8), (10, 20, 30, 0)).save(source, format="PNG")
    item = upload(client, ("a.png", source.getvalue())).json()["items"][0]
    image, _ = read_stored(client, item["url"])
    assert image.mode == "RGBA" and image.getpixel((0, 0))[3] == 0


# --- Library ---------------------------------------------------------------------------


def catalog_refs(db):
    brand = make_brand(db, "Marca Foto")
    category = make_category(db, "Categoria Foto")
    db.commit()
    return brand, category


def test_list_search_and_unused_filter(db, client):
    used = upload_one(client, "usada.jpg")
    free = upload_one(client, "libre.jpg")
    brand, category = catalog_refs(db)
    product = make_product(db, brand, category, "Pieza Foto")
    db.commit()
    assert (
        client.post(
            f"{BASE}/products/{product.id}/media",
            json={"media_asset_id": used["id"]},
            headers=ORIGIN,
        ).status_code
        == 201
    )
    everything = client.get(f"{BASE}/media").json()
    assert everything["total"] == 2
    assert {item["id"]: item["in_use"] for item in everything["items"]} == {
        used["id"]: True,
        free["id"]: False,
    }
    assert [i["id"] for i in client.get(f"{BASE}/media?unused=true").json()["items"]] == [free["id"]]
    assert [i["id"] for i in client.get(f"{BASE}/media?unused=false").json()["items"]] == [used["id"]]
    assert [i["id"] for i in client.get(f"{BASE}/media?q=libre").json()["items"]] == [free["id"]]


def test_alt_update(client):
    item = upload_one(client)
    response = client.patch(f"{BASE}/media/{item['id']}", json={"alt": "Texto"}, headers=ORIGIN)
    assert response.status_code == 200
    assert response.json()["alt"] == "Texto"


def test_unused_media_can_be_deleted_with_its_file(client):
    item = upload_one(client)
    assert len(stored_files(client)) == 1
    assert client.delete(f"{BASE}/media/{item['id']}", headers=ORIGIN).status_code == 204
    assert stored_files(client) == []
    assert client.get(item["url"]).status_code == 404


def test_media_in_a_gallery_cannot_be_deleted_until_unlinked(db, client):
    item = upload_one(client)
    brand, category = catalog_refs(db)
    product = make_product(db, brand, category, "Pieza Foto")
    db.commit()
    linked = client.post(
        f"{BASE}/products/{product.id}/media", json={"media_asset_id": item["id"]}, headers=ORIGIN
    ).json()
    response = client.delete(f"{BASE}/media/{item['id']}", headers=ORIGIN)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "media_in_use"
    assert len(stored_files(client)) == 1

    link = next(m for m in linked["media"] if m["media_asset_id"] == item["id"])
    assert (
        client.delete(f"{BASE}/products/{product.id}/media/{link['id']}", headers=ORIGIN).status_code
        == 200
    )
    assert client.delete(f"{BASE}/media/{item['id']}", headers=ORIGIN).status_code == 204


@pytest.mark.parametrize("kind", ["brand", "collection", "lookbook_cover", "lookbook_block", "hero"])
def test_media_used_elsewhere_cannot_be_deleted(db, client, kind):
    item = upload_one(client)
    brand, _ = catalog_refs(db)
    calls = {
        "brand": ("PATCH", f"/brands/{brand.id}", {"logo_asset_id": item["id"]}),
        "collection": ("POST", "/collections", {"title": "C", "cover_asset_id": item["id"]}),
        "lookbook_cover": ("POST", "/lookbooks", {"title": "L", "cover_asset_id": item["id"]}),
        "lookbook_block": (
            "POST",
            "/lookbooks",
            {"title": "L", "blocks": [{"type": "image", "url": item["url"], "alt": "a"}]},
        ),
        "hero": ("PATCH", "/settings", {"hero_mobile_asset_id": item["id"]}),
    }
    method, path, body = calls[kind]
    assert client.request(method, BASE + path, json=body, headers=ORIGIN).status_code in (200, 201)
    assert client.delete(f"{BASE}/media/{item['id']}", headers=ORIGIN).status_code == 409


# --- Gallery ---------------------------------------------------------------------------


@pytest.fixture
def bare_product(db):
    brand, category = catalog_refs(db)
    product = Product(
        sku="GAL-1", slug="gal-1", name="Galería", brand_id=brand.id, category_id=category.id
    )
    db.add(product)
    db.commit()
    return product


def add(client, product, item, **extra):
    return client.post(
        f"{BASE}/products/{product.id}/media",
        json={"media_asset_id": item["id"], **extra},
        headers=ORIGIN,
    )


def test_first_photo_is_primary_and_alt_defaults(client, bare_product):
    first = add(client, bare_product, upload_one(client)).json()["media"]
    assert first[0]["is_primary"] is True and first[0]["alt"] == "Galería"
    second = add(client, bare_product, upload_one(client), alt="Detalle").json()["media"]
    assert [m["is_primary"] for m in second] == [True, False]
    assert second[1]["alt"] == "Detalle"


def test_gallery_alt_is_edited_on_the_link_only(client, bare_product):
    item = upload_one(client)
    link = add(client, bare_product, item).json()["media"][0]
    url = f"{BASE}/products/{bare_product.id}/media/{link['id']}"
    response = client.patch(url, json={"alt": "Vista de frente"}, headers=ORIGIN)
    assert response.status_code == 200
    assert response.json()["media"][0]["alt"] == "Vista de frente"
    listed = client.get(f"{BASE}/media").json()["items"]
    assert next(m for m in listed if m["id"] == item["id"])["alt"] == item["alt"]


def test_gallery_alt_rejects_a_link_from_another_product(db, client, bare_product):
    other = Product(
        sku="GAL-2",
        slug="gal-2",
        name="Otra",
        brand_id=bare_product.brand_id,
        category_id=bare_product.category_id,
    )
    db.add(other)
    db.commit()
    link = add(client, other, upload_one(client)).json()["media"][0]
    url = f"{BASE}/products/{bare_product.id}/media/{link['id']}"
    assert client.patch(url, json={"alt": "x"}, headers=ORIGIN).status_code == 404


def test_the_same_asset_cannot_be_linked_twice(client, bare_product):
    item = upload_one(client)
    add(client, bare_product, item)
    response = add(client, bare_product, item)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "already_linked"


def test_linking_a_missing_asset_fails(client, bare_product):
    response = add(client, bare_product, {"id": "00000000-0000-4000-8000-000000000000"})
    assert response.status_code == 422


def test_reorder_and_set_primary(client, bare_product):
    add(client, bare_product, upload_one(client))
    add(client, bare_product, upload_one(client))
    media = add(client, bare_product, upload_one(client)).json()["media"]
    ids = [m["id"] for m in media]
    order = [ids[2], ids[0], ids[1]]
    response = client.patch(
        f"{BASE}/products/{bare_product.id}/media",
        json={"order": order, "primary_id": ids[1]},
        headers=ORIGIN,
    )
    assert response.status_code == 200, response.text
    result = response.json()["media"]
    assert [m["id"] for m in result] == order
    assert [m["position"] for m in result] == [0, 1, 2]
    assert [m["id"] for m in result if m["is_primary"]] == [ids[1]]


@pytest.mark.parametrize("variant", ["missing", "duplicate", "foreign_primary"])
def test_reorder_validates_ids(client, bare_product, variant):
    add(client, bare_product, upload_one(client))
    media = add(client, bare_product, upload_one(client)).json()["media"]
    ids = [m["id"] for m in media]
    other = "00000000-0000-4000-8000-000000000000"
    body = {
        "missing": {"order": ids[:1]},
        "duplicate": {"order": [ids[0], ids[0]]},
        "foreign_primary": {"order": ids, "primary_id": other},
    }[variant]
    response = client.patch(f"{BASE}/products/{bare_product.id}/media", json=body, headers=ORIGIN)
    assert response.status_code == 422


def test_removing_the_primary_promotes_the_next(client, bare_product):
    add(client, bare_product, upload_one(client))
    media = add(client, bare_product, upload_one(client)).json()["media"]
    response = client.delete(
        f"{BASE}/products/{bare_product.id}/media/{media[0]['id']}", headers=ORIGIN
    )
    assert [(m["id"], m["is_primary"]) for m in response.json()["media"]] == [(media[1]["id"], True)]


def test_unlink_keeps_the_file(client, bare_product):
    media = add(client, bare_product, upload_one(client)).json()["media"]
    client.delete(f"{BASE}/products/{bare_product.id}/media/{media[0]['id']}", headers=ORIGIN)
    assert len(stored_files(client)) == 1


# --- Bulk match and assign -------------------------------------------------------------


@pytest.fixture
def matchable(db):
    brand, category = catalog_refs(db)

    def product(sku, refs=(), variants=()):
        row = Product(
            sku=sku,
            slug=sku.lower(),
            name=f"Nombre {sku}",
            brand_id=brand.id,
            category_id=category.id,
            photo_refs=list(refs),
        )
        row.variants = [ProductVariant(sku=variant) for variant in variants]
        db.add(row)
        return row

    rows = {
        "sku": product("ABC-100", variants=("ABC-100-M", "ABC-100-L")),
        "ref": product("REF-1", refs=("Foto 12",)),
        "woman": product("REF-2", refs=("Foto mujer 12",)),
        "shared_a": product("SHARE-1", refs=("Foto 50",)),
        "shared_b": product("SHARE-2", refs=("Foto 50",)),
    }
    db.commit()
    return rows


def match(client, *names):
    items = [upload_one(client, name) for name in names]
    response = client.post(
        f"{BASE}/media/bulk-match",
        json={"media_asset_ids": [item["id"] for item in items]},
        headers=ORIGIN,
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


def test_match_by_sku(client, matchable):
    item = match(client, "abc-100.jpg")[0]
    assert item["match"] == "sku"
    assert item["product_id"] == str(matchable["sku"].id)
    assert [c["sku"] for c in item["candidates"]] == ["ABC-100"]
    assert set(item) == {"media_asset_id", "filename", "product_id", "match", "candidates"}


@pytest.mark.parametrize("name", ["ABC-100-M.jpg", "ABC-100_2.jpg", "ABC-100 (3).png"])
def test_match_by_variant_sku_and_numbered_copies(client, matchable, name):
    item = match(client, name)[0]
    assert (item["match"], item["product_id"]) == ("sku", str(matchable["sku"].id))


@pytest.mark.parametrize("name", ["Foto 12.jpg", "foto12.jpg", "FOTO_12 (2).jpg", "Foto 12-1.jpg"])
def test_match_by_photo_ref(client, matchable, name):
    item = match(client, name)[0]
    assert (item["match"], item["product_id"]) == ("photo_ref", str(matchable["ref"].id))


def test_photo_ref_distinguishes_mujer(client, matchable):
    item = match(client, "Foto mujer 12.jpg")[0]
    assert item["product_id"] == str(matchable["woman"].id)


def test_ambiguous_ref_stays_unassigned_and_lists_candidates(client, matchable):
    item = match(client, "Foto 50.jpg")[0]
    assert item["match"] == "none"
    assert item["product_id"] is None
    assert {c["sku"] for c in item["candidates"]} == {"SHARE-1", "SHARE-2"}


def test_filename_with_two_refs_of_different_products_is_ambiguous(client, matchable):
    item = match(client, "Foto 12+50.jpg")[0]
    assert item["product_id"] is None and len(item["candidates"]) == 3


def test_no_match(client, matchable):
    item = match(client, "IMG_0001.jpg")[0]
    assert (item["match"], item["product_id"], item["candidates"]) == ("none", None, [])


def test_foto_number_prefix_does_not_partially_match(client, matchable):
    assert match(client, "Foto 123.jpg")[0]["match"] == "none"


def test_archived_products_are_not_proposed(db, client, matchable):
    matchable["ref"].status = "archived"
    db.commit()
    assert match(client, "Foto 12.jpg")[0]["match"] == "none"


def test_match_saves_nothing(db, client, matchable):
    match(client, "abc-100.jpg")
    db.expire_all()
    assert db.get(Product, matchable["sku"].id).media == []


def test_bulk_assign_is_per_item_and_idempotent(db, client, matchable):
    item = upload_one(client, "x.jpg")
    missing = "00000000-0000-4000-8000-000000000000"
    target = str(matchable["sku"].id)
    body = {
        "items": [
            {"media_asset_id": item["id"], "product_id": target},
            {"media_asset_id": item["id"], "product_id": target},
            {"media_asset_id": missing, "product_id": target},
            {"media_asset_id": item["id"], "product_id": missing},
        ]
    }
    response = client.post(f"{BASE}/media/bulk-assign", json=body, headers=ORIGIN)
    assert response.status_code == 200
    assert [row["ok"] for row in response.json()["results"]] == [True, True, False, False]
    db.expire_all()
    media = db.get(Product, matchable["sku"].id).media
    assert len(media) == 1 and media[0].is_primary
    assert db.scalar(select(MediaAsset.url).where(MediaAsset.id == media[0].media_asset_id))
