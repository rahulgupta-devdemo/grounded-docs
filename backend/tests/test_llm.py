from types import SimpleNamespace

import pytest
from google.genai import types

from app import llm


class FakeModels:
    def __init__(self, vectors_per_call=None):
        self.requests: list[list[types.Content]] = []
        self.vectors_per_call = vectors_per_call

    def embed_content(self, *, model, contents, config):
        self.requests.append(contents)
        count = self.vectors_per_call or len(contents)
        return types.EmbedContentResponse(
            embeddings=[types.ContentEmbedding(values=[0.1, 0.2]) for _ in range(count)]
        )


@pytest.fixture
def fake_models(monkeypatch):
    models = FakeModels()
    monkeypatch.setattr(llm, "_client", lambda: SimpleNamespace(models=models))
    return models


def test_each_text_is_sent_as_its_own_content(fake_models):
    llm.embed_documents([("a.pdf", "first"), ("a.pdf", "second")])

    contents = fake_models.requests[0]
    assert len(contents) == 2
    assert all(isinstance(c, types.Content) for c in contents)
    assert contents[0].parts[0].text == "title: a.pdf | text: first"


def test_documents_are_embedded_in_batches(fake_models, monkeypatch):
    monkeypatch.setenv("EMBED_BATCH_SIZE", "2")
    llm.get_settings.cache_clear()

    vectors = llm.embed_documents([("a.pdf", f"chunk {i}") for i in range(5)])

    assert [len(r) for r in fake_models.requests] == [2, 2, 1]
    assert len(vectors) == 5


def test_query_uses_question_answering_prefix(fake_models):
    llm.embed_query("Which IP rating?")

    assert fake_models.requests[0][0].parts[0].text == (
        "task: question answering | query: Which IP rating?"
    )


def test_fails_loudly_if_provider_returns_fewer_vectors(monkeypatch):
    # This is what happens if texts get merged into one embedding.
    models = FakeModels(vectors_per_call=1)
    monkeypatch.setattr(llm, "_client", lambda: SimpleNamespace(models=models))

    with pytest.raises(RuntimeError, match="Expected 3 embeddings, got 1"):
        llm.embed_documents([("a.pdf", "x"), ("a.pdf", "y"), ("a.pdf", "z")])
