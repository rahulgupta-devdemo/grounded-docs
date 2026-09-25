from fastapi import APIRouter, HTTPException, UploadFile

from app import vector_store
from app.ingestion import IngestionError, ingest_pdf
from app.schemas import DocumentInfo

MAX_UPLOAD_BYTES = 20 * 1024 * 1024

router = APIRouter(prefix="/documents", tags=["documents"])


# Plain `def` (not async): FastAPI runs it in a worker thread, so the blocking
# embedding and Qdrant calls do not stall other requests.
@router.post("", response_model=DocumentInfo)
def upload_document(file: UploadFile) -> DocumentInfo:
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF files are supported.")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "The file is larger than 20 MB.")

    try:
        return ingest_pdf(filename, data)
    except IngestionError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("", response_model=list[DocumentInfo])
def list_documents() -> list[DocumentInfo]:
    return vector_store.list_documents()
