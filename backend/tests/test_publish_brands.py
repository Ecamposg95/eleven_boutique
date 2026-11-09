from sqlalchemy import func, select

from app.models import (
    KIND_CLASSIFICATION,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    AuditLog,
    Brand,
    BrandAlias,
)
from app.services.text import slugify
from scripts.publish_brands import run
from tests.factories import make_brand


def draft(db, name: str, **fields) -> Brand:
    brand = make_brand(db, name, status=STATUS_DRAFT, **fields)
    db.add(BrandAlias(brand_id=brand.id, alias=name, slug=f"alias-{slugify(name)}", is_original=True))
    db.flush()
    return brand


def statuses(db) -> dict[str, str]:
    return dict(db.execute(select(Brand.name, Brand.status)).all())


def seed(db) -> None:
    draft(db, "Hermès")
    draft(db, "Chanel")
    # Renamed after import: still recognised as pending by its original alias.
    draft(db, "Thierry Mugler").name = "Mugler"
    draft(db, "Sin marca", kind=KIND_CLASSIFICATION)
    make_brand(db, "Archivada", status=STATUS_ARCHIVED)
    make_brand(db, "Prada", status=STATUS_PUBLISHED)
    db.commit()


def test_dry_run_changes_nothing(db):
    seed(db)
    report = run(db, apply=False)
    db.commit()
    assert sorted(report.published) == ["Chanel", "Hermès"]
    assert report.pending == ["Mugler"]
    assert statuses(db)["Hermès"] == STATUS_DRAFT
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 0


def test_apply_publishes_drafts_and_skips_pending_classifications_and_archived(db):
    seed(db)
    report = run(db, apply=True)
    db.commit()
    assert sorted(report.published) == ["Chanel", "Hermès"]
    assert report.already_published == 1
    assert report.archived == 1
    assert statuses(db) == {
        "Hermès": STATUS_PUBLISHED,
        "Chanel": STATUS_PUBLISHED,
        "Mugler": STATUS_DRAFT,
        "Sin marca": STATUS_DRAFT,
        "Archivada": STATUS_ARCHIVED,
        "Prada": STATUS_PUBLISHED,
    }
    rows = db.scalars(select(AuditLog)).all()
    assert len(rows) == 2
    assert {row.changes["status"][1] for row in rows} == {STATUS_PUBLISHED}
    assert all(row.entity == "brand" and row.user_id is None for row in rows)


def test_second_run_publishes_nothing(db):
    seed(db)
    run(db, apply=True)
    db.commit()
    report = run(db, apply=True)
    db.commit()
    assert report.published == []
    assert report.already_published == 3
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 2
