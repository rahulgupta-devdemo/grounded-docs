from pydantic import BaseModel


class DocumentInfo(BaseModel):
    id: str
    filename: str
    pages: int
    chunks: int
