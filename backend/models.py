from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Index
from sqlalchemy.sql import func
from database import Base


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    risk = Column(
        String,
        nullable=False,
        index=True
    )

    compliance_score = Column(
        Integer,
        nullable=False,
        index=True
    )

    violation_count = Column(
        Integer,
        nullable=False
    )

    issues = Column(
        Text,
        nullable=False
    )

    recommendations = Column(
        Text,
        nullable=False
    )

    audit_timestamp = Column(
        String,
        nullable=False,
        index=True
    )

    auditor = Column(
        String,
        nullable=False,
        default="Compliance AI Auditor"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        Index('idx_risk_timestamp', 'risk', 'audit_timestamp'),
    )