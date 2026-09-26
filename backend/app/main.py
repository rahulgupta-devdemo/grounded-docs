import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.genai import errors as genai_errors
from qdrant_client.http.exceptions import ResponseHandlingException

from app import llm, vector_store
from app.api import chat, documents
from app.config import get_settings

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()  # fail at startup, not on first request, if configuration is missing
    # An empty key (.env copied but not filled in) still lets the app start, so
    # the UI can show what is missing; the log says it right away.
    if not settings.gemini_api_key.strip():
        logger.warning("GEMINI_API_KEY is empty: set it in .env, otherwise uploads and questions fail.")
    yield


app = FastAPI(title="Document Chat API", lifespan=lifespan)
app.include_router(documents.router)
app.include_router(chat.router)


@app.exception_handler(llm.MissingApiKeyError)
def missing_api_key(_: Request, exc: llm.MissingApiKeyError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(genai_errors.APIError)
def model_provider_error(_: Request, exc: genai_errors.APIError) -> JSONResponse:
    return JSONResponse(
        status_code=502, content={"detail": f"The model provider returned an error: {exc.message}"}
    )


@app.exception_handler(httpx.TimeoutException)
def model_provider_timeout(_: Request, __: httpx.TimeoutException) -> JSONResponse:
    return JSONResponse(
        status_code=504,
        content={"detail": "The language model did not respond in time. Please try again."},
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
