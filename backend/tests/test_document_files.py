import pytest
from fastapi.testclient import TestClient

from app import summarizing
from app.main import app


@pytest.fixture
def client(memory_qdrant, fake_embeddings, fake_generate):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def datasheet(client, make_pdf):
    pdf = make_pdf([
        ["StreetLight 20 Mini datasheet."],
        ["Protection class IP66, impact resistance IK08."],
        ["Article number 5XA6231NA20."],
    ])
    document = client.post(
        "/documents", files={"file": ("datasheet.pdf", pdf, "application/pdf")}
    ).json()
    return document, pdf


def test_original_file_can_be_downloaded(client, datasheet):
    document, pdf = datasheet

    response = client.get(f"/documents/{document['id']}/file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == pdf


@pytest.mark.parametrize(
    "document_id",
    ["..%2F..%2F.env", "..", "not-a-document-id", "0123456789abcdef"],
)
def test_only_stored_documents_are_served(client, datasheet, document_id):
    assert client.get(f"/documents/{document_id}/file").status_code == 404


def test_summary_sends_every_page_with_its_number(client, datasheet, fake_generate):
    document, _ = datasheet

    client.post(f"/documents/{document['id']}/summary")

    prompt = fake_generate.prompts[0]
    assert "Document: datasheet.pdf" in prompt
    assert "[1]\nStreetLight 20 Mini datasheet." in prompt
    assert "[2]\nProtection class IP66, impact resistance IK08." in prompt
    assert "[3]\nArticle number 5XA6231NA20." in prompt
    assert prompt.endswith("Summarise this document in English.")
    assert fake_generate.timeouts == [summarizing.SUMMARY_TIMEOUT_SECONDS]


def test_summary_returns_cited_pages_as_sources(client, datasheet, fake_generate):
    document, _ = datasheet
    fake_generate.answer = "A datasheet [1]. IP66 [2]."

    body = client.post(f"/documents/{document['id']}/summary").json()

    assert body["answer"] == "A datasheet [1]. IP66 [2]."
    assert [(s["number"], s["page"]) for s in body["sources"]] == [(1, 1), (2, 2)]
    assert all(s["score"] is None and s["cited"] for s in body["sources"])
    assert body["usage"]["model"] == "gemini-3.5-flash-lite"


@pytest.mark.parametrize(
    ("limit", "covered"),
    [(80, "pages 1–2"), (40, "page 1")],  # page lengths: 30, 47, 28 characters
)
def test_long_document_summary_says_which_pages_it_covers(
    client, datasheet, monkeypatch, limit, covered
):
    document, _ = datasheet
    monkeypatch.setattr(summarizing, "MAX_CHARACTERS", limit)

    answer = client.post(f"/documents/{document['id']}/summary").json()["answer"]

    assert answer.endswith(
        f"(This summary covers {covered} of 3; the document is longer than the summary limit.)"
    )


def test_german_document_is_summarised_in_german(client, make_pdf, fake_generate):
    pdf = make_pdf([["Die Leuchte darf nur von einer Elektrofachkraft installiert werden."]])
    document = client.post(
        "/documents", files={"file": ("anleitung.pdf", pdf, "application/pdf")}
    ).json()

    client.post(f"/documents/{document['id']}/summary")

    assert fake_generate.prompts[0].endswith("Summarise this document in German.")


def test_delete_removes_passages_and_file(client, datasheet, make_pdf, fake_generate):
    document, _ = datasheet
    other = make_pdf([["Installation height between 4 and 12 metres."]])
    client.post("/documents", files={"file": ("manual.pdf", other, "application/pdf")})

    response = client.delete(f"/documents/{document['id']}")

    assert response.status_code == 204
    assert [d["filename"] for d in client.get("/documents").json()] == ["manual.pdf"]
    assert client.get(f"/documents/{document['id']}/file").status_code == 404
    sources = client.post("/chat", json={"question": "IP66"}).json()["sources"]
    assert {s["filename"] for s in sources} == {"manual.pdf"}


@pytest.mark.parametrize("document_id", ["0123456789abcdef", "not-a-document-id"])
def test_deleting_unknown_document_is_404(client, document_id):
    assert client.delete(f"/documents/{document_id}").status_code == 404


def test_summary_of_unknown_document_is_404(client, fake_generate):
    response = client.post("/documents/0123456789abcdef/summary")

    assert response.status_code == 404
    assert "not available" in response.json()["detail"]
    assert fake_generate.prompts == []
