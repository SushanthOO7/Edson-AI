from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_title: str = "Edson IT AI Support Platform"
    api_version: str = "0.1.0"
    app_env: str = "local"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    createai_mock: bool = True
    createai_query_url: str | None = None
    createai_api_key: str | None = None
    createai_api_key_header: str = "Authorization"
    createai_model_provider: str = "openai"
    createai_model_name: str = "gpt4o"
    createai_temperature: float = 0.1
    createai_top_p: float = 0.01
    createai_timeout_seconds: float = 30.0

    database_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
