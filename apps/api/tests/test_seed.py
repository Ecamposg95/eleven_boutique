import json
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from eleven.catalog.models import Product, Variant
from eleven.seed import SeedError, load_demo_catalog
from eleven.tenancy import Tenant
from tests.conftest import FIXTURE


def _counts(session: Session) -> tuple[int, int]:
    return (
        session.scalar(select(func.count()).select_from(Product)) or 0,
        session.scalar(select(func.count()).select_from(Variant)) or 0,
    )


def test_reseeding_does_not_duplicate(engine: Engine) -> None:
    with Session(engine) as session:
        before = _counts(session)
        load_demo_catalog(session, FIXTURE)
        session.flush()
        assert _counts(session) == before
        session.rollback()


def test_refuses_to_seed_a_real_tenant(engine: Engine, tmp_path: Path) -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    data["tenant"]["is_demo"] = False
    path = tmp_path / "real.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with Session(engine) as session, pytest.raises(SeedError):
        load_demo_catalog(session, path)


def test_refuses_to_overwrite_existing_real_tenant(engine: Engine, tmp_path: Path) -> None:
    with Session(engine) as session:
        session.add(Tenant(slug="eleven", name="Eleven", is_demo=False))
        session.flush()
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["tenant"]["slug"] = "eleven"
        path = tmp_path / "eleven.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(SeedError):
            load_demo_catalog(session, path)
        session.rollback()
