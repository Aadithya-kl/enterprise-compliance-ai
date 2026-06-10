"""
Analytics Aggregation Service.
Handles SQL-based analytics compilation and LLM trend summary generation.
"""

import json
from datetime import datetime
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.compliance_violation import ComplianceViolation
from app.models.audit_report import AuditReport
from app.services.compliance_service import _call_ollama
from app.core.logging import get_logger

logger = get_logger(__name__)

def get_compliance_score_trend(db: Session, months: int = 12) -> list[dict]:
    """Compile monthly average compliance scores."""
    if "sqlite" in db.bind.url.drivername:
        query = text("""
            SELECT 
                strftime('%Y-%m', report_date) AS period,
                ROUND(AVG(compliance_score), 1) AS avg_score
            FROM compliance_violations
            WHERE report_date >= datetime('now', '-' || :months || ' month')
            GROUP BY period
            ORDER BY period ASC
        """)
    else:
        query = text("""
            SELECT 
                TO_CHAR(report_date, 'YYYY-MM') AS period,
                ROUND(AVG(compliance_score), 1)::float AS avg_score
            FROM compliance_violations
            WHERE report_date >= NOW() - INTERVAL ':months months'
            GROUP BY period
            ORDER BY period ASC
        """)
        
    rows = db.execute(query, {"months": months}).fetchall()
    return [{"period": r[0], "score": float(r[1]) if r[1] is not None else 100.0} for r in rows]

def get_violation_frequency(db: Session, months: int = 12) -> list[dict]:
    """Count violations grouped by violation_type and department."""
    rows = (
        db.query(
            ComplianceViolation.violation_type,
            ComplianceViolation.department,
            func.count(ComplianceViolation.id)
        )
        .filter(ComplianceViolation.report_date >= text("datetime('now', '-12 month')") if "sqlite" in db.bind.url.drivername else ComplianceViolation.report_date >= text("NOW() - INTERVAL '12 months'"))
        .group_by(ComplianceViolation.violation_type, ComplianceViolation.department)
        .all()
    )
    return [
        {
            "type": r[0],
            "department": r[1],
            "count": r[2]
        }
        for r in rows
    ]

def get_risk_distribution_trend(db: Session, months: int = 12) -> list[dict]:
    """Compile monthly distribution of violation severities."""
    if "sqlite" in db.bind.url.drivername:
        query = text("""
            SELECT 
                strftime('%Y-%m', report_date) AS period,
                severity,
                COUNT(*) AS count
            FROM compliance_violations
            WHERE report_date >= datetime('now', '-' || :months || ' month')
            GROUP BY period, severity
            ORDER BY period ASC
        """)
    else:
        query = text("""
            SELECT 
                TO_CHAR(report_date, 'YYYY-MM') AS period,
                severity,
                COUNT(*)::int AS count
            FROM compliance_violations
            WHERE report_date >= NOW() - INTERVAL ':months months'
            GROUP BY period, severity
            ORDER BY period ASC
        """)
        
    rows = db.execute(query, {"months": months}).fetchall()
    
    # Restructure into a timeline array: [{"period": "2026-06", "Critical": 5, "High": 2, ...}]
    data_by_period = {}
    for r in rows:
        period, severity, count = r[0], r[1], r[2]
        if period not in data_by_period:
            data_by_period[period] = {"period": period, "Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        data_by_period[period][severity] = count
        
    return sorted(list(data_by_period.values()), key=lambda x: x["period"])

def get_recurring_findings(db: Session, limit: int = 5) -> list[dict]:
    """Rank top violation categories and list common description themes."""
    rows = (
        db.query(
            ComplianceViolation.violation_type,
            func.count(ComplianceViolation.id)
        )
        .group_by(ComplianceViolation.violation_type)
        .order_by(func.count(ComplianceViolation.id).desc())
        .limit(limit)
        .all()
    )
    return [{"type": r[0], "count": r[1]} for r in rows]

def generate_ai_trend_summary(db: Session, query_prompt: str = "") -> str:
    """Compile recent stats and feed to LLM to produce a narrative summary."""
    # 1. Fetch statistics
    score_trend = get_compliance_score_trend(db, 6)
    violation_freq = get_recurring_findings(db, 5)
    
    # Get total violations count
    total_violations = db.query(ComplianceViolation).count()
    critical_count = db.query(ComplianceViolation).filter(ComplianceViolation.severity == "Critical").count()
    high_count = db.query(ComplianceViolation).filter(ComplianceViolation.severity == "High").count()
    medium_count = db.query(ComplianceViolation).filter(ComplianceViolation.severity == "Medium").count()
    
    # 2. Format as context prompt
    score_str = ", ".join([f"{s['period']}: {s['score']}%" for s in score_trend])
    freq_str = ", ".join([f"{f['type']}: {f['count']} findings" for f in violation_freq])
    
    context = f"""You are a Principal AI Compliance Director reporting to the board.
    
We have compiled the following historical compliance metrics:
- Total Identified Violations: {total_violations}
- Severity breakdown: Critical: {critical_count}, High: {high_count}, Medium: {medium_count}
- Average Compliance Score Trend (last 6 periods): {score_str}
- Top Recurring Findings: {freq_str}

User request/focus: {query_prompt if query_prompt else "Provide an executive summary of compliance trends."}

INSTRUCTION:
Write a highly professional, concise, narrative trend summary (2-3 sentences max). Cite statistics directly.
Example: "Critical violations increased 23% during the last quarter, mainly driven by MFA and access control policy failures. Average compliance score stabilized at 82.5%."
Do not include any greeting or conversational filler. Output the executive summary directly.
"""
    try:
        if total_violations == 0:
            return "No audit logs or violations recorded yet. Generate compliance reports first to view trends."
        return _call_ollama(context)
    except Exception as exc:
        logger.error(f"Failed to generate trend summary: {exc}")
        return "Failed to generate AI trend summary due to LLM timeout."
