import httpx
import pytest
from fastapi.testclient import TestClient

from app import llm
from app.answering import NO_DOCUMENTS_ANSWER, cited_numbers, keep_valid_citations
from app.main import app


@pytest.fixture
def client(memory_qdrant, fake_embeddings, fake_generate):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def two_documents(client, make_pdf):
    datasheet = make_pdf([
        ["Luminous flux 4200 lm, colour temperature 3000 K."],
        ["Protection class IP66, impact resistance IK08."],
    ])
    manual = make_pdf([["Installation height between 4 and 12 metres."]])
    ids = {}
    for name, pdf in (("datasheet.pdf", datasheet), ("manual.pdf", manual)):
        response = client.post("/documents", files={"file": (name, pdf, "application/pdf")})
        ids[name] = response.json()["id"]
    return ids


def _ask(client, question, document_ids=None):
    body = {"question": question}
    if document_ids is not None:
        body["document_ids"] = document_ids
    return client.post("/chat", json=body)


def test_most_relevant_passage_is_ranked_first(client, two_documents):
    sources = _ask(client, "What is the protection class IP66?").json()["sources"]

    assert sources[0]["filename"] == "datasheet.pdf"
    assert sources[0]["page"] == 2
    assert "IP66" in sources[0]["text"]
    assert [s["number"] for s in sources] == list(range(1, len(sources) + 1))


def test_prompt_contains_numbered_passages_with_file_and_page(client, two_documents, fake_generate):
    _ask(client, "What is the protection class IP66?")

    prompt = fake_generate.prompts[0]
    assert "[1] (datasheet.pdf, page 2)\nProtection class IP66, impact resistance IK08." in prompt
    assert "Question: What is the protection class IP66?\n\n" in prompt
    assert prompt.endswith("Answer in English. Translate passage content if needed.")


def test_prompt_names_german_for_german_question(client, two_documents, fake_generate):
    _ask(client, "Welche Schutzart hat die Leuchte?")

    assert "Answer in German." in fake_generate.prompts[0]


def test_answer_marks_cited_sources_and_reports_cost(client, two_documents, fake_generate):
    fake_generate.answer = "The luminaire is IP66 [1]."

    body = _ask(client, "What is the protection class IP66?").json()

    assert body["answer"] == "The luminaire is IP66 [1]."
    assert [s["cited"] for s in body["sources"]][0] is True
    assert not any(s["cited"] for s in body["sources"][1:])
    # 1000 input tokens * $0.30/M + 100 output tokens * $2.50/M
    assert body["usage"]["cost_usd"] == pytest.approx(0.00055)


def test_search_can_be_limited_to_selected_documents(client, two_documents):
    sources = _ask(client, "IP66", document_ids=[two_documents["manual.pdf"]]).json()["sources"]

    assert {s["filename"] for s in sources} == {"manual.pdf"}


def test_without_documents_the_model_is_not_called(client, fake_generate):
    body = _ask(client, "What is the IP rating?").json()

    assert body["answer"] == NO_DOCUMENTS_ANSWER
    assert body["sources"] == []
    assert fake_generate.prompts == []


def test_empty_document_selection_is_not_a_search_of_everything(client, two_documents, fake_generate):
    body = _ask(client, "IP66", document_ids=[]).json()

    assert body["answer"] == NO_DOCUMENTS_ANSWER
    assert fake_generate.prompts == []


def test_timeout_of_all_models_returns_504_with_reason(client, two_documents, monkeypatch):
    def timing_out(_system, _prompt):
        raise httpx.ReadTimeout("The read operation timed out")

    monkeypatch.setattr(llm, "generate", timing_out)
    response = _ask(client, "IP66?")

    assert response.status_code == 504
    assert "did not respond in time" in response.json()["detail"]


def test_citations_to_passages_the_model_never_saw_are_removed(client, two_documents, fake_generate):
    fake_generate.answer = "The luminaire is IP66 [1][9]. Flux is 4200 lm [7]. Height [1, 8]."

    body = _ask(client, "What is the protection class IP66?").json()

    assert body["answer"] == "The luminaire is IP66 [1]. Flux is 4200 lm. Height [1]."
    assert [s["number"] for s in body["sources"] if s["cited"]] == [1]


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("IP66 [1].", "IP66 [1]."),
        ("IP66 [6].", "IP66."),
        ("IP66 [1, 6] and IK08 [2][6].", "IP66 [1] and IK08 [2]."),
        ("No citation.", "No citation."),
    ],
)
def test_keep_valid_citations(answer, expected):
    assert keep_valid_citations(answer, valid={1, 2, 3, 4, 5}) == expected


def test_empty_question_is_rejected(client):
    assert _ask(client, "").status_code == 422


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("IP66 [1].", {1}),
        ("IP66 [1][3] and 4200 lm [2].", {1, 2, 3}),
        ("See [1, 4].", {1, 4}),
        ("No citation here.", set()),
    ],
)
def test_cited_numbers(answer, expected):
    assert cited_numbers(answer) == expected
