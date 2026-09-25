"""All Qdrant access goes through this module."""

import uuid
from functools import lru_cache

from qdrant_client import QdrantClient, models

from app.chunking import Chunk
from app.config import get_settings
from app.schemas import DocumentInfo


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
    # combination gets its own collection.
    settings = get_settings()
    return f"chunks_{settings.embedding_model}_{settings.embedding_dim}"


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
                vector=vector,
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


def list_documents() -> list[DocumentInfo]:
    client = get_client()
    name = collection_name()
    if not client.collection_exists(name):
        return []

    # Every document has exactly one chunk with index 0; its payload carries
    # the document-level fields.
    points, _ = client.scroll(
        name,
        scroll_filter=models.Filter(
            must=[models.FieldCondition(key="chunk_index", match=models.MatchValue(value=0))]
        ),
        limit=1000,
        with_payload=True,
        with_vectors=False,
    )
    documents = [
        DocumentInfo(
            id=p.payload["document_id"],
            filename=p.payload["filename"],
            pages=p.payload["page_count"],
            chunks=p.payload["chunk_count"],
        )
        for p in points
    ]
    return sorted(documents, key=lambda d: d.filename.lower())


def _ensure_collection(client: QdrantClient, name: str) -> None:
    if client.collection_exists(name):
        return
    client.create_collection(
        name,
        vectors_config=models.VectorParams(
            size=get_settings().embedding_dim, distance=models.Distance.COSINE
        ),
    )
    client.create_payload_index(name, "document_id", models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(name, "chunk_index", models.PayloadSchemaType.INTEGER)


def _document_filter(document_id: str) -> models.FilterSelector:
    return models.FilterSelector(
        filter=models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))]
        )
    )
