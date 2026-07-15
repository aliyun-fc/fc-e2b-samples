"""Runtime configuration for Browser Studio."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    e2b_api_key: str = ""
    e2b_api_url: str = ""
    e2b_domain: str = ""
    e2b_template: str = ""
    e2b_browser_image: str = "fc-e2b-registry.us-west-1.cr.aliyuncs.com/runtime/browser:v0.0.32"
    e2b_timeout: int = 600
    studio_host: str = "127.0.0.1"
    studio_port: int = 8000
    studio_cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.studio_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
