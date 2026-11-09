import pytest
from sqlalchemy import func, select

from app.data.brand_source import SOURCE_BRANDS
from app.models import (
    KIND_BRAND,
    KIND_CLASSIFICATION,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    VALIDATION_PENDING,
    Brand,
    BrandAlias,
)
from app.services.brand_import import run_import

NEVER_MERGED = [
    "Asaali",
    "Asali Jean",
    "Thierry Mugler",
    "Pali",
    "Steve McQueen",
    "Subhuman",
    "Unfathomable",
    "VSTAR 2",
]

CANONICAL = {
    "A Bathing Ape": "A Bathing Ape / BAPE",
    "BAPE": "A Bathing Ape / BAPE",
    "Ami Alexandre Mattiussi": "AMI Paris",
    "Ami Paris": "AMI Paris",
    "Ferragamo": "Ferragamo",
    "Salvatore Ferragamo": "Ferragamo",
    "Canadá Goose": "Canada Goose",
}


def count(db, *criteria, model=Brand) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*criteria))


def test_source_is_the_89_entries_in_order():
    assert len(SOURCE_BRANDS) == 89
    assert SOURCE_BRANDS[0] == "A Bathing Ape"
    assert SOURCE_BRANDS[14] == "BAPE"
    assert SOURCE_BRANDS[-1] == "Zegna"
    assert len(set(SOURCE_BRANDS)) == 89


def test_import_counts(db):
    run_import(db)
    db.commit()
    assert count(db, model=BrandAlias) == 89
    positions = db.scalars(select(BrandAlias.source_position)).all()
    assert sorted(positions) == list(range(1, 90))
    assert count(db) == 86
    assert count(db, Brand.kind == KIND_BRAND) == 85
    assert count(db, Brand.kind == KIND_CLASSIFICATION) == 1


def test_second_run_creates_nothing_and_says_so(db):
    first = run_import(db)
    db.commit()
    second = run_import(db)
    db.commit()
    assert first.brands_created == 86 and first.aliases_created == 89
    assert second.brands_created == 0 and second.aliases_created == 0
    assert second.brands_existing == 86 and second.aliases_existing == 89
    assert count(db) == 86
    assert count(db, model=BrandAlias) == 89


def test_second_run_does_not_undo_editorial_changes(db):
    run_import(db)
    prada = db.scalar(select(Brand).where(Brand.slug == "prada"))
    prada.status = STATUS_PUBLISHED
    db.commit()
    run_import(db)
    db.commit()
    db.refresh(prada)
    assert prada.status == STATUS_PUBLISHED


def test_every_source_name_resolves_to_its_final_record(db):
    run_import(db)
    db.commit()
    for position, source_name in enumerate(SOURCE_BRANDS, start=1):
        alias = db.scalar(select(BrandAlias).where(BrandAlias.source_position == position))
        assert alias.alias == source_name
        assert alias.is_original is True
        assert alias.brand.name == CANONICAL.get(source_name, source_name)


def test_canonical_slugs_and_merged_originals(db):
    run_import(db)
    db.commit()
    bape = db.scalar(select(Brand).where(Brand.slug == "a-bathing-ape"))
    assert bape.name == "A Bathing Ape / BAPE"
    assert bape.original_name == "A Bathing Ape"
    assert {a.alias for a in bape.aliases} == {"A Bathing Ape", "BAPE"}
    assert db.scalar(select(Brand).where(Brand.slug == "ami-paris")).name == "AMI Paris"
    assert db.scalar(select(Brand).where(Brand.slug == "ferragamo")).name == "Ferragamo"
    goose = db.scalar(select(Brand).where(Brand.slug == "canada-goose"))
    assert goose.name == "Canada Goose" and goose.original_name == "Canadá Goose"


def test_nothing_is_auto_published(db):
    run_import(db)
    db.commit()
    assert count(db, Brand.status != STATUS_DRAFT) == 0
    assert count(db, Brand.validation_status != VALIDATION_PENDING) == 0


@pytest.mark.parametrize("name", NEVER_MERGED)
def test_never_merged_names_stay_independent_and_pending(db, name):
    report = run_import(db)
    db.commit()
    brand = db.scalar(select(Brand).where(Brand.name == name))
    assert [a.alias for a in brand.aliases] == [name]
    assert name in report.pending_review


def test_report_lists_merges_corrections_and_classification(db):
    report = run_import(db)
    merges = {merge["canonical"]: merge["sources"] for merge in report.merges}
    assert merges == {
        "A Bathing Ape / BAPE": ["A Bathing Ape", "BAPE"],
        "AMI Paris": ["Ami Alexandre Mattiussi", "Ami Paris"],
        "Ferragamo": ["Ferragamo", "Salvatore Ferragamo"],
    }
    assert report.corrections == [{"canonical": "Canada Goose", "sources": ["Canadá Goose"]}]
    assert report.entries == 89
    assert report.classifications == ["Sin marca"]
    assert "89" in report.as_text()
    assert "Asali Jean" in report.as_text()


def test_alias_pointing_at_the_wrong_brand_aborts(db):
    run_import(db)
    wrong = db.scalar(select(Brand).where(Brand.slug == "prada"))
    alias = db.scalar(select(BrandAlias).where(BrandAlias.alias == "BAPE"))
    alias.brand_id = wrong.id
    db.commit()
    with pytest.raises(ValueError, match="BAPE"):
        run_import(db)
