"""Document upload and retrieval schemas."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    status: str
    filename: str
    document_type: str
    characters: int
    chunks: int


class DocumentCountResponse(BaseModel):
    document_type: str
    documents_found: int


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict]


class AnalysisResponse(BaseModel):
    analysis: str
