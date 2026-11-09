import pytest
from fastapi import APIRouter


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/products/no-existe",
        "/api/v1/brands/no-existe",
        "/api/v1/collections/no-existe",
        "/api/v1/lookbooks/no-existe",
        "/api/v1/ruta-desconocida",
        "/fuera-de-la-api",
    ],
)
def test_not_found_shape(public_client, path):
    assert_error(public_client.get(path), 404, "not_found")


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/products?page=0",
        "/api/v1/products?page=x",
        "/api/v1/products?page_size=61",
        "/api/v1/products?sort=precio",
        "/api/v1/products?featured=quiza",
        "/api/v1/novedades?page_size=0",
    ],
)
def test_query_validation_shape(public_client, path):
    assert_error(public_client.get(path), 422, "validation_error")


def test_body_validation_shape(public_client):
    assert_error(public_client.post("/api/v1/events", json={}), 422, "validation_error")
    malformed = public_client.post(
        "/api/v1/events", content="{no json", headers={"Content-Type": "application/json"}
    )
    assert_error(malformed, 422, "validation_error")


def test_method_not_allowed_shape(public_client):
    assert_error(public_client.delete("/api/v1/products"), 405, "method_not_allowed")


def test_unexpected_error_shape_hides_the_detail(public_client):
    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise RuntimeError("secreto interno")

    public_client.app.include_router(router)
    response = public_client.get("/boom")
    assert_error(response, 500, "internal_error")
    assert "secreto" not in response.text


def test_page_size_limit_of_60_is_accepted(public_client):
    assert public_client.get("/api/v1/products?page_size=60").json()["page_size"] == 60
