import pymupdf
import pytest
from qdrant_client import QdrantClient

from app import llm, vector_store
from app.config import get_settings


@pytest.fixture(autouse=True)
def settings_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def memory_qdrant(monkeypatch):
    client = QdrantClient(":memory:")
    monkeypatch.setattr(vector_store, "get_client", lambda: client)
    return client


@pytest.fixture
def fake_embeddings(monkeypatch):
    """Replace the Gemini call; records how many texts were embedded."""
    calls: list[int] = []

    def fake_embed_documents(items):
        calls.append(len(items))
        dim = get_settings().embedding_dim
        return [[1.0 + i] + [0.5] * (dim - 1) for i in range(len(items))]

    monkeypatch.setattr(llm, "embed_documents", fake_embed_documents)
    return calls


def _make_pdf(pages: list[list[str]]) -> bytes:
    doc = pymupdf.open()
    for paragraphs in pages:
        page = doc.new_page()
        for i, paragraph in enumerate(paragraphs):
            page.insert_text((72, 72 + i * 200), paragraph)
    return doc.tobytes()


@pytest.fixture
def make_pdf():
    return _make_pdf
