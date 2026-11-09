from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.brand_rules import CANONICAL_RULES, CLASSIFICATIONS, PENDING_REVIEW
from app.data.brand_source import SOURCE_BRANDS
from app.models import KIND_BRAND, KIND_CLASSIFICATION, Brand, BrandAlias
from app.services.text import slugify


@dataclass
class ImportReport:
    entries: int = 0
    brands_created: int = 0
    brands_existing: int = 0
    aliases_created: int = 0
    aliases_existing: int = 0
    merges: list[dict] = field(default_factory=list)
    corrections: list[dict] = field(default_factory=list)
    classifications: list[str] = field(default_factory=list)
    pending_review: list[str] = field(default_factory=list)

    def as_text(self) -> str:
        lines = [
            f"Entradas de origen: {self.entries}",
            f"Registros: {self.brands_created} creados, {self.brands_existing} existentes",
            f"Alias: {self.aliases_created} creados, {self.aliases_existing} existentes",
            "Fusiones:",
            *(f"  {m['canonical']} <- {', '.join(m['sources'])}" for m in self.merges),
            "Correcciones de ortografía:",
            *(f"  {c['canonical']} <- {', '.join(c['sources'])}" for c in self.corrections),
            f"Clasificaciones (fuera del directorio público): {', '.join(self.classifications)}",
            f"Pendientes de revisión: {', '.join(self.pending_review)}",
        ]
        return "\n".join(lines)


def run_import(db: Session) -> ImportReport:
    """Creates what is missing and never touches existing rows, so editorial changes survive."""
    rules = {source: rule for rule in CANONICAL_RULES for source in rule.sources}
    report = ImportReport(
        entries=len(SOURCE_BRANDS),
        merges=[
            {"canonical": rule.canonical, "sources": list(rule.sources)}
            for rule in CANONICAL_RULES
            if len(rule.sources) > 1
        ],
        corrections=[
            {"canonical": rule.canonical, "sources": list(rule.sources)}
            for rule in CANONICAL_RULES
            if len(rule.sources) == 1
        ],
        classifications=list(CLASSIFICATIONS),
        pending_review=list(PENDING_REVIEW),
    )
    seen_slugs: set[str] = set()

    for position, source in enumerate(SOURCE_BRANDS, start=1):
        rule = rules.get(source)
        canonical = rule.canonical if rule else source
        slug = (rule.slug if rule else None) or slugify(canonical)

        brand = db.scalar(select(Brand).where(Brand.slug == slug))
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            if brand is None:
                report.brands_created += 1
            else:
                report.brands_existing += 1
        if brand is None:
            brand = Brand(
                name=canonical,
                original_name=source,
                slug=slug,
                kind=KIND_CLASSIFICATION if source in CLASSIFICATIONS else KIND_BRAND,
            )
            db.add(brand)
            db.flush()

        alias = db.scalar(select(BrandAlias).where(BrandAlias.source_position == position))
        if alias is None:
            db.add(
                BrandAlias(
                    brand_id=brand.id,
                    alias=source,
                    slug=slugify(source),
                    source_position=position,
                    is_original=True,
                )
            )
            db.flush()
            report.aliases_created += 1
        elif alias.alias != source or alias.brand_id != brand.id:
            raise ValueError(
                f"Alias en posición {position} ({alias.alias!r}) no coincide con "
                f"{source!r} -> {canonical!r}; corrige los datos antes de reimportar"
            )
        else:
            report.aliases_existing += 1

    return report
