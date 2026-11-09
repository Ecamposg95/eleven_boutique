from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.limits import AdminGuard
from app.api.static import MediaFiles
from app.api.v1.routes import router
from app.config import Settings, get_settings
from app.db import make_engine, make_session_factory


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Eleven Boutique API", lifespan=_lifespan)
    app.state.settings = settings
    app.state.engine = make_engine(settings.resolved_database_url)
    app.state.session_factory = make_session_factory(app.state.engine)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(AdminGuard)
    install_error_handlers(app)
    app.include_router(router)
    app.mount("/media", MediaFiles(directory=settings.resolved_media_root, check_dir=False))
    return app


app = create_app()
