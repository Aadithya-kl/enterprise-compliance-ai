from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.mcp.google_drive import GoogleDriveMCPSource
from app.mcp.notion import NotionMCPSource
from app.core.logging import get_logger

router = APIRouter(prefix="/health", tags=["System Health"])
logger = get_logger(__name__)

@router.get("", summary="Detailed System Health Check")
def health_check(db: Session = Depends(get_db)):
    """Return detailed health status of all core components and external integrations."""
    health = {
        "database": "unhealthy",
        "chromadb": "unhealthy",
        "ollama": "unhealthy",
        "google_drive": "unhealthy",
        "notion": "unhealthy",
        "backend": "healthy",
    }

    # 1. Database
    try:
        db.execute("SELECT 1")
        health["database"] = "healthy"
    except Exception as exc:
        logger.error(f"Health Check - DB Error: {exc}")

    # 2. ChromaDB
    try:
        from app.services.rag_service import _collection
        _collection.count()
        health["chromadb"] = "healthy"
    except Exception as exc:
        logger.error(f"Health Check - ChromaDB Error: {exc}")

    # 3. Ollama
    try:
        import requests
        # Use host.docker.internal if running in Docker to hit the Windows host proxy
        # but realistically just test the configured endpoint.
        # Hardcoding the test to localhost:11434 proxy
        resp = requests.get("http://host.docker.internal:11435/api/tags", timeout=2)
        if resp.status_code == 200:
            health["ollama"] = "healthy"
    except Exception as exc:
        logger.error(f"Health Check - Ollama Error: {exc}")

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
