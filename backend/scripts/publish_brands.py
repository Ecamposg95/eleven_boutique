"""python -m scripts.publish_brands [--apply]

Publishes every draft brand in one go. Leaves out the names flagged for human review on
import (PENDING_REVIEW, matched by their original alias so a later rename does not matter),
classifications such as "Sin marca", and archived brands. Without --apply it only reports.
Idempotent: a second run publishes nothing.
"""

import argparse
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.data.brand_rules import PENDING_REVIEW
from app.db import make_engine, make_session_factory
from app.models import KIND_BRAND, STATUS_ARCHIVED, STATUS_DRAFT, STATUS_PUBLISHED, Brand, BrandAlias
from app.services.admin import audit


@dataclass
class Report:
    published: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    already_published: int = 0
    archived: int = 0

    def as_text(self, apply: bool) -> str:
        verb = "Publicadas" if apply else "Se publicarían"
        lines = [f"{verb}: {len(self.published)}"]
        lines += [f"  {name}" for name in sorted(self.published)]
        lines.append(f"En borrador por revisión pendiente: {len(self.pending)}")
        lines += [f"  {name}" for name in sorted(self.pending)]
        lines.append(f"Ya publicadas: {self.already_published}")
        lines.append(f"Archivadas (sin tocar): {self.archived}")
        if not apply:
            lines.append("Simulación: nada cambió. Repita con --apply para publicar.")
        return "\n".join(lines)


def run(db: Session, *, apply: bool) -> Report:
    pending_ids = set(
        db.scalars(
            select(BrandAlias.brand_id).where(
                BrandAlias.is_original.is_(True), BrandAlias.alias.in_(PENDING_REVIEW)
            )
        )
    )
    report = Report()
    for brand in db.scalars(select(Brand).where(Brand.kind == KIND_BRAND)):
        if brand.status == STATUS_PUBLISHED:
            report.already_published += 1
        elif brand.status == STATUS_ARCHIVED:
            report.archived += 1
        elif brand.status == STATUS_DRAFT and brand.id in pending_ids:
            report.pending.append(brand.name)
        elif brand.status == STATUS_DRAFT:
            report.published.append(brand.name)
            if apply:
                brand.status = STATUS_PUBLISHED
                audit.record(
                    db, None, "update", "brand", brand.id, {"status": [STATUS_DRAFT, STATUS_PUBLISHED]}
                )
    db.flush()
    return report


def main(argv: list[str] | None = None) -> Report:
    parser = argparse.ArgumentParser(description="Publica las marcas en borrador")
    parser.add_argument("--apply", action="store_true", help="publicar; sin esto solo simula")
    args = parser.parse_args(argv)
    engine = make_engine(get_settings().resolved_database_url)
    with make_session_factory(engine)() as session, session.begin():
        report = run(session, apply=args.apply)
    engine.dispose()
    print(report.as_text(args.apply))
    return report


if __name__ == "__main__":
    main()
