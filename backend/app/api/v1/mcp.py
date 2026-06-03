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
