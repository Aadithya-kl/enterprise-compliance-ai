from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.models.base import Base

class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    source = Column(String, nullable=False) # e.g. "google_drive", "notion", "all"
    status = Column(String, default="Starting Sync...")
    documents_processed = Column(Integer, default=0)
    total_documents = Column(Integer, default=0)
    chunks_generated = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
