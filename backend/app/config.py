from functools import lru_cache
from pathlib import Path

from pydantic import Field
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
    # Tried in order; the next one answers if a model is overloaded or too slow.
    chat_models: str = "gemini-3.1-flash-lite,gemini-3.5-flash-lite"
    # Per model. The Gemini API rejects deadlines below 10 seconds.
    chat_timeout_seconds: int = Field(default=10, ge=10)

    chunk_size: int = 3000
    chunk_overlap: int = 400
    top_k: int = 5

    qdrant_url: str = "http://localhost:6333"

    @property
    def chat_model_list(self) -> list[str]:
        return [m.strip() for m in self.chat_models.split(",") if m.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
