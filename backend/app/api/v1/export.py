import io
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.audit_report import AuditReport
from app.models.user import User

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.colors import HexColor
except ImportError:
    pass

try:
    from docx import Document
    from docx.shared import Pt
except ImportError:
    pass

router = APIRouter(prefix="/reports", tags=["Export"])

@router.get("/{report_id}/export/pdf", summary="Export Compliance Report as PDF")
def export_pdf(
    report_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    report = db.query(AuditReport).filter(AuditReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Add custom styles
        styles.add(ParagraphStyle(name='SubTitle', parent=styles['Heading2'], textColor=HexColor('#4f46e5')))
        styles.add(ParagraphStyle(name='RiskHigh', parent=styles['Normal'], textColor=HexColor('#dc2626'), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='RiskMedium', parent=styles['Normal'], textColor=HexColor('#d97706'), fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='RiskLow', parent=styles['Normal'], textColor=HexColor('#16a34a'), fontName='Helvetica-Bold'))

        story = []
        
        story.append(Paragraph(f"Compliance Audit Report #{report.id}", styles['Title']))
        story.append(Spacer(1, 12))
        
        story.append(Paragraph("Executive Summary", styles['SubTitle']))
        story.append(Paragraph(report.executive_summary or "No summary available.", styles['Normal']))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Metrics", styles['SubTitle']))
        story.append(Paragraph(f"Compliance Score: {report.compliance_score}%", styles['Normal']))
        
        risk_style = styles[f'Risk{report.risk_level}'] if f'Risk{report.risk_level}' in styles else styles['Normal']
        story.append(Paragraph(f"Risk Level: {report.risk_level}", risk_style))
        story.append(Paragraph(f"Violations Detected: {report.violation_count}", styles['Normal']))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Compliance Findings", styles['SubTitle']))
        for f in report.findings:
            story.append(Paragraph(f"• {f.get('description', 'Unknown Finding')}", styles['Normal']))
        story.append(Spacer(1, 12))

        story.append(Paragraph("Recommendations", styles['SubTitle']))
        for r in report.recommendations:
            story.append(Paragraph(f"• {r}", styles['Normal']))

        doc.build(story)
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Compliance_Report_{report.id}.pdf"}
        )
    except NameError:
        raise HTTPException(status_code=500, detail="PDF generation library (reportlab) not installed")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")


@router.get("/{report_id}/export/docx", summary="Export Compliance Report as DOCX")
def export_docx(
    report_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    report = db.query(AuditReport).filter(AuditReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    try:
        doc = Document()
        doc.add_heading(f"Compliance Audit Report #{report.id}", 0)

        doc.add_heading("Executive Summary", level=1)
        doc.add_paragraph(report.executive_summary or "No summary available.")

        doc.add_heading("Metrics", level=1)
        p = doc.add_paragraph()
        p.add_run(f"Compliance Score: {report.compliance_score}%\n")
        p.add_run(f"Risk Level: {report.risk_level}\n")
        p.add_run(f"Violations Detected: {report.violation_count}")

        doc.add_heading("Compliance Findings", level=1)
        for f in report.findings:
            doc.add_paragraph(f.get('description', 'Unknown Finding'), style='List Bullet')

        doc.add_heading("Recommendations", level=1)
        for r in report.recommendations:
            doc.add_paragraph(r, style='List Bullet')

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=Compliance_Report_{report.id}.docx"}
        )
    except NameError:
        raise HTTPException(status_code=500, detail="DOCX generation library (python-docx) not installed")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DOCX generation failed: {exc}")
