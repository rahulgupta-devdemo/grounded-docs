import math
import re
import zlib

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


def lexical_vector(text: str) -> list[float]:
    """Deterministic stand-in for an embedding: texts sharing words get similar vectors."""
    dim = get_settings().embedding_dim
    vector = [0.0] * dim
    for word in re.findall(r"\w+", text.lower()):
        vector[zlib.crc32(word.encode()) % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


@pytest.fixture
def fake_embeddings(monkeypatch):
    """Replace the Gemini embedding calls; records how many texts were embedded."""
    calls: list[int] = []

    def fake_embed_documents(items):
        calls.append(len(items))
        return [lexical_vector(text) for _, text in items]

    monkeypatch.setattr(llm, "embed_documents", fake_embed_documents)
    monkeypatch.setattr(llm, "embed_query", lexical_vector)
    return calls


class FakeGenerator:
    def __init__(self):
        self.answer = "IP66 [1]"
        self.prompts: list[str] = []

    def __call__(self, system_instruction, prompt):
        self.prompts.append(prompt)
        return llm.Generation(
            text=self.answer, model="gemini-3.5-flash-lite", input_tokens=1000, output_tokens=100
        )


@pytest.fixture
def fake_generate(monkeypatch):
    generator = FakeGenerator()
    monkeypatch.setattr(llm, "generate", generator)
    return generator


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
