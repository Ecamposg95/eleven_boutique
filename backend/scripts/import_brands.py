"""python -m scripts.import_brands"""

from app.config import get_settings
from app.db import make_engine, make_session_factory
from app.services.brand_import import ImportReport, run_import


def main() -> ImportReport:
    engine = make_engine(get_settings().resolved_database_url)
    with make_session_factory(engine)() as session, session.begin():
        report = run_import(session)
    engine.dispose()
    print(report.as_text())
    return report


if __name__ == "__main__":
    main()
