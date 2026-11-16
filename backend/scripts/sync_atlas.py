"""python -m scripts.sync_atlas [--full]

Una corrida de sincronización con Atlas ONE (el cron de Railway la llama cada 5 minutos).
Sale 0 sin hacer nada si ATLAS_SYNC_ENABLED es falso o falta la URL o la llave; sale 1 si la
corrida termina en error, para que Railway la marque como fallida.
"""

import argparse
import sys

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.services.atlas.client import AtlasClient
from app.services.atlas.sync import run_sync


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sincroniza piezas y disponibilidad desde Atlas ONE")
    parser.add_argument("--full", action="store_true", help="carga completa de piezas")
    args = parser.parse_args(argv)
    settings = get_settings()
    if not settings.atlas_sync_enabled:
        print("Sincronización con Atlas ONE desactivada (ATLAS_SYNC_ENABLED).")
        return 0
    if not settings.atlas_api_url.strip() or not settings.atlas_api_key.strip():
        print("Falta ATLAS_API_URL o ATLAS_API_KEY: no se sincroniza.")
        return 0

    engine = make_engine(settings.resolved_database_url)
    client = AtlasClient(settings.atlas_api_url.strip(), settings.atlas_api_key.strip())
    try:
        run = run_sync(make_session_factory(engine), client, kind="full" if args.full else "incremental")
    finally:
        client.close()
        engine.dispose()
    if run is None:
        print("Otra sincronización está en curso; no se hizo nada.")
        return 0
    counts = ", ".join(f"{key}={value}" for key, value in run.counts.items())
    print(f"Sincronización {run.kind}: {run.status}. {counts}")
    if run.error:
        print(f"Error: {run.error}")
    return 1 if run.status == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
