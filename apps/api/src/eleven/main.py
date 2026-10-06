from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eleven import site
from eleven.catalog.router import router as catalog_router
from eleven.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Eleven Boutique API",
        version="0.1.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    v1 = APIRouter(prefix="/api/v1")

    @v1.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    v1.include_router(site.router)
    v1.include_router(catalog_router)
    app.include_router(v1)
    return app


app = create_app()
