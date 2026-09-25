from functools import lru_cache

from qdrant_client import QdrantClient

from app.config import get_settings


@lru_cache
def get_client() -> QdrantClient:
    return QdrantClient(url=get_settings().qdrant_url, timeout=5)


def is_reachable() -> bool:
    try:
        get_client().get_collections()
        return True
    except Exception:
        return False
