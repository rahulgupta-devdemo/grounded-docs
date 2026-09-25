from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo-root .env for local runs; inside Docker the file does not exist and
# Compose injects the variables instead.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    gemini_api_key: str
    embedding_model: str = "gemini-embedding-2"
    embedding_dim: int = 768
    embed_batch_size: int = 20

    chunk_size: int = 3000
    chunk_overlap: int = 400

    qdrant_url: str = "http://localhost:6333"


@lru_cache
def get_settings() -> Settings:
    return Settings()
