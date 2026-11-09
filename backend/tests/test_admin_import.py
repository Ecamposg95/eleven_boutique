"""Catalog import. All data here is invented. The poisoned fixture mirrors the shape of a real
point-of-sale export: every forbidden value is unique, so any leak is detectable by search."""

import csv
import io
import re
import sqlite3
import time
import uuid
import zipfile
from datetime import timedelta
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import select, text

from app.models import (
    IMPORT_COMPLETED,
    IMPORT_EXPIRED,
    AuditLog,
    Category,
    ImportRun,
    Product,
    ProductVariant,
)
from app.models.base import utcnow
from app.services.admin.catalog_import import base_sku, extract_photo_refs
from tests.admin_helpers import BASE, ORIGIN, image_bytes, login, make_user, upload_one
from tests.factories import make_alias, make_brand, make_category

PREVIEW = f"{BASE}/imports/products/preview"
COMMIT = f"{BASE}/imports/products"

POISON_PRICE = "987654.32"
POISON_COST = "876543.21"
POISON_STOCK = 7654321
POISON_BARCODE = "7500000099887"
POISON_TIER = "654321.09"
POISON_HISTORY = "Familia del histórico: 2 ventas, precios de $3,141 a $5,926"
POISON_DESCRIPTION = f"Pieza clásica de temporada. {POISON_HISTORY}. Bodega norte."
POISON_VALUES = (
    POISON_PRICE,
    POISON_COST,
    str(POISON_STOCK),
    POISON_BARCODE,
    POISON_TIER,
    "3,141",
    "5,926",
    "Familia del histórico",
    "ventas",
    "Bodega norte",
    "temporada",
    "Pieza clásica",
)

FULL_HEADER = [
    "SKU",
    "Nombre",
    "Descripcion",
    "Unidad",
    "Departamento",
    "Marca",
    "Codigo Barras",
    "Precio Base",
    "Costo",
    "Stock",
    "Incluye IVA",
    "P1 Nombre",
    "P1 Precio",
    "E1 Barcode",
    "Color",
    "Talla",
]


def full_row(sku, name, department, brand, color=None, size=None, description=POISON_DESCRIPTION):
    return [
        sku,
        name,
        description,
        "Pieza",
        department,
        brand,
        POISON_BARCODE,
        float(POISON_PRICE),
        float(POISON_COST),
        POISON_STOCK,
        "Sí",
        "Mayoreo",
        float(POISON_TIER),
        POISON_BARCODE,
        color,
        size,
    ]


def xlsx(rows, header=FULL_HEADER, sheet="Plantilla") -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet
    worksheet.append(header)
    for row in rows:
        worksheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def csv_bytes(rows, header=("SKU", "Nombre", "Departamento", "Marca", "Color", "Talla"), **options):
    output = io.StringIO()
    writer = csv.writer(output, **options)
    writer.writerow(header)
    writer.writerows(rows)
    return output.getvalue().encode()


@pytest.fixture
def client(db, public_client):
    login(public_client, make_user(db))
    return public_client


@pytest.fixture
def catalog(db):
    casa = make_brand(db, "Casa Hermès", status="draft")
    make_alias(db, casa, "Hermes Paris")
    make_brand(db, "Otra Casa", status="draft")
    make_brand(db, "Sin marca", kind="classification")
    make_category(db, "Pantalones")
    db.commit()
    return casa


def preview(client, data: bytes, name="catalogo.xlsx"):
    return client.post(PREVIEW, files={"file": (name, data)}, headers=ORIGIN)


def ok_preview(client, data: bytes, name="catalogo.xlsx") -> dict:
    response = preview(client, data, name)
    assert response.status_code == 200, response.text
    return response.json()


def commit(client, preview_id, update_existing=False):
    return client.post(
        COMMIT, json={"preview_id": preview_id, "update_existing": update_existing}, headers=ORIGIN
    )


def run_import(client, data: bytes, name="catalogo.xlsx", update_existing=False) -> dict:
    response = commit(client, ok_preview(client, data, name)["preview_id"], update_existing)
    assert response.status_code == 200, response.text
    return response.json()


STANDARD_ROWS = [
    # Sizes of one piece, grouped through the SKU suffix.
    full_row("CAM-100-CH", "Camisa Lino", "Camisas Nuevas", "Casa Hermès", "Azul", "CH"),
    full_row("CAM-100-M", "Camisa Lino", "Camisas Nuevas", "Casa Hermès", "Azul", "M"),
    full_row("CAM-100-G", "Camisa Lino", "Camisas Nuevas", "Casa Hermès", "Azul", "G"),
    # A generic name on distinct base SKUs: separate products.
    full_row("PAN-1", "Pantalón", "Pantalones", "Casa Hermès"),
    full_row("PAN-2", "Pantalón", "Pantalones", "Casa Hermès"),
    # Size that is not a suffix: its own product.
    full_row("POL-7-PLAY", "Polo", "Pantalones", "Otra Casa", "Rojo", "Ch"),
    # No brand.
    full_row("X-9", "Pieza Suelta", "Pantalones", None),
    full_row("X-10", "Otra Suelta", "pantalones", "SIN MARCA"),
]


# --- Grouping --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sku,size,expected",
    [
        ("ABC-M", "M", "ABC"),
        ("ABC-m", "M", "ABC"),
        ("ABC-Ch", "ch", "ABC"),
        ("ABC - M", "M", "ABC"),
        ("ABC-12.5", "12.5", "ABC"),
        ("ABC", None, "ABC"),
        ("ABC-PLAY", "Ch", "ABC-PLAY"),
        ("ABC-XM", "M", "ABC-XM"),
        ("-M", "M", "-M"),
        ("M", "M", "M"),
    ],
)
def test_base_sku(sku, size, expected):
    assert base_sku(sku, size) == expected


def test_preview_counts_and_groups(client, catalog):
    body = ok_preview(client, xlsx(STANDARD_ROWS))
    assert body["rows"] == 8
    assert body["variants"] == 8
    assert body["products"] == 6
    assert body["new_products"] == 6
    assert body["conflicts"] == 0
    assert body["new_categories"] == ["Camisas Nuevas"]
    assert body["errors"] == []
    first = body["sample"][0]
    assert first == {
        "sku": "CAM-100",
        "name": "Camisa Lino",
        "brand": "Casa Hermès",
        "category": "Camisas Nuevas",
        "variants": 3,
    }


def test_preview_writes_nothing_to_the_catalog(db, client, catalog):
    categories = len(db.scalars(select(Category)).all())
    ok_preview(client, xlsx(STANDARD_ROWS))
    db.expire_all()
    assert db.scalars(select(Product)).all() == []
    assert db.scalars(select(ProductVariant)).all() == []
    assert len(db.scalars(select(Category)).all()) == categories


def test_commit_creates_drafts_with_grouped_variants(db, client, catalog):
    result = run_import(client, xlsx(STANDARD_ROWS))
    assert result["created"] == 6
    assert (result["updated"], result["skipped"], result["errors"]) == (0, 0, 0)

    products = {product.sku: product for product in db.scalars(select(Product))}
    assert set(products) == {"CAM-100", "PAN-1", "PAN-2", "POL-7-PLAY", "X-9", "X-10"}
    for product in products.values():
        assert product.status == "draft"
        assert product.is_demo is False
        assert product.published_at is None

    shirt = products["CAM-100"]
    assert shirt.slug == "casa-hermes-camisa-lino"
    assert {(v.sku, v.size, v.color) for v in shirt.variants} == {
        ("CAM-100-CH", "CH", "Azul"),
        ("CAM-100-M", "M", "Azul"),
        ("CAM-100-G", "G", "Azul"),
    }
    # Same generic name, distinct products, slug with suffix.
    assert {products["PAN-1"].slug, products["PAN-2"].slug} == {
        "casa-hermes-pantalon",
        "casa-hermes-pantalon-2",
    }
    assert products["X-9"].brand.slug == "sin-marca"
    assert products["X-9"].slug == "pieza-suelta"
    assert products["X-10"].category.slug == "pantalones"

    category = db.scalar(select(Category).where(Category.name == "Camisas Nuevas"))
    assert category.parent_id is None


def test_imported_products_stay_hidden_publicly(client, catalog):
    run_import(client, xlsx(STANDARD_ROWS))
    assert client.get("/api/v1/products").json()["total"] == 0


def test_brand_resolves_by_alias_ignoring_accents_and_case(db, client, catalog):
    rows = [
        full_row("A-1", "Uno", "Pantalones", "casa hermes"),
        full_row("A-2", "Dos", "Pantalones", "HERMES PARÍS"),
    ]
    assert run_import(client, xlsx(rows))["created"] == 2
    assert {p.brand_id for p in db.scalars(select(Product))} == {catalog.id}


def test_unknown_brand_is_a_row_error_and_never_created(db, client, catalog):
    brands_before = client.get(f"{BASE}/brands").json()["total"]
    rows = [
        full_row("A-1", "Uno", "Pantalones", "Marca Inventada"),
        full_row("A-2", "Dos", "Pantalones", "Casa Hermès"),
    ]
    body = ok_preview(client, xlsx(rows))
    assert body["errors"] == [
        {"row": 2, "sku": "A-1", "message": "Marca desconocida: Marca Inventada"}
    ]
    assert body["products"] == 1
    assert commit(client, body["preview_id"]).json()["errors"] == 1
    assert client.get(f"{BASE}/brands").json()["total"] == brands_before
    assert [p.sku for p in db.scalars(select(Product))] == ["A-2"]


def test_new_category_matches_existing_ignoring_accents(client, catalog):
    rows = [full_row("A-1", "Uno", "PANTALÓNES", "Casa Hermès")]
    assert ok_preview(client, xlsx(rows))["new_categories"] == []


def test_row_errors(client, catalog):
    rows = [
        full_row(None, "Sin SKU", "Pantalones", "Casa Hermès"),
        full_row("A-1", None, "Pantalones", "Casa Hermès"),
        full_row("A-2", "Sin depto", None, "Casa Hermès"),
        full_row("A-3", "Bien", "Pantalones", "Casa Hermès"),
        full_row("A-3", "Repetido", "Pantalones", "Casa Hermès"),
        full_row("A-4", "N" * 301, "Pantalones", "Casa Hermès"),
    ]
    body = ok_preview(client, xlsx(rows))
    assert [(e["row"], e["message"]) for e in body["errors"]] == [
        (2, "SKU vacío"),
        (3, "Nombre vacío"),
        (4, "Departamento vacío"),
        (6, "SKU repetido en el archivo"),
        (7, "Nombre demasiado largo"),
    ]
    assert body["products"] == 1


def test_same_base_with_another_brand_is_an_error(client, catalog):
    rows = [
        full_row("A-M", "Uno", "Pantalones", "Casa Hermès", size="M"),
        full_row("A-G", "Otro", "Pantalones", "Otra Casa", size="G"),
    ]
    body = ok_preview(client, xlsx(rows))
    assert body["errors"][0]["message"] == "SKU base repetido con otra marca"
    assert body["products"] == 1


def test_numeric_cells_become_text(db, client, catalog):
    rows = [full_row(12345, "Número", "Pantalones", "Casa Hermès", size=38.0)]
    rows.append(full_row("12345-40", "Número", "Pantalones", "Casa Hermès", size=40))
    run_import(client, xlsx(rows))
    products = db.scalars(select(Product)).all()
    assert {v.size for p in products for v in p.variants} == {"38", "40"}
    assert {v.sku for p in products for v in p.variants} == {"12345", "12345-40"}
    assert len(products) == 1


# --- Photo references ------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Foto 12", ["Foto 12"]),
        ("Foto 12+13+14", ["Foto 12", "Foto 13", "Foto 14"]),
        ("Foto mujer 5", ["Foto mujer 5"]),
        ("Pieza. Foto 3. Precio $3,500. Foto mujer 4+5", ["Foto 3", "Foto mujer 4", "Foto mujer 5"]),
        ("Foto 3 y Foto 3", ["Foto 3"]),
        (POISON_DESCRIPTION, []),
        ("Fotografía 12", []),
        ("Foto de la pieza", []),
        ('="Foto 1"', []),
        ("", []),
        (None, []),
    ],
)
def test_extract_photo_refs(text, expected):
    assert extract_photo_refs(text) == expected


def test_refs_are_stored_and_the_rest_of_descripcion_is_not(db, client, catalog):
    rows = [
        full_row(
            "A-M",
            "Uno",
            "Pantalones",
            "Casa Hermès",
            size="M",
            description=f"Foto 12+13 {POISON_HISTORY}",
        ),
        full_row(
            "A-G",
            "Uno",
            "Pantalones",
            "Casa Hermès",
            size="G",
            description=f"{POISON_HISTORY} Foto mujer 4",
        ),
    ]
    run_import(client, xlsx(rows))
    assert db.scalar(select(Product)).photo_refs == ["Foto 12", "Foto 13", "Foto mujer 4"]


def test_imported_refs_drive_photo_matching(client, catalog):
    rows = [full_row("A-1", "Uno", "Pantalones", "Casa Hermès", description="Foto 77")]
    run_import(client, xlsx(rows))
    item = upload_one(client, "Foto 77.jpg")
    match = client.post(
        f"{BASE}/media/bulk-match", json={"media_asset_ids": [item["id"]]}, headers=ORIGIN
    ).json()["items"][0]
    assert match["match"] == "photo_ref"


# --- The critical rule: nothing commercial gets in -------------------------------------


def dump_database(database_url: str) -> str:
    """Every cell of every table, as text, read directly from the file. Only the admin's Argon2
    hash is left out: its salt is random text with `$` separators that can look like money."""
    connection = sqlite3.connect(database_url.removeprefix("sqlite:///"))
    chunks = []
    tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    assert "products" in tables
    for table in tables:
        cursor = connection.execute(f'SELECT * FROM "{table}"')
        names = [column[0] for column in cursor.description]
        for row in cursor:
            cells = (str(cell) for name, cell in zip(names, row) if name != "password_hash")
            chunks.append(" | ".join(cells))
    connection.close()
    return "\n".join(chunks)


def assert_clean(text: str, where: str) -> None:
    for value in POISON_VALUES:
        assert value not in text, f"{value!r} leaked into {where}"
    assert not re.search(r"\$\s*\d", text), f"money leaked into {where}"


def test_poisoned_workbook_leaves_no_trace(db, client, catalog, database_url):
    response = preview(client, xlsx(STANDARD_ROWS))
    assert response.status_code == 200
    assert_clean(response.text, "the preview response")

    # While the preview is pending too: the staged rows are in the database at this point.
    assert_clean(dump_database(database_url), "the database during preview")

    preview_id = response.json()["preview_id"]
    result = commit(client, preview_id)
    assert result.status_code == 200
    assert_clean(result.text, "the commit response")

    dumped = dump_database(database_url)
    assert "CAM-100-CH" in dumped  # The dump really does contain the import.
    assert_clean(dumped, "the database after commit")

    report = client.get(f"{BASE}/imports/{preview_id}/report")
    assert report.status_code == 200
    assert_clean(report.text, "the report")

    for path in ("/products?page_size=60", "/audit"):
        assert_clean(client.get(BASE + path).text, path)


def test_poison_in_an_error_row_leaves_no_trace(db, client, catalog, database_url):
    rows = [full_row("A-1", "Uno", "Pantalones", "Marca Inventada")]
    response = preview(client, xlsx(rows))
    assert_clean(response.text, "the preview response")
    commit(client, response.json()["preview_id"])
    assert_clean(dump_database(database_url), "the database")


def test_poisoned_csv_leaves_no_trace(client, catalog, database_url):
    rows = [full_row("A-1", "Uno", "Pantalones", "Casa Hermès")]
    response = preview(client, csv_bytes(rows, header=FULL_HEADER), "catalogo.csv")
    assert response.status_code == 200, response.text
    assert_clean(response.text, "the preview response")
    commit(client, response.json()["preview_id"])
    assert_clean(dump_database(database_url), "the database")


def test_schema_has_no_commercial_columns(db, database_url):
    connection = sqlite3.connect(database_url.removeprefix("sqlite:///"))
    for table in ("products", "product_variants", "import_runs"):
        columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
        for column in columns:
            assert not re.search("price|precio|cost|stock|barcode|barras|iva", column), column
    connection.close()


def test_preview_response_has_only_the_contract_fields(client, catalog):
    body = ok_preview(client, xlsx(STANDARD_ROWS))
    assert set(body) == {
        "preview_id",
        "rows",
        "products",
        "variants",
        "new_products",
        "conflicts",
        "new_categories",
        "errors",
        "sample",
    }


def test_staged_rows_hold_only_allow_listed_keys(db, client, catalog):
    body = ok_preview(client, xlsx(STANDARD_ROWS))
    run = db.get(ImportRun, uuid.UUID(body["preview_id"]))
    assert {key for row in run.payload["rows"] for key in row} == {
        "row",
        "sku",
        "name",
        "department",
        "brand",
        "color",
        "size",
        "refs",
        "formula",
    }


# --- Formula and malformed content -----------------------------------------------------


def test_formula_cells_are_data_and_never_stored(db, client, catalog, database_url):
    rows = [
        full_row("A-1", "=HYPERLINK(\"http://evil.example\",\"x\")", "Pantalones", "Casa Hermès"),
        full_row("=1+1", "Dos", "Pantalones", "Casa Hermès"),
        full_row("A-3", "Tres", "Pantalones", "Casa Hermès", description='="Foto 9"'),
    ]
    body = ok_preview(client, xlsx(rows))
    assert [e["row"] for e in body["errors"]] == [2, 3]
    assert "evil.example" not in str(body)
    commit(client, body["preview_id"])
    dumped = dump_database(database_url)
    assert "evil.example" not in dumped and "=1+1" not in dumped
    assert db.scalar(select(Product)).photo_refs == []


def test_csv_formula_cells_are_rejected_too(client, catalog):
    rows = [["=cmd|' /C calc'!A0", "Uno", "Pantalones", "Casa Hermès", "", ""]]
    body = ok_preview(client, csv_bytes(rows), "catalogo.csv")
    assert body["errors"][0]["sku"] is None
    assert body["products"] == 0


def test_report_neutralizes_spreadsheet_formulas(client, catalog):
    rows = [["+1-SKU", "Uno", "Pantalones", "Casa Hermès", "", ""]]
    preview_id = ok_preview(client, csv_bytes(rows), "catalogo.csv")["preview_id"]
    commit(client, preview_id)
    report = client.get(f"{BASE}/imports/{preview_id}/report").text
    assert "'+1-SKU" in report


def zip_bomb() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/worksheets/sheet1.xml", b"\x00" * (220 * 1024 * 1024))
    return output.getvalue()


def test_zip_bomb_is_rejected_before_decompressing(client, catalog):
    data = zip_bomb()
    assert len(data) < 1024 * 1024
    started = time.perf_counter()
    response = preview(client, data)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_file"
    assert time.perf_counter() - started < 2


def test_high_ratio_entry_is_rejected_even_under_the_total_limit(client, catalog):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/sharedStrings.xml", b"a" * (50 * 1024 * 1024))
    assert preview(client, output.getvalue()).status_code == 422


def test_zip_with_too_many_entries_is_rejected(client, catalog):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for index in range(1001):
            archive.writestr(f"f{index}", b"x")
    assert preview(client, output.getvalue()).status_code == 422


@pytest.mark.parametrize(
    "name,data",
    [
        ("catalogo.xlsx", b"esto no es un zip"),
        ("catalogo.xlsx", b"PK\x03\x04roto"),
        ("catalogo.csv", b"PK\x03\x04roto"),
        ("catalogo.xls", b"antiguo"),
        ("catalogo.pdf", b"%PDF"),
        ("catalogo", b"sin extension"),
    ],
)
def test_wrong_files_are_rejected(client, catalog, name, data):
    response = preview(client, data, name)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_file"


def test_zip_that_is_not_a_workbook_is_rejected(client, catalog):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("hola.txt", "hola")
    response = preview(client, output.getvalue())
    assert response.status_code == 422


def test_file_over_20_mb_is_rejected(client, catalog):
    response = preview(client, b"SKU,Nombre\n" + b"x" * (20 * 1024 * 1024 + 1), "catalogo.csv")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_body_far_over_the_limit_is_rejected_up_front(client, catalog):
    response = preview(client, b"x" * (22 * 1024 * 1024), "catalogo.csv")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "body_too_large"


def test_missing_required_columns(client, catalog):
    response = preview(client, csv_bytes([["A"]], header=("SKU",)), "catalogo.csv")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_template"
    assert "nombre" in response.json()["error"]["message"]


def test_too_many_rows(client, catalog, monkeypatch):
    monkeypatch.setattr("app.services.admin.catalog_import.MAX_ROWS", 2)
    rows = [["A", "B", "C", "D", "", ""]] * 3
    response = preview(client, csv_bytes(rows), "catalogo.csv")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "too_many_rows"


def test_empty_rows_do_not_count_toward_the_row_limit(client, catalog, monkeypatch):
    monkeypatch.setattr("app.services.admin.catalog_import.MAX_ROWS", 1)
    rows = [[None] * len(FULL_HEADER)] * 5 + [full_row("A-1", "Uno", "Pantalones", "Casa Hermès")]
    body = ok_preview(client, xlsx(rows))
    assert (body["rows"], body["products"]) == (1, 1)


def test_no_file_in_the_request(client):
    response = client.post(PREVIEW, data={"a": "b"}, headers=ORIGIN)
    assert response.status_code == 422


# --- CSV template ----------------------------------------------------------------------


def test_template_downloads_and_round_trips(db, client, catalog):
    response = client.get(f"{BASE}/imports/template")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    header = response.text.lstrip("﻿").strip()
    assert header == "SKU,Nombre,Departamento,Marca,Color,Talla,Descripcion"

    body = (
        response.text
        + "T-100-M,Vestido,Pantalones,Casa Hermès,Negro,M,Foto 8\n"
        + "T-100-G,Vestido,Pantalones,Casa Hermès,Negro,G,\n"
    )
    assert run_import(client, body.encode(), "plantilla.csv")["created"] == 1
    product = db.scalar(select(Product))
    assert product.sku == "T-100"
    assert len(product.variants) == 2
    assert product.photo_refs == ["Foto 8"]


def test_csv_with_semicolons_and_latin1(db, client, catalog):
    rows = [["A-1", "Camisón", "Pantalones", "Casa Hermes", "", ""]]
    data = csv_bytes(rows, delimiter=";").decode().encode("cp1252")
    assert run_import(client, data, "catalogo.csv")["created"] == 1
    assert db.scalar(select(Product)).name == "Camisón"


# --- Conflicts and idempotence ---------------------------------------------------------


def test_reimport_creates_nothing(db, client, catalog):
    data = xlsx(STANDARD_ROWS)
    run_import(client, data)
    products = len(db.scalars(select(Product)).all())
    variants = len(db.scalars(select(ProductVariant)).all())
    categories = len(db.scalars(select(Category)).all())

    body = ok_preview(client, data)
    assert (body["new_products"], body["conflicts"], body["new_categories"]) == (0, 6, [])

    for update_existing in (False, True):
        result = run_import(client, data, update_existing=update_existing)
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["skipped"] == 6

    db.expire_all()
    assert len(db.scalars(select(Product)).all()) == products
    assert len(db.scalars(select(ProductVariant)).all()) == variants
    assert len(db.scalars(select(Category)).all()) == categories


def test_conflict_is_skipped_without_update_existing(db, client, catalog):
    run_import(client, xlsx([full_row("A-1", "Original", "Pantalones", "Casa Hermès")]))
    result = run_import(client, xlsx([full_row("A-1", "Cambiado", "Pantalones", "Casa Hermès")]))
    assert (result["created"], result["updated"], result["skipped"]) == (0, 0, 1)
    assert db.scalar(select(Product)).name == "Original"


def test_update_existing_touches_catalog_data_only(db, client, catalog):
    first = [full_row("A-M", "Original", "Pantalones", "Casa Hermès", "Azul", "M")]
    run_import(client, xlsx(first))
    product = db.scalar(select(Product))
    item = upload_one(client)
    path = f"{BASE}/products/{product.id}"
    client.post(f"{path}/media", json={"media_asset_id": item["id"]}, headers=ORIGIN)
    client.patch(
        path,
        json={
            "status": "published",
            "publish_brand": True,
            "slug": "slug-editado",
            "seo_title": "SEO editado",
            "internal_notes": "Nota editada",
            "is_featured": True,
        },
        headers=ORIGIN,
    )

    second = [
        full_row("A-M", "Renombrado", "Categoria Otra", "Otra Casa", "Verde", "M"),
        full_row("A-G", "Renombrado", "Categoria Otra", "Otra Casa", "Verde", "G"),
    ]
    result = run_import(client, xlsx(second), update_existing=True)
    assert (result["created"], result["updated"], result["skipped"]) == (0, 1, 0)

    db.expire_all()
    product = db.scalar(select(Product))
    assert product.name == "Renombrado"
    assert product.search_text.startswith("renombrado")
    assert product.brand.name == "Otra Casa"
    assert product.category.name == "Categoria Otra"
    assert {(v.sku, v.color) for v in product.variants} == {("A-M", "Verde"), ("A-G", "Verde")}
    # Untouched.
    assert product.status == "published"
    assert product.slug == "slug-editado"
    assert product.seo_title == "SEO editado"
    assert product.internal_notes == "Nota editada"
    assert product.is_featured is True
    assert len(product.media) == 1


def test_variant_sku_owned_by_another_product_is_an_error(db, client, catalog):
    run_import(client, xlsx([full_row("A-M", "Uno", "Pantalones", "Casa Hermès", size="M")]))
    body = ok_preview(client, xlsx([full_row("A-M", "Dos", "Pantalones", "Casa Hermès")]))
    assert body["errors"][0]["message"] == "El SKU ya es variante de otra pieza"


# --- Preview lifecycle -----------------------------------------------------------------


def test_commit_clears_the_staged_rows(db, client, catalog):
    body = ok_preview(client, xlsx(STANDARD_ROWS))
    run_id = uuid.UUID(body["preview_id"])
    assert db.get(ImportRun, run_id).payload is not None
    commit(client, body["preview_id"])
    db.expire_all()
    run = db.get(ImportRun, run_id)
    assert run.status == IMPORT_COMPLETED
    assert run.payload is None
    # Really SQL NULL, not the JSON value `null`.
    stored = db.execute(text("SELECT count(*) FROM import_runs WHERE payload IS NOT NULL")).scalar()
    assert stored == 0


def test_the_uploaded_file_is_not_written_to_disk(client, catalog, tmp_path: Path):
    ok_preview(client, xlsx(STANDARD_ROWS))
    assert not list(tmp_path.rglob("*.xlsx"))


def test_a_preview_commits_once(client, catalog):
    body = ok_preview(client, xlsx(STANDARD_ROWS))
    assert commit(client, body["preview_id"]).status_code == 200
    second = commit(client, body["preview_id"])
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "preview_already_used"


def test_expired_preview_cannot_commit_and_is_purged(db, client, catalog):
    body = ok_preview(client, xlsx(STANDARD_ROWS))
    run_id = uuid.UUID(body["preview_id"])
    run = db.get(ImportRun, run_id)
    assert timedelta(minutes=25) < run.expires_at - utcnow() <= timedelta(minutes=30)
    run.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()

    response = commit(client, body["preview_id"])
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "preview_expired"
    db.expire_all()
    run = db.get(ImportRun, run_id)
    assert run.status == IMPORT_EXPIRED
    assert run.payload is None
    assert db.scalars(select(Product)).all() == []


def test_a_new_preview_purges_old_expired_ones(db, client, catalog):
    old = ok_preview(client, xlsx(STANDARD_ROWS))
    run = db.get(ImportRun, uuid.UUID(old["preview_id"]))
    run.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    ok_preview(client, xlsx(STANDARD_ROWS))
    db.expire_all()
    assert db.get(ImportRun, uuid.UUID(old["preview_id"])).payload is None


def test_unknown_preview_is_404(client):
    assert commit(client, str(uuid.uuid4())).status_code == 404


def test_commit_uses_the_database_as_it_is_now(db, client, catalog):
    body = ok_preview(client, xlsx([full_row("A-1", "Uno", "Pantalones", "Casa Hermès")]))
    run_import(client, xlsx([full_row("A-1", "Antes", "Pantalones", "Casa Hermès")]))
    result = commit(client, body["preview_id"]).json()
    assert (result["created"], result["skipped"]) == (0, 1)


def test_report_lists_each_row(client, catalog):
    rows = [*STANDARD_ROWS[:3], full_row("Z-1", "Mala", "Pantalones", "Marca Inventada")]
    preview_id = ok_preview(client, xlsx(rows))["preview_id"]
    commit(client, preview_id)
    response = client.get(f"{BASE}/imports/{preview_id}/report")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    parsed = list(csv.DictReader(io.StringIO(response.text.lstrip("﻿"))))
    assert [(r["fila"], r["sku"], r["resultado"]) for r in parsed] == [
        ("2", "CAM-100-CH", "created"),
        ("3", "CAM-100-M", "created"),
        ("4", "CAM-100-G", "created"),
        ("5", "Z-1", "error"),
    ]


def test_report_before_commit_is_409(client, catalog):
    preview_id = ok_preview(client, xlsx(STANDARD_ROWS))["preview_id"]
    assert client.get(f"{BASE}/imports/{preview_id}/report").status_code == 409
    assert client.get(f"{BASE}/imports/{uuid.uuid4()}/report").status_code == 404


def test_import_is_audited_once_with_counts(db, client, catalog):
    run_import(client, xlsx(STANDARD_ROWS))
    rows = db.scalars(select(AuditLog).where(AuditLog.operation == "import")).all()
    assert len(rows) == 1
    assert rows[0].changes["created"] == [None, 6]


def test_large_catalog_finishes_quickly(db, client, catalog):
    rows = []
    for index in range(800):
        for size in ("CH", "M", "G"):
            rows.append(
                full_row(f"BIG-{index}-{size}", "Pantalón", "Pantalones", "Casa Hermès", size=size)
            )
    data = xlsx(rows)
    started = time.perf_counter()
    result = run_import(client, data)
    assert result["created"] == 800
    assert time.perf_counter() - started < 8


def test_image_upload_is_not_accepted_as_a_catalog(client, catalog):
    assert preview(client, image_bytes(), "foto.jpg").status_code == 422
