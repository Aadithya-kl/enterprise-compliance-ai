from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models import AuditReport
from typing import List, Optional
import json
import logging

logger = logging.getLogger(__name__)


def save_audit_report(db: Session, report: dict) -> AuditReport:
    """
    Save a compliance report dict to the database.
    issues and recommendations are stored as JSON-encoded strings.
    """
    try:
        issues = report.get("issues", [])
        recommendations = report.get("recommendations", [])

        # Ensure lists are serialised as JSON strings
        issues_json = json.dumps(issues) if isinstance(issues, list) else issues
        recommendations_json = (
            json.dumps(recommendations)
            if isinstance(recommendations, list)
            else recommendations
        )

        audit = AuditReport(
            risk=report.get("risk", "Unknown"),
            compliance_score=int(report.get("compliance_score", 0)),
            violation_count=int(report.get("violation_count", 0)),
            issues=issues_json,
            recommendations=recommendations_json,
            audit_timestamp=report.get("audit_timestamp", ""),
            auditor=report.get("auditor", "Compliance AI Auditor"),
        )

        db.add(audit)
        db.commit()
        db.refresh(audit)

        logger.info(
            f"Saved audit report: id={audit.id}, risk={audit.risk}, "
            f"score={audit.compliance_score}"
        )
        return audit

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save audit report: {e}")
        raise


def get_all_audit_reports(db: Session) -> List[AuditReport]:
    """
    Retrieve all audit reports ordered by most recent first.
    Returns ORM objects that Pydantic will serialise via from_attributes.
    """
    try:
        reports = (
            db.query(AuditReport)
            .order_by(desc(AuditReport.created_at))
            .all()
        )
        logger.info(f"Retrieved {len(reports)} audit reports")
        return reports
    except Exception as e:
        logger.error(f"Failed to retrieve audit reports: {e}")
        raise


def get_audit_report_by_id(db: Session, report_id: int) -> Optional[AuditReport]:
    """Retrieve a single audit report by primary key."""
    try:
        report = (
            db.query(AuditReport)
            .filter(AuditReport.id == report_id)
            .first()
        )
        if report:
            logger.info(f"Retrieved audit report id={report_id}")
        else:
            logger.warning(f"Audit report id={report_id} not found")
        return report
    except Exception as e:
        logger.error(f"Failed to retrieve audit report id={report_id}: {e}")
        raise


def delete_audit_report(db: Session, report_id: int) -> bool:
    """
    Delete an audit report by ID.
    Returns True if deleted, False if not found.
    """
    try:
        report = (
            db.query(AuditReport)
            .filter(AuditReport.id == report_id)
            .first()
        )

        if not report:
            logger.warning(f"Audit report id={report_id} not found for deletion")
            return False

        db.delete(report)
        db.commit()
        logger.info(f"Deleted audit report id={report_id}")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete audit report id={report_id}: {e}")
        raise


def get_dashboard_stats(db: Session) -> dict:
    """
    Compute dashboard statistics from the audit_reports table.
    Uses SQLAlchemy func.avg() correctly (not db.func which doesn't exist).
    """
    try:
        total_audits = db.query(AuditReport).count()

        high_risk = (
            db.query(AuditReport)
            .filter(AuditReport.risk == "High")
            .count()
        )

        medium_risk = (
            db.query(AuditReport)
            .filter(AuditReport.risk == "Medium")
            .count()
        )

        low_risk = (
            db.query(AuditReport)
            .filter(AuditReport.risk == "Low")
            .count()
        )

        # BUG FIX: was `db.func.avg(...)` — db is a Session, not SQLAlchemy.
        # Correct usage is the imported `func` from sqlalchemy.
        avg_score = 0.0
        if total_audits > 0:
            result = db.query(
                func.avg(AuditReport.compliance_score)
            ).scalar()
            avg_score = float(result) if result is not None else 0.0

        stats = {
            "total_audits": total_audits,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "average_compliance_score": round(avg_score, 2),
        }

        logger.info(f"Dashboard stats computed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Failed to compute dashboard stats: {e}")
        raise
