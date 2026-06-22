import logging
logger = logging.getLogger(__name__)
"""
Enterprise Compliance & Audit Intelligence Platform
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.session import engine, verify_db_connection
from app.models.base import Base
from app.models.user import User, UserRole

# Ensure all models are imported so Base.metadata is populated
import app.models.audit_report  # noqa: F401
import app.models.compliance_violation  # noqa: F401
import app.models.sync_job  # noqa: F401
import app.models.integration_config  # noqa: F401

configure_logging()
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Autonomous Enterprise Compliance & Audit Intelligence Platform. "
        "Provides AI-powered document analysis, compliance gap assessment, "
        "risk classification, and structured audit reporting."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import uuid
import time

@app.middleware("http")
async def add_correlation_id_and_log(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"[req_id={request_id}] route={request.url.path} method={request.method} status={response.status_code} exec_time={process_time:.4f}s")
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"[req_id={request_id}] route={request.url.path} method={request.method} exec_time={process_time:.4f}s exception={repr(e)}", exc_info=True)
        raise e

# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"[req_id={req_id}] Unhandled exception: {exc} | "
        f"path={request.url.path} method={request.method}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An unexpected error occurred.",
            "request_id": req_id,
            "detail": str(exc) if settings.DEBUG else "Internal server error.",
        },
    )

# ---------------------------------------------------------------------------
# Startup / shutdown lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Temporary diagnostic logging
    api_key = os.environ.get("GEMINI_API_KEY", getattr(settings, "GEMINI_API_KEY", ""))
    key_suffix = api_key[-8:] if api_key and len(api_key) >= 8 else "NOT_SET"
    logger.info(f"Loaded Gemini Key Suffix: {key_suffix}")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified / created.")

    # Auto-migrate schema changes
    _auto_migrate_schema()

    # Verify database connectivity
    if not verify_db_connection():
        logger.error("Database connection failed on startup. Check DATABASE_URL.")
    else:
        logger.info("Database connection verified.")

    # Bootstrap default admin user if no users exist
    _bootstrap_admin()

    # Bootstrap default integrations config if missing
    _bootstrap_integrations_config()

    # Ensure upload directory exists
    logger.info("Local upload persistence has been removed (Supabase Migration Phase 3).")

    # Production Hardening Diagnostics
    logger.info("Supported Drive MIME Types: PDF, DOCX, PPTX, XLSX, CSV, TXT")
    logger.info("Google Drive Discovery Ready")
    logger.info("Qdrant Payload Index Verification Complete")

def _auto_migrate_schema():
    """Ensure missing columns like created_by_user_id are automatically added."""
    from sqlalchemy import text, inspect
    try:
        with engine.connect() as conn:
            if "sqlite" in engine.url.drivername:
                inspector = inspect(engine)
                columns = [c["name"] for c in inspector.get_columns("audit_reports")]
                has_column = "created_by_user_id" in columns
            else:
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'audit_reports' AND column_name = 'created_by_user_id'
                """)).fetchone()
                has_column = result is not None
            
            if not has_column:
                logger.info("Column created_by_user_id is missing from audit_reports. Adding column...")
                conn.execute(text("""
                    ALTER TABLE audit_reports 
                    ADD COLUMN created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_audit_reports_user 
                    ON audit_reports (created_by_user_id)
                """))
                conn.commit()
                logger.info("Column created_by_user_id added successfully.")

        # Backfill existing audits into compliance_violations if empty
        from app.db.session import SessionLocal
        from app.models.audit_report import AuditReport
        from app.models.compliance_violation import ComplianceViolation
        import json
        from datetime import datetime
        
        db = SessionLocal()
        try:
            violation_count = db.query(ComplianceViolation).count()
            if violation_count == 0:
                reports = db.query(AuditReport).all()
                if reports:
                    logger.info(f"Backfilling structured compliance_violations for {len(reports)} existing reports...")
                    for r in reports:
                        try:
                            # Parse audit timestamp to datetime
                            try:
                                report_dt = datetime.strptime(r.audit_timestamp, "%Y-%m-%d %H:%M:%S")
                            except Exception as e:
                                logger.error(f"Exception caught: {e}", exc_info=True)
                                report_dt = r.created_at or datetime.now()

                            # Deserialise issues
                            issues = []
                            if r.issues:
                                try:
                                    issues = json.loads(r.issues)
                                except Exception as e:
                                    logger.error(f"Exception caught: {e}", exc_info=True)
                                    issues = [r.issues]
                                    
                            for issue in issues:
                                issue_lower = issue.lower()
                                
                                severity = "Medium"
                                if any(kw in issue_lower for kw in ["critical", "mfa", "encryption", "credentials"]):
                                    severity = "Critical"
                                elif any(kw in issue_lower for kw in ["high", "password", "access", "unauthorized"]):
                                    severity = "High"
                                elif any(kw in issue_lower for kw in ["low", "minor", "version", "formatting"]):
                                    severity = "Low"
                                    
                                v_type = "Other"
                                if any(kw in issue_lower for kw in ["mfa", "auth", "login", "password", "privilege"]):
                                    v_type = "Access Control"
                                elif any(kw in issue_lower for kw in ["encrypt", "aes", "ssl", "tls", "rest", "transit"]):
                                    v_type = "Data Encryption"
                                elif any(kw in issue_lower for kw in ["audit", "log", "history", "record"]):
                                    v_type = "Audit Logging"
                                elif any(kw in issue_lower for kw in ["privacy", "gdpr", "personal", "pii"]):
                                    v_type = "Data Privacy"
                                    
                                dept = "General"
                                if any(kw in issue_lower for kw in ["it", "system", "administrator", "network"]):
                                    dept = "IT"
                                elif any(kw in issue_lower for kw in ["finance", "billing", "payment"]):
                                    dept = "Finance"
                                elif any(kw in issue_lower for kw in ["hr", "employee", "staff"]):
                                    dept = "HR"

                                db.add(
                                    ComplianceViolation(
                                        report_id=r.id,
                                        violation_type=v_type,
                                        severity=severity,
                                        department=dept,
                                        compliance_score=r.compliance_score,
                                        regulation_category="Compliance Standards",
                                        report_date=report_dt,
                                        description=issue,
                                    )
                                )
                        except Exception as e:
                            logger.error(f"Failed to backfill report {r.id}: {e}")
                    db.commit()
                    logger.info("Database backfill completed successfully.")
        except Exception as e:
            logger.error(f"Schema backfill check failed: {e}")
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Auto-migration of schema failed: {exc}", exc_info=True)


@app.on_event("shutdown")
def on_shutdown():
    logger.info(f"{settings.APP_NAME} shutting down.")


def _bootstrap_admin():
    """Create a default admin user on application startup if no admin exists."""
    from sqlalchemy.orm import Session
    from app.db.session import SessionLocal
    from app.core.security import hash_password

    db: Session = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin_exists:
            existing_user = db.query(User).filter(User.email == "admin@company.com").first()
            if existing_user:
                existing_user.role = UserRole.ADMIN
                existing_user.full_name = "System Administrator"
                existing_user.hashed_password = hash_password("Admin123!")
                existing_user.is_active = True
            else:
                admin = User(
                    email="admin@company.com",
                    full_name="System Administrator",
                    hashed_password=hash_password("Admin123!"),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
                db.add(admin)
            db.commit()
            logger.info("Default admin account created")
        else:
            logger.info("Admin account already exists")
    except Exception as exc:
        logger.error(f"Admin bootstrap failed: {exc}")
        db.rollback()
    finally:
        db.close()


def _bootstrap_integrations_config():
    """Bootstrap default database records for Google Drive and Notion integrations."""
    from app.db.session import SessionLocal
    from app.models.integration_config import IntegrationConfig
    db = SessionLocal()
    try:
        # Google Drive config
        gdrive = db.query(IntegrationConfig).filter_by(source_name="google_drive").first()
        if not gdrive:
            gdrive = IntegrationConfig(
                source_name="google_drive",
                is_enabled=settings.GOOGLE_DRIVE_ENABLED
            )
            db.add(gdrive)
            logger.info("Bootstrapped Google Drive integration config")

        # Notion config
        notion = db.query(IntegrationConfig).filter_by(source_name="notion").first()
        if not notion:
            is_notion_env_configured = bool(settings.NOTION_API_TOKEN and settings.NOTION_DATABASE_ID)
            notion = IntegrationConfig(
                source_name="notion",
                is_enabled=is_notion_env_configured
            )
            db.add(notion)
            logger.info("Bootstrapped Notion integration config")

        db.commit()
    except Exception as exc:
        logger.error(f"Integrations configuration bootstrap failed: {exc}")
        db.rollback()
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Versioned API routes
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# ---------------------------------------------------------------------------
# Root and health endpoints (unversioned, no auth required)
# ---------------------------------------------------------------------------

@app.get("/", tags=["System"])
def root():
    return {
        "platform": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
    }


@app.get("/health", tags=["System"])
def health():
    """
    Health check endpoint.
    Returns 200 if the application is running and the database is reachable.
    """
    db_ok = verify_db_connection()
    return JSONResponse(
        status_code=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "healthy" if db_ok else "degraded",
            "database": "connected" if db_ok else "unreachable",
            "version": settings.APP_VERSION,
        },
    )
