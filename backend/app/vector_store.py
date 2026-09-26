"""All Qdrant access goes through this module."""

import uuid
from dataclasses import dataclass
from functools import lru_cache

from qdrant_client import QdrantClient, models

from app.chunking import Chunk
from app.config import get_settings
from app.keywords import keyword_vector, query_vector
from app.schemas import DocumentInfo

_PAGE_SIZE = 1000
_DENSE = "dense"
_SPARSE = "sparse"
# Candidates each search contributes before the two rankings are fused.
_CANDIDATES = 20


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    filename: str
    page: int
    text: str
    # Cosine similarity for semantic search, reciprocal-rank-fusion score for
    # hybrid search; higher is better in both.
    score: float


@lru_cache
def get_client() -> QdrantClient:
    return QdrantClient(url=get_settings().qdrant_url, timeout=5)


def is_reachable() -> bool:
    try:
        get_client().get_collections()
        return True
    except Exception:
        return False


def collection_name() -> str:
    # Vectors from different models or sizes are not comparable, so each
    # combination gets its own collection. "hybrid" marks the layout with a
    # semantic and a keyword vector per passage.
    settings = get_settings()
    return f"chunks_{settings.embedding_model}_{settings.embedding_dim}_hybrid"


def replace_document(
    document: DocumentInfo, chunks: list[Chunk], vectors: list[list[float]]
) -> None:
    """Store a document's chunks, replacing any earlier version of it."""
    client = get_client()
    name = collection_name()
    _ensure_collection(client, name)

    client.delete(name, points_selector=_document_filter(document.id), wait=True)
    client.upsert(
        name,
        wait=True,
        points=[
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document.id}/{chunk.index}")),
                vector={
                    _DENSE: vector,
                    _SPARSE: keyword_vector(f"{document.filename} {chunk.text}"),
                },
                payload={
                    "document_id": document.id,
                    "filename": document.filename,
                    "page_count": document.pages,
                    "chunk_count": document.chunks,
                    "page": chunk.page,
                    "chunk_index": chunk.index,
                    "text": chunk.text,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ],
    )


def delete_document(document_id: str) -> None:
    client = get_client()
    name = collection_name()
    if client.collection_exists(name):
        client.delete(name, points_selector=_document_filter(document_id), wait=True)


def list_documents() -> list[DocumentInfo]:
    return sorted(_first_chunks(), key=lambda d: d.filename.lower())


def get_document(document_id: str) -> DocumentInfo | None:
    documents = _first_chunks(document_id)
    return documents[0] if documents else None


def _first_chunks(document_id: str | None = None) -> list[DocumentInfo]:
    client = get_client()
    name = collection_name()
    if not client.collection_exists(name):
        return []

    # Every document has exactly one chunk with index 0; its payload carries
    # the document-level fields.
    conditions = [models.FieldCondition(key="chunk_index", match=models.MatchValue(value=0))]
    if document_id is not None:
        conditions.append(
            models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))
        )
    # Read page by page, so the list is complete however many documents exist.
    documents: list[DocumentInfo] = []
    offset = None
    while True:
        points, offset = client.scroll(
            name,
            scroll_filter=models.Filter(must=conditions),
            limit=_PAGE_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        documents += [
            DocumentInfo(
                id=p.payload["document_id"],
                filename=p.payload["filename"],
                pages=p.payload["page_count"],
                chunks=p.payload["chunk_count"],
            )
            for p in points
        ]
        if offset is None:
            return documents


def search(
    vector: list[float],
    limit: int,
    document_ids: list[str] | None = None,
    keywords: str | None = None,
) -> list[SearchHit]:
    """Semantic search, or hybrid search when the question text is given as `keywords`."""
    client = get_client()
    name = collection_name()
    if not client.collection_exists(name):
        return []

    query_filter = None
    if document_ids is not None:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchAny(any=document_ids))]
        )

    sparse = query_vector(keywords) if keywords else None
    if sparse is not None and sparse.indices:
        # Both searches return their best candidates; reciprocal rank fusion
        # merges the two rankings by position, so their different score
        # scales never have to be compared.
        points = client.query_points(
            name,
            prefetch=[
                models.Prefetch(query=vector, using=_DENSE, filter=query_filter, limit=_CANDIDATES),
                models.Prefetch(query=sparse, using=_SPARSE, filter=query_filter, limit=_CANDIDATES),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        ).points
    else:
        points = client.query_points(
            name, query=vector, using=_DENSE, limit=limit, query_filter=query_filter, with_payload=True
        ).points
    return [
        SearchHit(
            document_id=p.payload["document_id"],
            filename=p.payload["filename"],
            page=p.payload["page"],
            text=p.payload["text"],
            score=p.score,
        )
        for p in points
    ]


def _ensure_collection(client: QdrantClient, name: str) -> None:
    if client.collection_exists(name):
        return
    client.create_collection(
        name,
        vectors_config={
            _DENSE: models.VectorParams(size=get_settings().embedding_dim, distance=models.Distance.COSINE)
        },
        # IDF: Qdrant weights each word by how rare it is across all passages.
        sparse_vectors_config={_SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
    )
    client.create_payload_index(name, "document_id", models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(name, "chunk_index", models.PayloadSchemaType.INTEGER)


def _document_filter(document_id: str) -> models.FilterSelector:
    return models.FilterSelector(
        filter=models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
        )
    )
