"""All calls to the model provider go through this module.

Switching provider means reimplementing these functions; nothing else in
the backend imports the Gemini SDK.
"""

from functools import lru_cache

from google import genai
from google.genai import types

from app.config import get_settings

_RETRY = types.HttpRetryOptions(
    attempts=5,
    initial_delay=2.0,
    max_delay=30.0,
    http_status_codes=[429, 500, 503],
)


@lru_cache
def _client() -> genai.Client:
    return genai.Client(
        api_key=get_settings().gemini_api_key,
        http_options=types.HttpOptions(retry_options=_RETRY, timeout=60_000),
    )


def embed_documents(items: list[tuple[str, str]]) -> list[list[float]]:
    """Embed (title, text) pairs for storage. Returns one vector per pair."""
    batch_size = get_settings().embed_batch_size
    vectors: list[list[float]] = []
    for start in range(0, len(items), batch_size):
        batch = items[start : start + batch_size]
        vectors.extend(_embed([f"title: {title} | text: {text}" for title, text in batch]))
    return vectors


def embed_query(question: str) -> list[float]:
    return _embed([f"task: question answering | query: {question}"])[0]


def _embed(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    # One Content per text: gemini-embedding-2 merges a plain list of strings
    # into a single vector.
    contents = [types.Content(parts=[types.Part.from_text(text=t)]) for t in texts]
    response = _client().models.embed_content(
        model=settings.embedding_model,
        contents=contents,
        config=types.EmbedContentConfig(output_dimensionality=settings.embedding_dim),
    )
    vectors = [e.values for e in response.embeddings or []]
    if len(vectors) != len(texts):
        raise RuntimeError(f"Expected {len(texts)} embeddings, got {len(vectors)}")
    return vectors
