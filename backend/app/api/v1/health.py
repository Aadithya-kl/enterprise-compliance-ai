from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.mcp.google_drive import GoogleDriveMCPSource
from app.mcp.notion import NotionMCPSource
from app.core.logging import get_logger
from app.services.ingestion import get_collection_count

router = APIRouter(prefix="/health", tags=["System Health"])
logger = get_logger(__name__)

@router.get("", summary="Detailed System Health Check")
def health_check(db: Session = Depends(get_db)):
    """Return detailed health status of all core components and external integrations."""
    health = {
        "database": "unhealthy",
        "qdrant": "unhealthy",
        "supabase": "unhealthy",
        "llm": "unhealthy",
        "google_drive": "unhealthy",
        "notion": "unhealthy",
        "backend": "healthy",
    }

    # 1. Database
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        health["database"] = "healthy"
    except Exception as exc:
        logger.error(f"Health Check - DB Error: {exc}")

    # 2. Qdrant
    try:

        get_collection_count()
        health["qdrant"] = "healthy"
    except Exception as exc:
        logger.error(f"Health Check - Qdrant Error: {exc}")

    # 3. Supabase Storage
    try:
        from app.services.supabase_storage import supabase_storage_service
        if supabase_storage_service.is_configured():
            health["supabase"] = "healthy"
        else:
            health["supabase"] = "not_configured"
    except Exception as exc:
        logger.error(f"Health Check - Supabase Error: {exc}")

    # 4. LLM (Gemini)
    try:
        from app.core.llm import check_llm_health
        if check_llm_health():
            health["llm"] = "healthy"
        else:
            health["llm"] = "unhealthy"
            logger.error("Health Check - Gemini Error: Client not initialized")
    except Exception as exc:
        logger.error(f"Health Check - Gemini Error: {exc}")

    # 4. Google Drive MCP
    try:
        gdrive = GoogleDriveMCPSource()
        if gdrive.is_configured():
            res = gdrive.verify_connection()
            health["google_drive"] = "healthy" if res.get("ok") else "error"
        else:
            health["google_drive"] = "not_configured"
    except Exception as exc:
        logger.error(f"Health Check - Google Drive Error: {exc}")

    # 5. Notion MCP
    try:
        notion = NotionMCPSource()
        if notion.is_configured():
            res = notion.verify_connection()
            health["notion"] = "healthy" if res.get("ok") else "error"
        else:
            health["notion"] = "not_configured"
    except Exception as exc:
        logger.error(f"Health Check - Notion Error: {exc}")

    return health
