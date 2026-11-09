import io
from functools import lru_cache

from PIL import Image
from sqlalchemy.orm import Session

from app.models import ROLE_ADMIN, AdminUser
from app.services.admin.auth import hash_password

ORIGIN = {"Origin": "http://localhost:3000"}
PASSWORD = "contrasena-de-prueba-123"
BASE = "/api/v1/admin"


@lru_cache
def _password_hash() -> str:
    return hash_password(PASSWORD)  # Argon2 is slow on purpose; once per test run is enough.


def make_user(db: Session, role: str = ROLE_ADMIN, email: str | None = None) -> AdminUser:
    user = AdminUser(
        email=email or f"{role}@eleven.example", password_hash=_password_hash(), role=role
    )
    db.add(user)
    db.commit()
    return user


def login(client, user: AdminUser):
    response = client.post(
        f"{BASE}/auth/login", json={"email": user.email, "password": PASSWORD}, headers=ORIGIN
    )
    assert response.status_code == 200, response.text
    return response


def image_bytes(fmt: str = "JPEG", size=(32, 24), color=(120, 40, 40), **save) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format=fmt, **save)
    return output.getvalue()


def upload(client, *files: tuple[str, bytes]):
    return client.post(
        f"{BASE}/media",
        files=[("files", (name, data, "application/octet-stream")) for name, data in files],
        headers=ORIGIN,
    )


def upload_one(client, name: str = "foto.jpg") -> dict:
    response = upload(client, (name, image_bytes()))
    assert response.status_code == 201, response.text
    return response.json()["items"][0]
