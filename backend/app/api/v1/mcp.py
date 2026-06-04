"""
MCP router.
POST /api/v1/mcp/sync — trigger sync from all configured MCP sources
GET  /api/v1/mcp/sources — list configured and available sources
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.core.dependencies import get_admin
from app.core.logging import get_logger
from app.mcp.google_drive import GoogleDriveMCPSource
from app.mcp.local_files import LocalFilesMCPSource
from app.mcp.notion import NotionMCPSource
from app.models.user import User
from app.services.rag_service import chunk_text, store_document_chunks

router = APIRouter(prefix="/mcp", tags=["MCP Integrations"])
logger = get_logger(__name__)

_SOURCES = [
    LocalFilesMCPSource(),
    GoogleDriveMCPSource(),
    NotionMCPSource(),
]


class SyncResult(BaseModel):
    source: str
    configured: bool
    documents_ingested: int
    errors: list[str]


class SyncResponse(BaseModel):
    total_documents_ingested: int
    results: list[SyncResult]


class SourceInfo(BaseModel):
    source: str
    configured: bool


@router.get(
    "/sources",
    response_model=list[SourceInfo],
    summary="List all MCP sources and their configuration status",
)
def list_sources(_admin: User = Depends(get_admin)):
    return [
        SourceInfo(source=s.source_name, configured=s.is_configured())
        for s in _SOURCES
    ]


@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Sync documents from all configured MCP sources (admin only)",
)
def sync_all_sources(_admin: User = Depends(get_admin)):
    """
    Iterates all configured MCP sources, fetches documents,
    chunks them, and stores in ChromaDB for RAG retrieval.
    """
    results: list[SyncResult] = []
    total_ingested = 0

    for source in _SOURCES:
        errors: list[str] = []
        ingested = 0

        if not source.is_configured():
            results.append(
                SyncResult(
                    source=source.source_name,
                    configured=False,
                    documents_ingested=0,
                    errors=[],
                )
            )
            continue

        try:
            documents = source.fetch_documents()
        except Exception as exc:
            logger.error(
                f"MCP sync error [{source.source_name}]: {exc}", exc_info=True
            )
            results.append(
                SyncResult(
                    source=source.source_name,
                    configured=True,
                    documents_ingested=0,
                    errors=[str(exc)],
                )
            )
            continue

        for doc in documents:
            try:
                chunks = chunk_text(doc.content)
                store_document_chunks(
                    chunks,
                    filename=f"{source.source_name}:{doc.title}",
                    document_type=doc.document_type,
                )
                ingested += 1
            except Exception as exc:
                logger.error(
                    f"MCP ingest error [{source.source_name}/{doc.title}]: {exc}"
                )
                errors.append(f"{doc.title}: {exc}")

        total_ingested += ingested
        results.append(
            SyncResult(
                source=source.source_name,
                configured=True,
                documents_ingested=ingested,
                errors=errors,
            )
        )
        logger.info(
            f"MCP sync [{source.source_name}]: {ingested} documents ingested"
        )

    logger.info(f"MCP sync complete: {total_ingested} total documents ingested")
    return SyncResponse(total_documents_ingested=total_ingested, results=results)


# ---------------------------------------------------------------------------
# Google Drive — dedicated sync endpoint
# ---------------------------------------------------------------------------


class GoogleDriveSyncResponse(BaseModel):
    """Response returned by the Google Drive dedicated sync endpoint."""
    documents_found: int
    documents_processed: int
    chunks_created: int
    status: str


class GoogleDriveVerifyResponse(BaseModel):
    """Detailed diagnostic response from the Google Drive verify endpoint."""
    connected: bool
    credentials_file_exists: bool
    service_account_loaded: bool
    drive_client_initialized: bool
    folder_accessible: bool
    message: str


_google_drive_source = GoogleDriveMCPSource()


@router.post(
    "/google-drive/sync",
    response_model=GoogleDriveSyncResponse,
    summary="Sync PDF documents from the configured Google Drive folder (admin only)",
)
def sync_google_drive(_admin: User = Depends(get_admin)):
    """
    Fetches all PDF files from the configured Google Drive folder,
    extracts text, chunks it, and stores it in ChromaDB for RAG retrieval.

    Only files not already present in ChromaDB are downloaded (incremental sync).
    Sub-folders are traversed recursively.
    Full pagination is used — handles folders with more than 100 files.
    """
    if not _google_drive_source.is_configured():
        from fastapi import HTTPException, status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google Drive integration is not configured. "
                "Set GOOGLE_DRIVE_ENABLED=true, GOOGLE_SERVICE_ACCOUNT_FILE, "
                "and GOOGLE_DRIVE_FOLDER_ID in .env."
            ),
        )

    try:
        documents = _google_drive_source.fetch_documents()
    except Exception as exc:
        logger.error(f"Google Drive sync error: {exc}", exc_info=True)
        from fastapi import HTTPException, status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google Drive sync failed: {exc}",
        )

    total_chunks = 0
    processed = 0

    for doc in documents:
        try:
            chunks = chunk_text(doc.content)
            # Pass all Drive metadata (source, drive_file_id, drive_file_name,
            # drive_web_view_link) into ChromaDB so MCP-synced chunks are
            # indistinguishable from upload-pipeline chunks for RAG retrieval
            # and incremental sync deduplication.
            store_document_chunks(
                chunks,
                filename=doc.title,
                document_type=doc.document_type,
                extra_metadata=doc.metadata or {},
            )
            total_chunks += len(chunks)
            processed += 1
        except Exception as exc:
            logger.error(
                f"Google Drive ingest error [{doc.title}]: {exc}"
            )

    logger.info(
        f"Google Drive sync complete: {processed}/{len(documents)} documents processed, "
        f"{total_chunks} chunks created."
    )

    return GoogleDriveSyncResponse(
        documents_found=len(documents),
        documents_processed=processed,
        chunks_created=total_chunks,
        status="success",
    )


@router.get(
    "/google-drive/verify",
    response_model=GoogleDriveVerifyResponse,
    summary="Verify Google Drive API connection and folder access (admin only)",
)
def verify_google_drive_connection(_admin: User = Depends(get_admin)):
    """
    Tests Google Drive connectivity step by step:
    1. Confirms credential file exists on disk.
    2. Loads and validates service account credentials.
    3. Initializes the Drive API client.
    4. Verifies folder access.

    Returns per-step diagnostic flags so the operator can pinpoint the failure.
    The most common failure is step 4 (folder_accessible=false), which means
    the Google Drive folder has not been shared with the service account email.
    """
    # Create a fresh instance to avoid stale module-level singleton
    source = GoogleDriveMCPSource()
    result = source.verify_connection()
    return GoogleDriveVerifyResponse(
        connected=result["ok"],
        credentials_file_exists=result.get("credentials_file_exists", False),
        service_account_loaded=result.get("service_account_loaded", False),
        drive_client_initialized=result.get("drive_client_initialized", False),
        folder_accessible=result.get("folder_accessible", False),
        message=result["message"],
    )
