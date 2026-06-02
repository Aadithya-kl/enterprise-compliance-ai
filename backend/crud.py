from sqlalchemy.orm import Session
from models import AuditReport
from sqlalchemy import desc
from typing import List, Optional
import json


def save_audit_report(db: Session, report: dict) -> AuditReport:
    """Save a compliance report to the database."""
    try:
        audit = AuditReport(
            risk=report.get("risk", "Unknown"),
            compliance_score=report.get("compliance_score", 0),
            violation_count=report.get("violation_count", 0),
            issues=json.dumps(report.get("issues", [])),
            recommendations=json.dumps(report.get("recommendations", [])),
            audit_timestamp=report.get("audit_timestamp", ""),
            auditor=report.get("auditor", "Compliance AI Auditor")
        )
        
        db.add(audit)
        db.commit()
        db.refresh(audit)
        
        return audit
    except Exception as e:
        db.rollback()
        raise e


def get_all_audit_reports(db: Session) -> List[AuditReport]:
    """Get all audit reports from the database, ordered by latest first."""
    try:
        reports = db.query(AuditReport).order_by(
            desc(AuditReport.created_at)
        ).all()
        return reports
    except Exception as e:
        raise e


def get_audit_report_by_id(db: Session, report_id: int) -> Optional[AuditReport]:
    """Get a specific audit report by ID."""
    try:
        report = db.query(AuditReport).filter(
            AuditReport.id == report_id
        ).first()
        return report
    except Exception as e:
        raise e


def delete_audit_report(db: Session, report_id: int) -> bool:
    """Delete an audit report by ID."""
    try:
        report = db.query(AuditReport).filter(
            AuditReport.id == report_id
        ).first()
        
        if not report:
            return False
        
        db.delete(report)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e


def get_dashboard_stats(db: Session) -> dict:
    """Get dashboard statistics from audit reports."""
    try:
        total_audits = db.query(AuditReport).count()
        
        high_risk = db.query(AuditReport).filter(
            AuditReport.risk == "High"
        ).count()
        
        medium_risk = db.query(AuditReport).filter(
            AuditReport.risk == "Medium"
        ).count()
        
        low_risk = db.query(AuditReport).filter(
            AuditReport.risk == "Low"
        ).count()
        
        avg_score = 0.0
        if total_audits > 0:
            result = db.query(
                db.func.avg(AuditReport.compliance_score)
            ).scalar()
            avg_score = float(result) if result else 0.0
        
        return {
            "total_audits": total_audits,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "average_compliance_score": round(avg_score, 2)
        }
    except Exception as e:
        raise e
