"""
MCP router.
POST /api/v1/mcp/sync — trigger sync from all configured MCP sources
GET  /api/v1/mcp/sources — list configured and available sources
"""

from fastapi import APIRouter, Depends, status, BackgroundTasks
from pydantic import BaseModel

from app.core.dependencies import get_admin, require_role
from app.core.logging import get_logger
from app.mcp.google_drive import GoogleDriveMCPSource
from app.mcp.notion import NotionMCPSource
from app.models.user import User
from app.services.ingestion import (
    chunk_text,
    store_document_chunks,
    get_document_metadata,
)

router = APIRouter(prefix="/mcp", tags=["MCP Integrations"])
logger = get_logger(__name__)

_SOURCES = [
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


class IntegrationToggleRequest(BaseModel):
    is_enabled: bool


@router.get(
    "/integrations",
    summary="Get all integration activation statuses (admin only)",
)
def get_integrations(current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
    from app.db.session import SessionLocal
    from app.models.integration_config import IntegrationConfig
    db = SessionLocal()
    try:
        configs = db.query(IntegrationConfig).all()
        return {c.source_name: c.is_enabled for c in configs}
    finally:
        db.close()


@router.patch(
    "/integrations/{source_name}",
    summary="Toggle activation status of an integration (admin only)",
)
def toggle_integration(source_name: str, payload: IntegrationToggleRequest, current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
    from app.db.session import SessionLocal
    from app.models.integration_config import IntegrationConfig
    from fastapi import HTTPException
    
    if source_name not in ["google_drive", "notion"]:
        raise HTTPException(status_code=400, detail="Invalid source name")
        
    db = SessionLocal()
    try:
        config = db.query(IntegrationConfig).filter_by(source_name=source_name).first()
        if not config:
            config = IntegrationConfig(source_name=source_name, is_enabled=payload.is_enabled)
            db.add(config)
        else:
            config.is_enabled = payload.is_enabled
        db.commit()
        return {"status": "success", "source": source_name, "is_enabled": config.is_enabled}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get(
    "/sources",
    response_model=list[SourceInfo],
    summary="List all MCP sources and their configuration status",
)
def list_sources(current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
    return [
        SourceInfo(source=s.source_name, configured=s.is_configured())
        for s in _SOURCES
    ]



@router.post(
    "/sync",
    response_model=SyncResponse,
    summary="Sync documents from all configured MCP sources (admin only)",
)
def sync_all_sources(current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
    """
    Iterates all configured MCP sources, fetches documents,
    chunks them, and stores in Qdrant for RAG retrieval.
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


class MCPStatsResponse(BaseModel):
    sources_connected: int
    total_documents: int
    total_chunks: int
    last_sync: str

@router.get(
    "/stats",
    response_model=dict[str, MCPStatsResponse],
    summary="Get metrics for all MCP integrations",
)
def get_mcp_stats(current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
    """Returns knowledge source metrics for the dashboard widget."""
    
    stats = {}
    sources = ["supabase_storage", "google_drive", "notion"]
    
    try:
        metadatas = get_document_metadata()
        
        for source_name in sources:
            if source_name == "supabase_storage":
                # Catch all local/uploaded docs to ensure identical total counts
                source_metas = [m for m in metadatas if m and m.get("source") not in ["google_drive", "notion"]]
            else:
                source_metas = [m for m in metadatas if m and m.get("source") == source_name]
            
            # Count unique documents purely by filename to perfectly match get_indexed_files()
            unique_docs = set()
            for m in source_metas:
                fname = m.get("filename")
                if fname:
                    unique_docs.add(fname)
                    
            is_connected = False
            if source_name == "supabase_storage":
                from app.services.supabase_storage import supabase_storage_service
                is_connected = supabase_storage_service.is_configured()
            elif source_name == "google_drive":
                is_connected = GoogleDriveMCPSource().is_configured()
            elif source_name == "notion":
                is_connected = NotionMCPSource().is_configured()
                
            stats[source_name] = MCPStatsResponse(
                sources_connected=1 if is_connected else 0,
                total_documents=len(unique_docs),
                total_chunks=len(source_metas),
                last_sync="Recently" if source_metas else "Never"
            )
            
    except Exception as exc:
        logger.error(f"Failed to fetch MCP stats from Qdrant: {exc}")
        # Return empty stats on failure
        for source_name in sources:
            stats[source_name] = MCPStatsResponse(
                sources_connected=0, total_documents=0, total_chunks=0, last_sync="Error"
            )
            
    return stats


# ---------------------------------------------------------------------------
# Google Drive — dedicated sync endpoint
# ---------------------------------------------------------------------------


class SyncJobResponse(BaseModel):
    job_id: str
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

def _process_google_drive_sync_background(job_id: str):
    from app.db.session import SessionLocal
    from app.models.sync_job import SyncJob
    from datetime import datetime
    import time
    
    db = SessionLocal()
    job = db.query(SyncJob).filter(SyncJob.job_id == job_id).first()
    if not job:
        db.close()
        return
        
    try:
        job.status = "Discovering Documents..."
        db.commit()
        
        documents = _google_drive_source.fetch_documents()
        total_docs = len(documents)
        job.total_documents = total_docs
        job.status = f"Processing 0 of {total_docs} Files..."
        db.commit()
        
        processed = 0
        total_chunks = 0
        for doc in documents:
            try:
                chunks = chunk_text(doc.content)
                store_document_chunks(
                    chunks,
                    filename=doc.title,
                    document_type=doc.document_type,
                    extra_metadata=doc.metadata or {},
                )
                total_chunks += len(chunks)
                processed += 1
                
                # Update progress
                job.documents_processed = processed
                job.chunks_generated = total_chunks
                job.status = f"Processing {processed} of {total_docs} Files..."
                db.commit()
            except Exception as exc:
                logger.error(f"Google Drive ingest error [{doc.title}]: {exc}")
                
        job.status = "Sync Complete"
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Google Drive background sync complete: {processed} processed, {total_chunks} chunks.")
    except Exception as exc:
        job.status = f"Failed: {str(exc)}"
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.error(f"Google Drive background sync failed: {exc}", exc_info=True)
    finally:
        db.close()

@router.post(
    "/google-drive/sync",
    response_model=SyncJobResponse,
    summary="Sync PDF documents from the configured Google Drive folder (admin only)",
)
def sync_google_drive(background_tasks: BackgroundTasks, current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
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

    import uuid
    from app.db.session import SessionLocal
    from app.models.sync_job import SyncJob
    
    job_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        new_job = SyncJob(
            job_id=job_id,
            source="google_drive",
            status="Starting Sync..."
        )
        db.add(new_job)
        db.commit()
    finally:
        db.close()

    background_tasks.add_task(_process_google_drive_sync_background, job_id)

    return SyncJobResponse(job_id=job_id, status="Starting Sync...")


@router.get(
    "/google-drive/verify",
    response_model=GoogleDriveVerifyResponse,
    summary="Verify Google Drive API connection and folder access (admin only)",
)
def verify_google_drive_connection(current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
    """Tests Google Drive connectivity step by step."""
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


# ---------------------------------------------------------------------------
# Notion — dedicated sync endpoint
# ---------------------------------------------------------------------------

class NotionVerifyResponse(BaseModel):
    """Detailed diagnostic response from the Notion verify endpoint."""
    connected: bool
    api_token_set: bool
    database_id_set: bool
    client_initialized: bool
    database_accessible: bool
    message: str

_notion_source = NotionMCPSource()

def _process_notion_sync_background(job_id: str):
    from app.db.session import SessionLocal
    from app.models.sync_job import SyncJob
    from datetime import datetime
    
    db = SessionLocal()
    job = db.query(SyncJob).filter(SyncJob.job_id == job_id).first()
    if not job:
        db.close()
        return
        
    try:
        job.status = "Discovering Documents..."
        db.commit()
        
        documents = _notion_source.fetch_documents()
        total_docs = len(documents)
        job.total_documents = total_docs
        job.status = f"Processing 0 of {total_docs} Files..."
        db.commit()

        total_chunks = 0
        processed = 0

        for doc in documents:
            try:
                chunks = chunk_text(doc.content)
                store_document_chunks(
                    chunks,
                    filename=doc.title,
                    document_type=doc.document_type,
                    extra_metadata=doc.metadata or {},
                )
                total_chunks += len(chunks)
                processed += 1
                
                # Update progress
                job.documents_processed = processed
                job.chunks_generated = total_chunks
                job.status = f"Processing {processed} of {total_docs} Files..."
                db.commit()
            except Exception as exc:
                logger.error(f"Notion ingest error [{doc.title}]: {exc}")

        job.status = "Sync Complete"
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Notion background sync complete: {processed}/{total_docs} documents processed, {total_chunks} chunks created.")
    except Exception as exc:
        job.status = f"Failed: {str(exc)}"
        job.completed_at = datetime.utcnow()
        db.commit()
        logger.error(f"Notion background sync failed: {exc}", exc_info=True)
    finally:
        db.close()

@router.post(
    "/notion/sync",
    response_model=SyncJobResponse,
    summary="Sync pages from the configured Notion database (admin only)",
)
def sync_notion(background_tasks: BackgroundTasks, current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
    if not _notion_source.is_configured():
        from fastapi import HTTPException, status as http_status
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notion integration is not configured. Set NOTION_API_TOKEN and NOTION_DATABASE_ID in .env.",
        )

    import uuid
    from app.db.session import SessionLocal
    from app.models.sync_job import SyncJob
    
    job_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        new_job = SyncJob(
            job_id=job_id,
            source="notion",
            status="Starting Sync..."
        )
        db.add(new_job)
        db.commit()
    finally:
        db.close()

    background_tasks.add_task(_process_notion_sync_background, job_id)

    return SyncJobResponse(job_id=job_id, status="Starting Sync...")

@router.get(
    "/sync/status/{job_id}",
    summary="Get the status of a background sync job",
)
def get_sync_status(job_id: str, current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
    from fastapi import HTTPException
    from app.db.session import SessionLocal
    from app.models.sync_job import SyncJob
    
    db = SessionLocal()
    try:
        job = db.query(SyncJob).filter(SyncJob.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Sync job not found")
            
        return {
            "job_id": job.job_id,
            "status": job.status,
            "documents_processed": job.documents_processed,
            "total_documents": job.total_documents,
            "chunks_generated": job.chunks_generated,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }
    finally:
        db.close()

@router.get(
    "/notion/verify",
    response_model=NotionVerifyResponse,
    summary="Verify Notion API connection and database access (admin only)",
)
def verify_notion_connection(current_user: User = Depends(require_role(["admin", "compliance_officer"]))):
    """Tests Notion connectivity step by step."""
    source = NotionMCPSource()
    result = source.verify_connection()
    return NotionVerifyResponse(
        connected=result["ok"],
        api_token_set=result.get("api_token_set", False),
        database_id_set=result.get("database_id_set", False),
        client_initialized=result.get("client_initialized", False),
        database_accessible=result.get("database_accessible", False),
        message=result["message"],
    )
