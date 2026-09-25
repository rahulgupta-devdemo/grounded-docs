from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors
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


class FakeGenerateModels:
    """Fails with the given errors per model, otherwise answers."""

    def __init__(self, failures: dict[str, Exception]):
        self.failures = failures
        self.called: list[str] = []

    def generate_content(self, *, model, contents, config):
        self.called.append(model)
        if model in self.failures:
            raise self.failures[model]
        return types.GenerateContentResponse(
            candidates=[types.Candidate(content=types.Content(parts=[types.Part(text="Answer [1]")]))],
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=500, candidates_token_count=20, thoughts_token_count=30
            ),
        )


def _use_generate_models(monkeypatch, models):
    monkeypatch.setenv("CHAT_MODELS", "primary-model,fallback-model")
    llm.get_settings.cache_clear()
    monkeypatch.setattr(llm, "_client", lambda: SimpleNamespace(models=models))


def _server_error(code):
    return genai_errors.ServerError(code, {"error": {"message": "busy", "status": "UNAVAILABLE"}})


def test_generate_reports_model_and_counts_thinking_as_output(monkeypatch):
    _use_generate_models(monkeypatch, FakeGenerateModels({}))

    generation = llm.generate("system", "prompt")

    assert generation.text == "Answer [1]"
    assert generation.model == "primary-model"
    assert generation.input_tokens == 500
    assert generation.output_tokens == 50


def test_overloaded_model_falls_back_to_next(monkeypatch):
    models = FakeGenerateModels({"primary-model": _server_error(503)})
    _use_generate_models(monkeypatch, models)

    generation = llm.generate("system", "prompt")

    assert models.called == ["primary-model", "fallback-model"]
    assert generation.model == "fallback-model"


def test_deadline_exceeded_falls_back_to_next(monkeypatch):
    models = FakeGenerateModels({"primary-model": _server_error(504)})
    _use_generate_models(monkeypatch, models)

    assert llm.generate("system", "prompt").model == "fallback-model"


def test_request_errors_do_not_fall_back(monkeypatch):
    bad_request = genai_errors.ClientError(400, {"error": {"message": "bad", "status": "INVALID_ARGUMENT"}})
    models = FakeGenerateModels({"primary-model": bad_request})
    _use_generate_models(monkeypatch, models)

    with pytest.raises(genai_errors.ClientError):
        llm.generate("system", "prompt")
    assert models.called == ["primary-model"]


def test_raises_when_all_models_are_unavailable(monkeypatch):
    models = FakeGenerateModels({"primary-model": _server_error(503), "fallback-model": _server_error(504)})
    _use_generate_models(monkeypatch, models)

    with pytest.raises(genai_errors.ServerError):
        llm.generate("system", "prompt")


def test_fails_loudly_if_provider_returns_fewer_vectors(monkeypatch):
    # This is what happens if texts get merged into one embedding.
    models = FakeModels(vectors_per_call=1)
    monkeypatch.setattr(llm, "_client", lambda: SimpleNamespace(models=models))

    with pytest.raises(RuntimeError, match="Expected 3 embeddings, got 1"):
        llm.embed_documents([("a.pdf", "x"), ("a.pdf", "y"), ("a.pdf", "z")])
