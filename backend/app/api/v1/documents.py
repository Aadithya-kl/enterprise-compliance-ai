"""Document management router.

Endpoints:
  POST /api/v1/documents/upload        — upload, ingest, and push to Google Drive
  GET  /api/v1/documents/{type}/count  — count Qdrant chunks by type
  POST /api/v1/documents/ask           — RAG question answering
  POST /api/v1/documents/analyze       — narrative compliance gap analysis
  GET  /api/v1/documents/indexed-files — list all indexed filenames

Upload pipeline (in order):
  1. Validate: extension + max file size + duplicate check.
  2. Save:     Write bytes to Supabase Storage.
  3. Drive:    If configured, upload to Google Drive folder.
               - Deduplication: if a file with the same name exists in the folder,
                 reuse its metadata (drive_upload_status="duplicate").
               - Non-blocking: Drive failure does not abort the request.
               - drive_upload_status: "uploaded" | "duplicate" | "skipped" | "failed"
  4. Extract:  Parse text via format-appropriate extractor (PDF, DOCX, XLSX, etc.).
  5. Chunk:    Split text into overlapping windows.
  6. Ingest:   Store chunks in Qdrant with full provenance metadata:
               - filename, document_type, source, file_hash
               - drive_file_id, drive_file_name, drive_web_view_link (when available)
  7. Respond:  Return UploadResponse including all Drive metadata fields.
"""

import os
import tempfile
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks
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
from app.services.compliance_service import analyze_compliance
from app.services.supabase_storage import supabase_storage_service
from app.services.drive_upload_service import (
    DriveUploadResult,
    UploadToGoogleDriveError,
    drive_upload_service,
)
from app.services.ingestion import (
    chunk_text,
    compute_file_hash,
    check_duplicate,
    check_version_conflict,
    extract_text,
    extract_text_from_pdf,
    store_document_chunks,
)
from app.services.generation import (
    generate_answer,
)
from app.services.retrieval import (
    get_document_chunks_by_type,
    get_indexed_files,
    retrieve_chunks,
)

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = get_logger(__name__)




def _process_document_background(
    temp_path: str,
    filename: str,
    document_type: str,
    file_hash: str,
    supabase_path: str,
    extra_metadata: dict,
):
    try:
        # Google Drive upload (non-blocking)
        if drive_upload_service.is_enabled():
            try:
                drive_result = drive_upload_service.upload_file(
                    local_path=temp_path,
                    filename=filename,
                    document_type=document_type,
                )
                extra_metadata["source"] = "google_drive"
                extra_metadata["drive_file_id"] = drive_result.file_id
                if drive_result.web_view_link:
                    extra_metadata["drive_web_view_link"] = drive_result.web_view_link
                extra_metadata["drive_file_name"] = filename
            except Exception as exc:
                logger.warning(f"Drive upload failed for '{filename}': {exc}")

        # Text extraction
        text = extract_text(temp_path)
        if not text.strip():
            logger.error(f"No readable text extracted for {filename}")
            return

        # Chunking
        chunks = chunk_text(text)

        import re
        doc_year = None
        fn_match = re.search(r'\b(19|20)\d{2}\b', filename)
        if fn_match:
            doc_year = int(fn_match.group(1))
        else:
            text_match = re.search(r'\b(19|20)\d{2}\b', text[:2000])
            if text_match:
                doc_year = int(text_match.group(1))

        if doc_year:
            extra_metadata["year"] = doc_year

        # Ingest to Qdrant
        store_document_chunks(
            chunks=chunks,
            filename=filename,
            document_type=document_type,
            extra_metadata=extra_metadata,
        )
        logger.info(f"Background ingestion complete for {filename}")

    except Exception as proc_exc:
        logger.error(f"Background processing failed for {filename}. Rolling back Supabase upload. Error: {proc_exc}")
        supabase_storage_service.delete_file(supabase_path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_path}: {e}")

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    document_type: str = QueryParam(
        ...,
        description="Document category: 'policy', 'regulation', or 'general'",
        pattern="^[a-zA-Z_]{1,50}$",
    ),
    replace: bool = QueryParam(
        False,
        description="If true, replace existing version of the same document.",
    ),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Full document ingestion pipeline (Supabase Migration Phase 3):

    1. Save file temporarily via NamedTemporaryFile.
    2. Check for duplicates via SHA256 hash. If duplicate, clean up and return early.
    3. Upload file to Supabase Storage (primary persistence).
    4. If Google Drive is configured, upload the file to the Drive folder.
    5. Extract text via format-aware extractor, chunk it, and persist to
       Qdrant Cloud with full provenance metadata.
    6. Ensure rollback of Supabase object and tempfile deletion if extraction/chunking fails.
    """
    logger.info(
        f"Upload request: filename={file.filename!r} type={document_type} "
        f"user_id={current_user.id}"
    )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format '{file_ext}'. "
                f"Accepted formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
            ),
        )

    content_bytes = await file.read()
    size_mb = len(content_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File exceeds maximum allowed size of "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB. "
                f"Received: {size_mb:.2f} MB."
            ),
        )

    # Use NamedTemporaryFile
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
    temp_path = temp_file.name
    try:
        temp_file.write(content_bytes)
        temp_file.close()

        # Duplicate detection
        file_hash = compute_file_hash(temp_path)
        dup_info = check_duplicate(file_hash)

        if dup_info["is_duplicate"]:
            replace_mode = replace
            if not replace_mode:
                version_info = check_version_conflict(file.filename, file_hash)
                if version_info["is_version_conflict"]:
                    return UploadResponse(
                        status="version_conflict",
                        filename=file.filename,
                        document_type=document_type,
                        characters=0,
                        chunks=0,
                        file_hash=file_hash,
                        existing_filename=version_info.get("existing_filename"),
                        message=(
                            f"A different version of '{file.filename}' is already indexed. "
                            f"Re-upload with replace=true to update, or rename the file."
                        ),
                    )
                return UploadResponse(
                    status="duplicate",
                    filename=file.filename,
                    document_type=document_type,
                    characters=0,
                    chunks=0,
                    file_hash=file_hash,
                    existing_filename=dup_info.get("existing_filename"),
                    message=f"Document already indexed (identical to '{dup_info.get('existing_filename', 'unknown')}').",
                )
            else:
                logger.info(f"Replace mode: re-ingesting '{file.filename}'")

        # Upload to Supabase
        supabase_path = f"{document_type}/{file.filename}"
        supabase_upload_success = supabase_storage_service.upload_file(temp_path, supabase_path)
        if not supabase_upload_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload document to Supabase Storage."
            )

        # Qdrant metadata tracking
        extra_metadata: dict = {
            "source": "local_upload",
            "file_hash": file_hash,
            "supabase_storage_path": supabase_path,
            "storage_provider": "supabase"
        }

        background_tasks.add_task(
            _process_document_background,
            temp_path=temp_path,
            filename=file.filename,
            document_type=document_type,
            file_hash=file_hash,
            supabase_path=supabase_path,
            extra_metadata=extra_metadata
        )

        return UploadResponse(
            status="processing",
            filename=file.filename,
            document_type=document_type,
            characters=0,
            chunks=0,
            file_hash=file_hash,
            existing_filename=None,
            message="Document accepted and is processing in the background.",
            drive_upload_status="pending",
            drive_file_id=None,
            drive_web_view_link=None,
        )

    except Exception as exc:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise exc


@router.get(
    "/{document_type}/count",
    response_model=DocumentCountResponse,
    summary="Count stored chunks for a document type",
)
def get_document_count(
    document_type: str,
    current_user: User = Depends(get_current_user),
):
    docs = get_document_chunks_by_type(document_type)
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
    using the configured LLM. Sources include all chunk metadata, enabling
    the frontend to display Drive links when available.

    Supports optional file selection via selected_files parameter to restrict
    retrieval to specific documents.
    """
    logger.info(
        f"Q&A request: user_id={current_user.id} "
        f"question={payload.question[:100]!r} "
        f"selected_files={payload.selected_files}"
    )

    try:
        # ---- Retrieve relevant chunks ----
        results = retrieve_chunks(
            payload.question,
            selected_files=payload.selected_files,
        )
        chunks = results.get("documents", [])
        metadatas = results.get("metadata", [])
        distances = results.get("distances", [])

        if not chunks:
            return QuestionResponse(
                question=payload.question,
                answer=(
                    "No relevant documents found. "
                    "Please upload documents first or adjust your file selection."
                ),
                sources=[],
                diagnostics={
                    "matched_files": [],
                    "selected_files": payload.selected_files or [],
                    "retrieved_chunks_per_file": {},
                    "total_chunks": 0,
                    "retrieval_mode": "no_results",
                },
            )

        # ---- Format chunks with metadata headers ----
        formatted_chunks = []
        source_detail: dict[str, dict] = {}  # per-file aggregation

        for doc, meta, dist in zip(chunks, metadatas, distances):
            # FIX: Do NOT overwrite meta — it already contains valid Qdrant metadata
            if not meta:
                meta = {}
            filename = meta.get("filename", "Unknown")
            chunk_id = meta.get("id", str(uuid.uuid4())[:8])
            conf = max(0.0, 100.0 - (float(dist) * 100.0)) if dist is not None else 0.0
            page_num = meta.get("page_number", "N/A")
            heading = meta.get("section_heading", "N/A")

            header = (
                f"[File Name: {filename} | Page Number: {page_num} | "
                f"Chunk ID: {chunk_id} | Section Heading: {heading} | "
                f"Confidence Score: {conf:.1f}%]"
            )
            formatted_chunks.append(f"{header}\n{doc}")

            # Aggregate per-file source detail for enhanced attribution
            if filename not in source_detail:
                source_detail[filename] = {
                    "filename": filename,
                    "document_type": meta.get("document_type", "unknown"),
                    "chunks_used": 0,
                    "sections": [],
                    "confidence_scores": [],
                    "drive_web_view_link": meta.get("drive_web_view_link"),
                }
            source_detail[filename]["chunks_used"] += 1
            source_detail[filename]["confidence_scores"].append(conf)
            if heading and heading != "N/A" and heading not in source_detail[filename]["sections"]:
                source_detail[filename]["sections"].append(heading)

        # Build enhanced sources with average confidence per file
        enhanced_sources = []
        for fname_key, detail in source_detail.items():
            scores = detail.pop("confidence_scores")
            detail["confidence"] = round(sum(scores) / len(scores), 1) if scores else 0.0
            enhanced_sources.append(detail)
            
        # ---- Coverage Score & Diagnostics Injection ----
        total_searched = len(payload.selected_files) if payload.selected_files else len(results.get("matched_filenames", []))
        if total_searched == 0:
            total_searched = 1
        
        used_files_count = len(source_detail)
        coverage_ratio = used_files_count / total_searched
        
        if coverage_ratio > 0.8:
            coverage_score = "High"
        elif coverage_ratio >= 0.4:
            coverage_score = "Medium"
        else:
            coverage_score = "Low"
            
        from app.schemas.document import RetrievalDiagnostics
        
        diagnostics = RetrievalDiagnostics(
            strategy=results.get("retrieval_mode", "full_knowledge_base"),
            similarity=None, # TBD or from distances
            distribution=results.get("retrieved_chunks_per_filename", {}),
            deduplication=None, # TBD or computed
            coverage=f"{coverage_score} ({(coverage_ratio*100):.1f}%)",
            documents_searched=total_searched,
            documents_used=used_files_count,
            total_chunks=results.get("total_chunks_retrieved", 0)
        )

        # ---- Check LLM availability before LLM call ----
        from app.core.llm import check_llm_health
        if not check_llm_health():
            logger.error("LLM is not reachable")
            return QuestionResponse(
                question=payload.question,
                answer=(
                    "The AI language model is currently unavailable. "
                    "Please ensure GEMINI_API_KEY is valid and try again."
                ),
                sources=enhanced_sources,
                diagnostics=diagnostics,
            )

        # ---- Generate answer via LLM ----
        answer = generate_answer(
            question=payload.question,
            context_chunks=formatted_chunks,
            comparison_mode=(results.get("retrieval_mode") == "multi_document_comparison"),
        )
            
        # ---- Dynamic Suggested Questions (Sprint B) ----
        suggested_questions = []
        if payload.selected_files:
            file_str = " ".join(payload.selected_files).lower()
            if "risk" in file_str or "register" in file_str:
                suggested_questions.extend(["Show high-risk vendors", "Summarize vendor risks"])
            if "security" in file_str:
                suggested_questions.extend(["Summarize security controls", "Show MFA requirements"])
            if "continuity" in file_str or "disaster" in file_str or "recovery" in file_str:
                suggested_questions.extend(["Summarize recovery strategies", "Show continuity testing requirements"])
            if len(payload.selected_files) > 1:
                suggested_questions.extend(["Summarize access controls", "Compare incident response obligations"])
        
        # Fallback defaults if none matched
        if not suggested_questions:
            suggested_questions = [
                "What are the primary compliance risks identified?",
                "Summarize the key takeaways from these documents.",
                "What actions are required for compliance?"
            ]
            
        return QuestionResponse(
            question=payload.question,
            answer=answer,
            sources=enhanced_sources,
            diagnostics=diagnostics,
            suggested_questions=list(set(suggested_questions))[:4]
        )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as exc:
        logger.error(f"Ask question failed: {exc}", exc_info=True)
        return QuestionResponse(
            question=payload.question,
            answer=(
                "An unexpected error occurred while processing your question. "
                "Please try again or contact support if the issue persists."
            ),
            sources=[],
            diagnostics=None,
        )


@router.get(
    "/indexed-files",
    summary="List all indexed document filenames",
)
def list_indexed_files(
    current_user: User = Depends(get_current_user),
):
    """Return a list of all unique filenames currently indexed in Qdrant."""
    files = get_indexed_files()
    return {"files": files, "total": len(files)}


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
    policy_chunks = get_document_chunks_by_type("policy")
    regulation_chunks = get_document_chunks_by_type("regulation")

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
