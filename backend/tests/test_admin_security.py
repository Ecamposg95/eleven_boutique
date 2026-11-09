"""Authentication, roles, Origin, lockout, audit secrecy and scripts.create_admin."""

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import timedelta

import pytest
from fastapi.routing import iter_route_contexts
from sqlalchemy import select, text

from app.config import BASE_DIR
from app.models import (
    ROLE_ADMIN,
    ROLE_EDITOR,
    ROLE_SUPERADMIN,
    AdminSession,
    AdminUser,
    AuditLog,
    LoginAttempt,
)
from app.models.base import utcnow
from app.services.admin.auth import COOKIE_NAME
from tests.admin_helpers import BASE, ORIGIN, PASSWORD, login, make_user

PUBLIC_ADMIN_ROUTES = {("POST", f"{BASE}/auth/login")}
ADMIN_ONLY = [
    ("GET", "/settings"),
    ("PATCH", "/settings"),
    ("GET", "/audit"),
    ("POST", "/brands"),
    ("PATCH", f"/brands/{uuid.uuid4()}"),
    ("POST", "/imports/products/preview"),
    ("POST", "/imports/products"),
    ("GET", "/imports/template"),
    ("GET", f"/imports/{uuid.uuid4()}/report"),
]


def admin_routes(app):
    """Every method of every route below the admin prefix, read from the router itself."""
    for route in iter_route_contexts(app.routes):
        path = getattr(route, "path", "") or ""
        if path.startswith(BASE):
            for method in set(route.methods) - {"HEAD", "OPTIONS"}:
                yield method, path


def fill(path: str) -> str:
    return re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)


@pytest.fixture
def client(public_client):
    return public_client


def test_every_admin_route_is_401_without_a_session(client):
    routes = set(admin_routes(client.app))
    # Guards against the walk itself silently finding nothing or missing part of the tree.
    documented = {
        (method.upper(), path)
        for path, operations in client.app.openapi()["paths"].items()
        if path.startswith(BASE)
        for method in operations
    }
    assert len(routes) >= 44
    assert documented <= routes
    for method, path in routes - PUBLIC_ADMIN_ROUTES:
        response = client.request(method, fill(path), headers=ORIGIN)
        assert response.status_code == 401, f"{method} {path}: {response.status_code}"
        assert response.json()["error"]["code"] == "unauthorized"


def test_only_login_is_public(client):
    assert PUBLIC_ADMIN_ROUTES <= set(admin_routes(client.app))
    assert len(PUBLIC_ADMIN_ROUTES) == 1


def test_mutations_reject_bad_origin_on_every_route(db, client):
    login(client, make_user(db))
    for method, path in admin_routes(client.app):
        if method == "GET":
            continue
        for headers in ({"Origin": "https://evil.example"}, {}, {"Origin": "null"}):
            response = client.request(method, fill(path), headers=headers)
            assert response.status_code == 403, f"{method} {path} {headers}"
            assert response.json()["error"]["code"] == "invalid_origin"


def test_public_site_url_is_an_allowed_origin(db, make_client):
    client = make_client(public_site_url="https://eleven.example/")
    response = client.post(
        f"{BASE}/auth/login",
        json={"email": "a@b.example", "password": "x"},
        headers={"Origin": "https://eleven.example"},
    )
    assert response.status_code == 401


def test_get_does_not_need_origin(db, client):
    login(client, make_user(db))
    assert client.get(f"{BASE}/auth/me").status_code == 200


@pytest.mark.parametrize("method,path", ADMIN_ONLY)
def test_editor_is_denied_admin_routes(db, client, method, path):
    login(client, make_user(db, ROLE_EDITOR))
    response = client.request(method, BASE + path, headers=ORIGIN)
    assert response.status_code == 403, path
    assert response.json()["error"]["code"] == "forbidden"


def test_editor_reaches_catalog_routes(db, client):
    login(client, make_user(db, ROLE_EDITOR))
    for path in ("/dashboard", "/products", "/brands", "/categories", "/media", "/collections"):
        assert client.get(BASE + path).status_code == 200, path


def test_admin_and_superadmin_reach_admin_routes(db, make_client):
    for role in (ROLE_ADMIN, ROLE_SUPERADMIN):
        client = make_client()
        login(client, make_user(db, role))
        assert client.get(f"{BASE}/settings").status_code == 200
        assert client.get(f"{BASE}/audit").status_code == 200


# --- Sessions --------------------------------------------------------------------------


def set_cookie_header(response) -> str:
    return next(v for k, v in response.headers.multi_items() if k == "set-cookie")


def test_login_returns_me_and_sets_a_hardened_cookie(db, client):
    user = make_user(db)
    response = login(client, user)
    assert response.json() == {"id": str(user.id), "email": user.email, "role": user.role}
    header = set_cookie_header(response).casefold()
    assert header.startswith(f"{COOKIE_NAME}=")
    assert "httponly" in header
    assert "samesite=lax" in header
    assert "secure" in header
    assert "max-age=43200" in header
    assert "path=/" in header


def test_cookie_is_not_secure_in_development(db, make_client):
    client = make_client(app_env="development")
    assert "secure" not in set_cookie_header(login(client, make_user(db))).casefold()


def test_only_the_token_hash_is_stored(db, client):
    response = login(client, make_user(db))
    token = response.cookies[COOKIE_NAME]
    stored = db.scalars(select(AdminSession.token_hash)).all()
    assert len(stored) == 1
    assert token not in stored
    assert len(stored[0]) == 64
    assert token not in response.text


def test_logout_revokes_the_session_server_side(db, client):
    response = login(client, make_user(db))
    token = response.cookies[COOKIE_NAME]
    assert client.post(f"{BASE}/auth/logout", headers=ORIGIN).status_code == 204
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, token)  # A copied cookie must not outlive the logout.
    assert client.get(f"{BASE}/auth/me").status_code == 401


def test_expired_session_is_rejected(db, client):
    login(client, make_user(db))
    assert client.get(f"{BASE}/auth/me").status_code == 200
    session = db.scalar(select(AdminSession))
    assert timedelta(hours=11) < session.expires_at - utcnow() <= timedelta(hours=12)
    session.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert client.get(f"{BASE}/auth/me").status_code == 401


def test_deactivated_user_loses_access_at_once(db, client):
    user = make_user(db)
    login(client, user)
    user.is_active = False
    db.commit()
    assert client.get(f"{BASE}/auth/me").status_code == 401


def test_forged_cookie_is_rejected(client):
    client.cookies.set(COOKIE_NAME, "forged")
    assert client.get(f"{BASE}/auth/me").status_code == 401


# --- Lockout ---------------------------------------------------------------------------


def attempt(client, email: str, password: str):
    return client.post(
        f"{BASE}/auth/login", json={"email": email, "password": password}, headers=ORIGIN
    )


def test_unknown_email_and_wrong_password_look_the_same(db, client):
    user = make_user(db)
    wrong = attempt(client, user.email, "incorrecta")
    unknown = attempt(client, "nadie@eleven.example", "incorrecta")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_lockout_after_five_failures_blocks_even_the_right_password(db, client):
    user = make_user(db)
    for _ in range(5):
        assert attempt(client, user.email, "incorrecta").status_code == 401
    locked = attempt(client, user.email, PASSWORD)
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "too_many_attempts"
    assert int(locked.headers["Retry-After"]) > 0
    assert COOKIE_NAME not in locked.cookies


def test_lockout_applies_to_unknown_emails_too(client):
    for _ in range(5):
        assert attempt(client, "nadie@eleven.example", "x").status_code == 401
    assert attempt(client, "nadie@eleven.example", "x").status_code == 429


def test_lockout_is_per_email_and_ignores_case(db, client):
    user, other = make_user(db), make_user(db, ROLE_EDITOR)
    for _ in range(5):
        attempt(client, user.email.upper(), "incorrecta")
    assert attempt(client, user.email, PASSWORD).status_code == 429
    assert attempt(client, other.email, PASSWORD).status_code == 200


def test_lockout_ends_when_the_window_passes(db, client):
    user = make_user(db)
    for _ in range(5):
        attempt(client, user.email, "incorrecta")
    for row in db.scalars(select(LoginAttempt)):
        row.attempted_at = utcnow() - timedelta(minutes=16)
    db.commit()
    assert attempt(client, user.email, PASSWORD).status_code == 200


def test_success_resets_the_failure_count(db, client):
    user = make_user(db)
    for _ in range(4):
        attempt(client, user.email, "incorrecta")
    assert attempt(client, user.email, PASSWORD).status_code == 200
    for _ in range(4):
        assert attempt(client, user.email, "incorrecta").status_code == 401
    assert attempt(client, user.email, PASSWORD).status_code == 200


def test_login_attempts_do_not_store_the_email(db, client):
    attempt(client, "persona@eleven.example", "incorrecta")
    assert "persona" not in db.scalar(select(LoginAttempt)).email_key


# --- Audit -----------------------------------------------------------------------------


def test_audit_holds_no_secrets(db, client):
    user = make_user(db)
    token = login(client, user).cookies[COOKIE_NAME]
    client.patch(f"{BASE}/settings", json={"intro": "Hola"}, headers=ORIGIN)
    attempt(client, user.email, "contrasena-escrita-mal")
    client.post(f"{BASE}/auth/logout", headers=ORIGIN)

    rows = db.scalars(select(AuditLog)).all()
    assert {row.operation for row in rows} >= {"login", "logout", "update"}
    dumped = json.dumps(
        [[row.operation, row.entity, row.entity_id, row.user_email, row.changes] for row in rows]
    )
    for secret in (token, PASSWORD, "contrasena-escrita-mal", user.password_hash, "argon2"):
        assert secret not in dumped
    assert not re.search(r"password|token|hash", dumped, re.IGNORECASE)


def test_audit_records_who_what_and_the_change(db, client):
    user = make_user(db)
    login(client, user)
    client.patch(f"{BASE}/settings", json={"intro": "Hola"}, headers=ORIGIN)
    entries = client.get(f"{BASE}/audit?entity=site_settings").json()
    assert entries["total"] == 1
    entry = entries["items"][0]
    assert entry["user_email"] == user.email
    assert entry["operation"] == "update"
    assert entry["changes"] == {"intro": [None, "Hola"]}


def test_audit_drops_secret_fields_even_if_a_caller_passes_them(db):
    from app.services.admin import audit

    audit.record(db, None, "x", "y", None, {"password_hash": ["a", "b"], "safe": [1, 2]})
    db.commit()
    assert db.scalar(select(AuditLog)).changes == {"safe": [1, 2]}


# --- Forbidden fields ------------------------------------------------------------------


@pytest.mark.parametrize("field", ["price", "cost", "stock", "barcode", "codigo_barras"])
def test_product_endpoints_refuse_commercial_fields(db, client, field):
    login(client, make_user(db))
    response = client.patch(
        f"{BASE}/products/{uuid.uuid4()}", json={field: 100}, headers=ORIGIN
    )
    assert response.status_code == 422


def test_body_size_limit(db, client):
    login(client, make_user(db))
    response = client.post(
        f"{BASE}/products/bulk",
        content=b"x" * (3 * 1024 * 1024),
        headers={**ORIGIN, "Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "body_too_large"


def test_body_size_limit_counts_a_stream_without_content_length(db, client):
    login(client, make_user(db))

    def chunks():
        for _ in range(4):
            yield b"x" * (1024 * 1024)

    response = client.post(
        f"{BASE}/products/bulk",
        content=chunks(),
        headers={**ORIGIN, "Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "body_too_large"


def test_anonymous_upload_is_refused_before_reading_the_form(client):
    files = {"files": ("a.jpg", b"x" * 1024)}
    for path in ("/media", "/imports/products/preview"):
        response = client.post(BASE + path, files=files, headers=ORIGIN)
        assert response.status_code == 401, path


def test_editor_upload_to_import_is_refused(db, client):
    login(client, make_user(db, ROLE_EDITOR))
    response = client.post(
        f"{BASE}/imports/products/preview", files={"file": ("a.csv", b"SKU")}, headers=ORIGIN
    )
    assert response.status_code == 403


def test_admin_responses_are_not_cacheable_or_indexable(db, client):
    response = client.get(f"{BASE}/auth/me")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-robots-tag"] == "noindex"
    assert "x-robots-tag" not in client.get("/api/v1/health").headers


def test_error_shape_is_uniform_on_admin_routes(client):
    body = client.get(f"{BASE}/auth/me").json()
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message"}


# --- create_admin ----------------------------------------------------------------------


def run_create_admin(database_url: str, *args: str, password: str | None = "contrasena-larga-1"):
    env = {**os.environ, "DATABASE_URL": database_url}
    env.pop("ADMIN_PASSWORD", None)
    if password is not None:
        env["ADMIN_PASSWORD"] = password
    return subprocess.run(
        [sys.executable, "-m", "scripts.create_admin", *args],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )


def test_create_admin_creates_a_superadmin_who_can_log_in(db, database_url, client):
    result = run_create_admin(database_url, "Dueno@Eleven.Example")
    assert result.returncode == 0, result.stderr
    assert "contrasena-larga-1" not in result.stdout + result.stderr
    user = db.scalar(select(AdminUser))
    assert user.email == "dueno@eleven.example"
    assert user.role == ROLE_SUPERADMIN
    assert user.password_hash.startswith("$argon2id$")
    response = attempt(client, "dueno@eleven.example", "contrasena-larga-1")
    assert response.status_code == 200


def test_create_admin_refuses_short_password_and_duplicates(db, database_url):
    assert run_create_admin(database_url, "a@b.example", password="corta").returncode != 0
    assert db.scalar(select(AdminUser)) is None
    assert run_create_admin(database_url, "a@b.example").returncode == 0
    assert run_create_admin(database_url, "a@b.example").returncode != 0


def test_there_are_no_default_users(db):
    assert db.execute(text("SELECT count(*) FROM admin_users")).scalar() == 0
