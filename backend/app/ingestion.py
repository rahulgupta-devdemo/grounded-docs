import hashlib

from app import llm, vector_store
from app.chunking import chunk_pages
from app.config import get_settings
from app.pdf_parser import InvalidPdfError, extract_pages
from app.schemas import DocumentInfo


class IngestionError(ValueError):
    """A problem with the uploaded file that the user can fix."""


def ingest_pdf(filename: str, data: bytes) -> DocumentInfo:
    settings = get_settings()

    try:
        pages = extract_pages(data)
    except InvalidPdfError as exc:
        raise IngestionError(str(exc)) from exc

    chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise IngestionError(
            "No text found in the PDF. Scanned documents without a text layer are not supported."
        )

    # Same file content -> same id, so re-uploading replaces instead of duplicating.
    document = DocumentInfo(
        id=hashlib.sha256(data).hexdigest()[:16],
        filename=filename,
        pages=len(pages),
        chunks=len(chunks),
    )
    vectors = llm.embed_documents([(filename, chunk.text) for chunk in chunks])
    vector_store.replace_document(document, chunks, vectors)
    return document
