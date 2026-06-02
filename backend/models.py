from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from database import Base


class AuditReport(Base):

    __tablename__ = "audit_reports"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    risk = Column(
        String
    )

    compliance_score = Column(
        Integer
    )

    violation_count = Column(
        Integer
    )

    issues = Column(
        Text
    )

    recommendations = Column(
        Text
    )

    audit_timestamp = Column(
        String
    )

    auditor = Column(
        String
    )