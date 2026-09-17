"""Application settings — all secrets from environment (.env via pydantic-settings)."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://localhost/buyorwait"
    secret_key: str
    access_token_expire_seconds: int = 60 * 60 * 24 * 7  # 7 days
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
