import pytest
from fastapi.testclient import TestClient

from app import llm
from app.config import get_settings
from app.keywords import keyword_vector, query_vector
from app.main import app


def test_keyword_vector_has_one_weight_per_word():
    vector = keyword_vector("IP66 luminaire IP66")

    assert len(vector.indices) == len(set(vector.indices)) == 2
    weights = dict(zip(vector.indices, vector.values))
    ip66 = query_vector("ip66").indices[0]
    luminaire = query_vector("luminaire").indices[0]
    assert weights[ip66] > weights[luminaire]  # occurs twice


def test_keywords_are_case_insensitive_and_skip_single_characters():
    assert query_vector("AB12CD34EF").indices == query_vector("ab12cd34ef").indices
    assert query_vector("E R U I H").indices == []


@pytest.fixture
def indistinguishable_embeddings(monkeypatch):
    """Every text gets the same vector, so only keyword search can tell passages apart."""
    dim = get_settings().embedding_dim
    same = [1.0] + [0.0] * (dim - 1)
    monkeypatch.setattr(llm, "embed_documents", lambda items: [same for _ in items])
    monkeypatch.setattr(llm, "embed_query", lambda question: same)


@pytest.fixture
def client(memory_qdrant, indistinguishable_embeddings, fake_generate, make_pdf):
    with TestClient(app) as test_client:
        for name, text in (
            ("datasheet-a.pdf", "Order no. XY98ZW76QR. Control: Bluetooth Mesh."),
            ("datasheet-b.pdf", "Bestell-Nr. AB12CD34EF. Ansteuerung: DALI 2."),
            ("brochure.pdf", "High bay luminaires for logistics and production halls."),
        ):
            test_client.post("/documents", files={"file": (name, make_pdf([[text]]), "application/pdf")})
        yield test_client


def _first_source(client, question):
    return client.post("/chat", json={"question": question}).json()["sources"][0]["filename"]


def test_hybrid_search_finds_the_passage_with_the_article_number(client, monkeypatch):
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")
    get_settings.cache_clear()

    assert _first_source(client, "Which control does AB12CD34EF use?") == "datasheet-b.pdf"
    assert _first_source(client, "Which control does XY98ZW76QR use?") == "datasheet-a.pdf"


@pytest.mark.parametrize(("mode", "expected_keywords"), [("hybrid", "AB12CD34EF?"), ("dense", None)])
def test_retrieval_mode_decides_whether_keywords_are_used(client, monkeypatch, mode, expected_keywords):
    from app import vector_store

    monkeypatch.setenv("RETRIEVAL_MODE", mode)
    get_settings.cache_clear()
    calls = []
    original = vector_store.search
    monkeypatch.setattr(
        vector_store, "search", lambda *args, **kwargs: calls.append(kwargs) or original(*args, **kwargs)
    )

    client.post("/chat", json={"question": "AB12CD34EF?"})

    assert calls[0]["keywords"] == expected_keywords
