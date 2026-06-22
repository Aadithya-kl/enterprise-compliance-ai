"""
Integration configuration ORM model.
Controls the activation status of integrations like Notion and Google Drive.
"""

from sqlalchemy import Boolean, Column, Integer, String
from app.models.base import Base

class IntegrationConfig(Base):
    """Configuration record for external integrations (MCP sources)."""

    __tablename__ = "integration_configs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    source_name = Column(String(50), unique=True, nullable=False, index=True) # e.g. "google_drive", "notion"
    is_enabled = Column(Boolean, nullable=False, default=False)
