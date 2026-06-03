from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Please configure your .env file."
    )

# Supabase uses PostgreSQL over SSL; pool_pre_ping prevents stale connections.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,        # Detects broken connections before using them
    pool_recycle=300,          # Recycle connections every 5 minutes
    pool_size=5,               # Maximum persistent connections
    max_overflow=10,           # Allow up to 10 extra connections under load
    connect_args={
        "sslmode": "require",  # Supabase requires SSL
        "connect_timeout": 10, # Fail fast on connection issues
    },
    echo=False,                # Set to True for SQL debug logging
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()