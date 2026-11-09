import shutil
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import BASE_DIR, Settings
from app.db import make_engine, make_session_factory
from app.main import create_app


def alembic_config(database_url: str) -> Config:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.attributes["database_url"] = database_url
    config.attributes["skip_logging"] = True
    return config


@pytest.fixture(scope="session")
def migrated_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The real Alembic migration, applied once; each test gets a copy of the result."""
    path = tmp_path_factory.mktemp("template") / "template.db"
    command.upgrade(alembic_config(f"sqlite:///{path}"), "head")
    return path


@pytest.fixture
def database_url(migrated_template: Path, tmp_path: Path) -> str:
    path = tmp_path / "test.db"
    shutil.copy(migrated_template, path)
    return f"sqlite:///{path}"


@pytest.fixture
def db(database_url: str) -> Iterator[Session]:
    engine = make_engine(database_url)
    with make_session_factory(engine)() as session:
        yield session
    engine.dispose()


@pytest.fixture
def make_settings(database_url: str, tmp_path: Path) -> Callable[..., Settings]:
    def build(**overrides) -> Settings:
        # _env_file=None: backend/.env must never influence a test.
        values = {
            "database_url": database_url,
            "demo_mode": False,
            "whatsapp_number": "",
            "public_site_url": "https://eleven.example",
            "cors_origins": "http://localhost:3000",
            "app_env": "production",
            "media_root": str(tmp_path / "media"),
        }
        return Settings(_env_file=None, **{**values, **overrides})

    return build


@pytest.fixture
def make_client(make_settings) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def build(**overrides) -> TestClient:
        # Server errors must come back as responses so their shape can be asserted.
        # https: the admin session cookie is Secure and httpx would not send it back otherwise.
        client = TestClient(
            create_app(make_settings(**overrides)),
            base_url="https://testserver",
            raise_server_exceptions=False,
        )
        clients.append(client)
        return client

    yield build
    for client in clients:
        client.close()
        client.app.state.engine.dispose()


@pytest.fixture
def public_client(make_client) -> TestClient:
    return make_client(demo_mode=False)


@pytest.fixture
def demo_client(make_client) -> TestClient:
    return make_client(demo_mode=True)
