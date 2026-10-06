from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Configuración por variables de entorno. Ver `.env.example` en la raíz del repo."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "preview", "production"] = "local"
    database_url: str = "postgresql+psycopg://eleven:eleven@localhost:5433/eleven"
    test_database_url: str | None = None
    # Tenant servido por esta instancia. Se resuelve en servidor, nunca desde el cliente.
    tenant_slug: str = "demo"
    # Lista separada por comas en la variable de entorno.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    catalog_page_max: int = 48
    fixtures_dir: Path = REPO_ROOT / "fixtures"
    # Prefijo público de medios aprobados. Vacío = rutas relativas al sitio (medios demo en
    # apps/web/public). En E3 apuntará al CDN de derivados aprobados.
    media_public_base_url: str = ""

    demo_mode: bool = True
    catalog_public_enabled: bool = True
    vision_processing_enabled: bool = False
    whatsapp_autoreply_enabled: bool = False
    atlas_sync_enabled: bool = False
    checkout_enabled: bool = False
    payments_enabled: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
