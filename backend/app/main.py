from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.genai import errors as genai_errors
from qdrant_client.http.exceptions import ResponseHandlingException

from app import vector_store
from app.api import documents
from app.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()  # fail at startup, not on first request, if configuration is missing
    yield


app = FastAPI(title="Document Chat API", lifespan=lifespan)
app.include_router(documents.router)


@app.exception_handler(genai_errors.APIError)
def model_provider_error(_: Request, exc: genai_errors.APIError) -> JSONResponse:
    return JSONResponse(
        status_code=502, content={"detail": f"The model provider returned an error: {exc.message}"}
    )


@app.exception_handler(ResponseHandlingException)
def vector_store_unreachable(_: Request, __: ResponseHandlingException) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "The vector database is not reachable."})


@app.get("/health")
def health() -> JSONResponse:
    qdrant_ok = vector_store.is_reachable()
    return JSONResponse(
        status_code=200 if qdrant_ok else 503,
        content={"status": "ok" if qdrant_ok else "degraded", "qdrant": qdrant_ok},
    )
