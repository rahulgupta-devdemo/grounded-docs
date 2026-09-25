"""All calls to the model provider go through this module.

Switching provider means reimplementing these functions; nothing else in
the backend imports the Gemini SDK.
"""

from dataclasses import dataclass
from functools import lru_cache

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import get_settings

_RETRY = types.HttpRetryOptions(
    attempts=5,
    initial_delay=2.0,
    max_delay=30.0,
    http_status_codes=[429, 500, 503],
)

# 504 is what the API returns when the request deadline passes.
_FALLBACK_STATUS = {429, 500, 503, 504}


@dataclass(frozen=True)
class Generation:
    text: str
    model: str
    input_tokens: int
    output_tokens: int  # includes thinking tokens, which are billed as output


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


def generate(system_instruction: str, prompt: str) -> Generation:
    """Answer with the first configured model that responds in time."""
    settings = get_settings()
    # Answers are interactive: one attempt per model with a short deadline,
    # then the next model, instead of waiting through retries and backoff.
    http_options = types.HttpOptions(
        retry_options=types.HttpRetryOptions(attempts=1),
        timeout=settings.chat_timeout_seconds * 1000,
    )
    last_error: Exception | None = None
    for model in settings.chat_model_list:
        try:
            response = _client().models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    http_options=http_options,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
        except genai_errors.APIError as exc:
            if exc.code not in _FALLBACK_STATUS:
                raise
            last_error = exc
            continue
        except httpx.TimeoutException as exc:
            last_error = exc
            continue

        usage = response.usage_metadata
        return Generation(
            text=(response.text or "").strip(),
            model=model,
            input_tokens=(usage.prompt_token_count or 0) if usage else 0,
            output_tokens=(
                (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
                if usage
                else 0
            ),
        )

    assert last_error is not None, "CHAT_MODELS is empty"
    raise last_error


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
