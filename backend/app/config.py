from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    database_url: str = "sqlite:///./eleven.db"
    demo_mode: bool = False
    whatsapp_number: str = ""
    public_site_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"
    # Anything other than "development" marks the session cookie Secure: safe if left unset.
    app_env: str = "production"
    media_root: str = ""

    @property
    def resolved_database_url(self) -> str:
        """Anchors a relative SQLite path to backend/, whatever the current directory is."""
        prefix = "sqlite:///./"
        if self.database_url.startswith(prefix):
            return f"sqlite:///{BASE_DIR / self.database_url.removeprefix(prefix)}"
        return self.database_url

    @property
    def secure_cookies(self) -> bool:
        return self.app_env.strip().casefold() != "development"

    @property
    def resolved_media_root(self) -> Path:
        return Path(self.media_root).resolve() if self.media_root else BASE_DIR / "media"

    @property
    def admin_origins(self) -> set[str]:
        """Origins allowed to send admin mutations."""
        origins = [*self.cors_origin_list, self.public_site_url]
        return {origin.strip().rstrip("/").casefold() for origin in origins if origin.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def site_base_url(self) -> str:
        return self.public_site_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
