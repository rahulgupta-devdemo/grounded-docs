from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import vector_store

app = FastAPI(title="Document Chat API")


@app.get("/health")
def health() -> JSONResponse:
    qdrant_ok = vector_store.is_reachable()
    return JSONResponse(
        status_code=200 if qdrant_ok else 503,
        content={"status": "ok" if qdrant_ok else "degraded", "qdrant": qdrant_ok},
    )
