import os
from collections.abc import Iterator
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from eleven.catalog.models import ChannelListing, Product, PublicationStatus, Variant
from eleven.config import REPO_ROOT, Settings, get_settings
from eleven.db import get_session
from eleven.main import create_app
from eleven.seed import load_demo_catalog
from eleven.tenancy import Tenant

API_DIR = REPO_ROOT / "apps" / "api"
FIXTURE = REPO_ROOT / "fixtures" / "demo" / "catalog.json"


def _test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or Settings().test_database_url
    if not url:
        url = "postgresql+psycopg://eleven:eleven@localhost:5433/eleven_test"
    if not url.rsplit("/", 1)[-1].endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL debe apuntar a una base *_test")
    return url


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = _test_database_url()
    eng = create_engine(url)
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")

    with Session(eng) as session, session.begin():
        load_demo_catalog(session, FIXTURE)
        _seed_other_tenant(session)
    yield eng
    eng.dispose()


def _seed_other_tenant(session: Session) -> None:
    """Segundo tenant con un slug repetido y un producto propio, para probar aislamiento."""
    other = Tenant(slug="otro", name="Otra tienda", is_demo=True)
    session.add(other)
    session.flush()
    for slug, name in (("blusa-de-manga-larga", "SECRETO otro tenant"), ("solo-otro", "Solo otro")):
        product = Product(
            tenant_id=other.id,
            slug=slug,
            name=name,
            category="blusas",
            status=PublicationStatus.published,
        )
        session.add(product)
        session.flush()
        session.add(
            Variant(tenant_id=other.id, product_id=product.id, sku=f"OTRO-{slug}", size="M")
        )
        session.add(
            ChannelListing(
                tenant_id=other.id,
                product_id=product.id,
                status=PublicationStatus.published,
                price=Decimal("1.00"),
            )
        )


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", tenant_slug="demo", catalog_page_max=48)


@pytest.fixture
def client(engine: Engine, settings: Settings) -> Iterator[TestClient]:
    app = create_app()

    def session_override() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    with Session(engine) as session:
        yield session
