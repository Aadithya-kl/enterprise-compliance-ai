from models import AuditReport


def save_audit_report(db, report):

    audit = AuditReport(
        risk=report["risk"],
        compliance_score=report["compliance_score"],
        violation_count=report["violation_count"],
        issues=str(report["issues"]),
        recommendations=str(report["recommendations"]),
        audit_timestamp=report["audit_timestamp"],
        auditor=report["auditor"]
    )

    db.add(audit)
    db.commit()
    db.refresh(audit)

    return audit