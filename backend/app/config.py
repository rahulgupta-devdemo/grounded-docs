from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root .env for local runs; inside Docker the file does not exist and
# Compose injects the variables instead.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    qdrant_url: str = "http://localhost:6333"


@lru_cache
def get_settings() -> Settings:
    return Settings()
