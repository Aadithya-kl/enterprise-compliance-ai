from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SyncStatusResponse(BaseModel):
    job_id: str
    status: str
    documents_processed: int
    total_documents: int
    chunks_generated: int
    started_at: datetime
    completed_at: Optional[datetime] = None
