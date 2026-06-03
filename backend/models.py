from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from database import Base


class AuditReport(Base):
    """SQLAlchemy ORM model for audit reports stored in Supabase PostgreSQL."""

    __tablename__ = "audit_reports"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    risk = Column(
        String(20),
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
        nullable=False,
        default=0
    )

    # Stored as JSON-encoded strings (Text) for broad DB compatibility
    issues = Column(
        Text,
        nullable=False,
        default="[]"
    )

    recommendations = Column(
        Text,
        nullable=False,
        default="[]"
    )

    audit_timestamp = Column(
        String(30),
        nullable=False,
        index=True
    )

    auditor = Column(
        String(100),
        nullable=False,
        default="Compliance AI Auditor"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )

    __table_args__ = (
        Index("idx_risk_timestamp", "risk", "audit_timestamp"),
    )

    def __repr__(self):
        return (
            f"<AuditReport id={self.id} risk={self.risk} "
            f"score={self.compliance_score}>"
        )