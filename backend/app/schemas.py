from datetime import datetime

from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    id: str
    filename: str
    pages: int
    chunks: int
    # UTC; None for documents indexed before upload times were stored.
    uploaded_at: datetime | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # None searches all documents.
    document_ids: list[str] | None = None


class Source(BaseModel):
    number: int  # the [n] used in the answer
    document_id: str
    filename: str
    page: int
    text: str
    score: float | None  # relevance to the question; None for summaries
    cited: bool


class Usage(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float | None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    usage: Usage | None
