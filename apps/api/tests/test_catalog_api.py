from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from eleven.catalog.models import Variant
from eleven.config import Settings
from eleven.tenancy import Tenant

PUBLISHED_DEMO = 30  # 32 en fixtures: 1 draft y 1 archived no son públicos


def _all_slugs(client: TestClient, **params: object) -> list[str]:
    slugs: list[str] = []
    cursor = None
    while True:
        query = {**params, **({"cursor": cursor} if cursor else {})}
        page = client.get("/api/v1/catalog/products", params=query).json()
        slugs += [item["slug"] for item in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            return slugs


def test_only_published_products_are_listed(client: TestClient) -> None:
    page = client.get("/api/v1/catalog/products").json()
    assert page["total"] == PUBLISHED_DEMO
    slugs = _all_slugs(client)
    assert "bolso-tote" not in slugs  # draft
    assert "vestido-de-noche-satinado" not in slugs  # archived
    assert client.get("/api/v1/catalog/products/bolso-tote").status_code == 404
    assert client.get("/api/v1/catalog/products/vestido-de-noche-satinado").status_code == 404


def test_other_tenant_is_never_visible(client: TestClient, db: Session) -> None:
    slugs = _all_slugs(client)
    assert "solo-otro" not in slugs
    assert client.get("/api/v1/catalog/products/solo-otro").status_code == 404

    shared = client.get("/api/v1/catalog/products/blusa-de-manga-larga").json()
    assert shared["name"] == "Blusa de manga larga"

    other_variant = db.scalar(
        select(Variant.id).join(Tenant, Tenant.id == Variant.tenant_id).where(Tenant.slug == "otro")
    )
    response = client.get(f"/api/v1/catalog/variants/{other_variant}/availability")
    assert response.status_code == 404

    facets = client.get("/api/v1/catalog/facets").json()
    assert sum(c["count"] for c in facets["categories"]) == PUBLISHED_DEMO


def test_tenant_comes_from_server_config_not_client(client: TestClient) -> None:
    response = client.get(
        "/api/v1/catalog/products/solo-otro",
        params={"tenant_id": "otro", "tenant": "otro"},
        headers={"X-Tenant": "otro"},
    )
    assert response.status_code == 404


def test_pagination_walks_every_product_once(client: TestClient) -> None:
    for sort in ("new", "name", "price_asc", "price_desc"):
        slugs = _all_slugs(client, limit=7, sort=sort)
        assert len(slugs) == PUBLISHED_DEMO
        assert len(set(slugs)) == PUBLISHED_DEMO


def test_limit_is_capped_and_cursor_validated(client: TestClient, settings: Settings) -> None:
    settings.catalog_page_max = 5
    page = client.get("/api/v1/catalog/products", params={"limit": 500}).json()
    assert len(page["items"]) == 5

    assert client.get("/api/v1/catalog/products", params={"cursor": "basura"}).status_code == 400
    cursor = page["next_cursor"]
    wrong_sort = client.get("/api/v1/catalog/products", params={"cursor": cursor, "sort": "name"})
    assert wrong_sort.status_code == 400


def test_missing_price_is_null_never_zero(client: TestClient) -> None:
    product = client.get("/api/v1/catalog/products/blusa-con-hombros-descubiertos").json()
    assert product["price_from"] is None
    assert all(v["price"] is None for v in product["variants"])

    by_price = client.get("/api/v1/catalog/products", params={"sort": "price_asc", "limit": 48})
    items = by_price.json()["items"]
    priced = [i for i in items if i["price_from"] is not None]
    assert [Decimal(i["price_from"]) for i in priced] == sorted(
        Decimal(i["price_from"]) for i in priced
    )
    assert all(i["price_from"] is None for i in items[len(priced) :])


def test_variant_price_overrides_product_price(client: TestClient) -> None:
    product = client.get("/api/v1/catalog/products/saco-oversize").json()
    assert product["price_varies"] is True
    prices = {v["size"]: Decimal(v["price"]) for v in product["variants"]}
    assert prices["XG"] == prices["M"] + 100
    assert Decimal(product["price_from"]) == prices["M"]


def test_filters(client: TestClient) -> None:
    uni = client.get("/api/v1/catalog/products", params={"size": "UNI"}).json()
    assert uni["total"] == 3
    assert {i["category"] for i in uni["items"]} == {"accesorios"}

    multi = client.get(
        "/api/v1/catalog/products", params=[("category", "sacos"), ("category", "faldas")]
    ).json()
    assert multi["total"] == 5

    olive = client.get("/api/v1/catalog/products", params={"color": "verde olivo"}).json()
    assert all("verde olivo" in i["colors"] for i in olive["items"])

    autumn = client.get("/api/v1/catalog/products", params={"collection": "otono-demo"}).json()
    assert autumn["total"] > 0
    assert (
        client.get("/api/v1/catalog/products", params={"collection": "no-existe"}).json()["total"]
        == 0
    )

    ranged = client.get(
        "/api/v1/catalog/products", params={"price_min": 1000, "price_max": 1300}
    ).json()
    assert all(1000 <= Decimal(i["price_from"]) <= 1300 for i in ranged["items"])


def test_search_escapes_wildcards(client: TestClient) -> None:
    assert client.get("/api/v1/catalog/products", params={"q": "%"}).json()["total"] == 0
    found = client.get("/api/v1/catalog/products", params={"q": "VESTIDO"}).json()
    assert found["total"] == 5  # 6 vestidos, 1 archivado


def test_availability_is_unknown_without_authorized_source(client: TestClient) -> None:
    product = client.get("/api/v1/catalog/products/falda-lapiz").json()
    variant_id = product["variants"][0]["id"]
    availability = client.get(f"/api/v1/catalog/variants/{variant_id}/availability").json()
    assert availability["state"] == "unknown"
    assert availability["available"] is None


def test_catalog_flag_disables_public_catalog(client: TestClient, settings: Settings) -> None:
    settings.catalog_public_enabled = False
    assert client.get("/api/v1/catalog/products").status_code == 503
    assert client.get("/api/v1/health").status_code == 200


def test_site_exposes_public_config_only(client: TestClient) -> None:
    site = client.get("/api/v1/site").json()
    assert site["whatsapp_phone"] == "+525639748035"
    assert site["flags"]["checkout_enabled"] is False
    assert site["flags"]["payments_enabled"] is False
