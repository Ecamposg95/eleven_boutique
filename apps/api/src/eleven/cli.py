"""Comandos de operación: `uv run eleven <comando>`."""

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from eleven.config import get_settings
from eleven.db import get_engine
from eleven.seed import SeedError, load_demo_catalog


def seed_demo(path: Path) -> int:
    settings = get_settings()
    if settings.app_env == "production":
        print("seed-demo no se ejecuta en production.", file=sys.stderr)
        return 2
    with Session(get_engine()) as session, session.begin():
        try:
            report = load_demo_catalog(session, path)
        except SeedError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    print(
        f"Fixtures demo cargados desde {path}: {report.products} productos, "
        f"{report.variants} variantes, {report.collections} colecciones, "
        f"{report.archived} archivados por ausencia."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="eleven")
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed-demo", help="Carga o actualiza el catálogo DEMO")
    seed.add_argument("--file", type=Path, default=None)
    args = parser.parse_args()

    if args.command == "seed-demo":
        path = args.file or get_settings().fixtures_dir / "demo" / "catalog.json"
        sys.exit(seed_demo(path))


if __name__ == "__main__":
    main()
