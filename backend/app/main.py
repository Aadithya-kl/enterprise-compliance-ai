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

# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception: {exc} | "
        f"path={request.url.path} method={request.method}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An unexpected error occurred.",
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

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")


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
