from fastapi import APIRouter, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse

from app import file_store, vector_store
from app.ingestion import IngestionError, ingest_pdf
from app.schemas import ChatResponse, DocumentInfo
from app.summarizing import DocumentNotAvailable, summarize_document

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


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str) -> Response:
    if vector_store.get_document(document_id) is None and file_store.path_for(document_id) is None:
        raise HTTPException(404, "Document not found.")
    vector_store.delete_document(document_id)
    file_store.delete(document_id)
    return Response(status_code=204)


@router.get("/{document_id}/file", response_class=FileResponse)
def get_document_file(document_id: str) -> FileResponse:
    path = file_store.path_for(document_id)
    if path is None:
        raise HTTPException(404, "The original file is not available.")
    # No filename header: the browser shows the PDF inline, and "#page=N"
    # in the URL opens it at a page. The UI sets the name for downloads.
    return FileResponse(path, media_type="application/pdf")


@router.post("/{document_id}/summary", response_model=ChatResponse)
def summarize(document_id: str) -> ChatResponse:
    try:
        return summarize_document(document_id)
    except DocumentNotAvailable as exc:
        raise HTTPException(404, str(exc)) from exc
