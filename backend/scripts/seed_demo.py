"""python -m scripts.seed_demo: demo catalog. Refuses to run unless DEMO_MODE=true."""

import sys

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.services.demo_seed import DemoModeRequired, DemoSlugConflict, seed_demo


def main() -> int:
    settings = get_settings()
    engine = make_engine(settings.resolved_database_url)
    try:
        with make_session_factory(engine)() as session, session.begin():
            summary = seed_demo(session, settings)
    except (DemoModeRequired, DemoSlugConflict) as exc:
        print(f"Seed demo rechazado: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print(f"Seed demo listo: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
