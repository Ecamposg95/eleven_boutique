"""python -m scripts.seed_base: category tree and real site settings row. Idempotent."""

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.services.base_seed import seed_categories, seed_site_settings


def main() -> None:
    settings = get_settings()
    engine = make_engine(settings.resolved_database_url)
    with make_session_factory(engine)() as session, session.begin():
        created = seed_categories(session)
        seed_site_settings(session, settings)
    engine.dispose()
    print(f"Categorías creadas: {created}")


if __name__ == "__main__":
    main()
