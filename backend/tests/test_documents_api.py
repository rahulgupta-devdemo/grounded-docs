import pytest
from fastapi.testclient import TestClient
from google.genai import errors as genai_errors

from app import llm
from app.main import app


@pytest.fixture
def client(memory_qdrant, fake_embeddings):
    with TestClient(app) as test_client:
        yield test_client


def _upload(client, content: bytes, filename: str = "datasheet.pdf"):
    return client.post("/documents", files={"file": (filename, content, "application/pdf")})


def test_upload_indexes_pdf_and_lists_it(client, make_pdf):
    response = _upload(client, make_pdf([["Luminous flux 4200 lm."], ["IP66, IK08."]]))

    assert response.status_code == 200
    document = response.json()
    assert document["filename"] == "datasheet.pdf"
    assert document["pages"] == 2
    assert document["chunks"] == 2

    assert client.get("/documents").json() == [document]


def test_chunks_are_stored_with_page_and_text(client, make_pdf, memory_qdrant):
    _upload(client, make_pdf([["Luminous flux 4200 lm."], ["IP66, IK08."]]))

    points, _ = memory_qdrant.scroll(
        memory_qdrant.get_collections().collections[0].name, with_payload=True
    )
    stored = sorted((p.payload["page"], p.payload["text"]) for p in points)
    assert stored == [(1, "Luminous flux 4200 lm."), (2, "IP66, IK08.")]


def test_uploading_same_file_twice_does_not_duplicate(client, make_pdf):
    pdf = make_pdf([["Same content."]])
    _upload(client, pdf)
    _upload(client, pdf)

    assert len(client.get("/documents").json()) == 1


def test_list_includes_every_document_beyond_one_page(client, make_pdf, monkeypatch):
    from app import vector_store

    monkeypatch.setattr(vector_store, "_PAGE_SIZE", 2)
    for i in range(5):
        _upload(client, make_pdf([[f"Document number {i}."]]), filename=f"doc-{i}.pdf")

    names = [d["filename"] for d in client.get("/documents").json()]

    assert names == [f"doc-{i}.pdf" for i in range(5)]


def test_list_is_empty_before_any_upload(client):
    assert client.get("/documents").json() == []


def test_rejects_file_over_the_size_limit(client, monkeypatch):
    from app.api import documents

    monkeypatch.setattr(documents, "MAX_UPLOAD_BYTES", 10)
    response = _upload(client, b"%PDF-" + b"x" * 20)

    assert response.status_code == 413


def test_rejects_non_pdf_filename(client):
    response = _upload(client, b"hello", filename="notes.txt")

    assert response.status_code == 415


def test_rejects_file_that_is_not_a_pdf(client):
    response = _upload(client, b"not really a pdf")

    assert response.status_code == 422
    assert "could not be read" in response.json()["detail"]


def test_model_provider_error_returns_502_with_reason(client, make_pdf, monkeypatch):
    def failing_embed(_items):
        raise genai_errors.ClientError(
            429, {"error": {"message": "Quota exceeded", "status": "RESOURCE_EXHAUSTED"}}
        )

    monkeypatch.setattr(llm, "embed_documents", failing_embed)
    response = _upload(client, make_pdf([["Some text."]]))

    assert response.status_code == 502
    assert "Quota exceeded" in response.json()["detail"]


def test_rejects_pdf_without_text(client, make_pdf, fake_embeddings):
    response = _upload(client, make_pdf([[]]))

    assert response.status_code == 422
    assert "No text found" in response.json()["detail"]
    assert fake_embeddings == []  # nothing was sent to the model
