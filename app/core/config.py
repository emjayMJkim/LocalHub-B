from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


APP_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = APP_DIR / ".env"

class Settings(BaseSettings):
    app_name: str = "지역정보 공유 커뮤니티 API"
    app_version: str = "1.0.0"
    api_v1_prefix: str = "/api/v1"

    database_url: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()