"""
Document management router.
POST /api/v1/documents/upload         — upload and ingest PDF
GET  /api/v1/documents/{type}/count   — count chunks by type
POST /api/v1/documents/ask            — RAG question answering
"""

import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi import Query as QueryParam

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.document import (
    AnalysisResponse,
    DocumentCountResponse,
    QuestionRequest,
    QuestionResponse,
    UploadResponse,
)
from app.services.rag_service import (
    chunk_text,
    extract_text_from_pdf,
    generate_answer,
    get_chunks_by_type,
    retrieve_chunks,
    store_document_chunks,
)
from app.services.compliance_service import analyze_compliance

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = get_logger(__name__)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a PDF document",
)
async def upload_document(
    document_type: str = QueryParam(
        ...,
        description="Document category: 'policy' or 'regulation'",
        pattern="^[a-zA-Z_]{1,50}$",
    ),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Accept a PDF upload, extract text, chunk it, and store in ChromaDB.
    The document_type parameter categorises the document for RAG retrieval.
    """
    logger.info(
        f"Upload request: filename={file.filename} type={document_type} "
        f"user_id={current_user.id}"
    )

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted. Ensure the file has a .pdf extension.",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File exceeds maximum allowed size of "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        )

    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as fh:
        fh.write(content)

    text = extract_text_from_pdf(file_path)
    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No readable text could be extracted from the uploaded PDF.",
        )

    chunks = chunk_text(text)
    store_document_chunks(chunks, file.filename, document_type)

    logger.info(
        f"Upload complete: {file.filename} | "
        f"{len(chunks)} chunks | {len(text)} chars"
    )

    return UploadResponse(
        status="ingested",
        filename=file.filename,
        document_type=document_type,
        characters=len(text),
        chunks=len(chunks),
    )


@router.get(
    "/{document_type}/count",
    response_model=DocumentCountResponse,
    summary="Count stored chunks for a document type",
)
def get_document_count(
    document_type: str,
    current_user: User = Depends(get_current_user),
):
    docs = get_chunks_by_type(document_type)
    return DocumentCountResponse(
        document_type=document_type,
        documents_found=len(docs),
    )


@router.post(
    "/ask",
    response_model=QuestionResponse,
    summary="Answer a question using RAG over uploaded documents",
)
def ask_question(
    payload: QuestionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the most relevant document chunks and generate a grounded answer
    using the configured LLM.
    """
    logger.info(
        f"Q&A request: user_id={current_user.id} "
        f"question={payload.question[:100]}"
    )

    results = retrieve_chunks(payload.question)
    chunks = results.get("documents", [])

    if not chunks:
        return QuestionResponse(
            question=payload.question,
            answer=(
                "No documents have been uploaded yet. "
                "Please upload policy or regulation documents first."
            ),
            sources=[],
        )

    answer = generate_answer(payload.question, chunks)
    sources = [m for m in results.get("metadata", []) if m]

    return QuestionResponse(
        question=payload.question,
        answer=answer,
        sources=sources,
    )


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Generate a narrative compliance analysis",
)
def analyze_documents(current_user: User = Depends(get_current_user)):
    """
    Produce a free-text compliance analysis comparing uploaded policy
    documents against uploaded regulation documents.
    """
    policy_chunks = get_chunks_by_type("policy")
    regulation_chunks = get_chunks_by_type("regulation")

    if not policy_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No policy documents found. Upload a policy PDF first.",
        )
    if not regulation_chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No regulation documents found. Upload a regulation PDF first.",
        )

    analysis = analyze_compliance(policy_chunks, regulation_chunks)
    logger.info(f"Compliance analysis produced: user_id={current_user.id}")
    return AnalysisResponse(analysis=analysis)
