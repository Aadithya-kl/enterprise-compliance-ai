from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import json
import logging

from rag import (
    extract_text,
    chunk_text,
    store_chunks,
    search_chunks,
    generate_answer,
    get_documents_by_type   
)
from compliance import (
    analyze_compliance,
    calculate_compliance_score,
    generate_compliance_report,
    assess_risk,
)
import os
from database import engine, get_db
from models import Base, AuditReport
from schemas import (
    AuditReportResponse,
    AuditReportListResponse,
    DashboardStatsResponse,
    ComplianceReportResponse,
    UploadResponse,
    QuestionResponse,
    DocumentResponse,
    RiskAssessmentResponse,
    AnalysisResponse
)
from crud import (
    save_audit_report,
    get_all_audit_reports,
    get_audit_report_by_id,
    delete_audit_report,
    get_dashboard_stats
)

app = FastAPI(title="Enterprise Compliance AI Platform", version="1.0.0")

Base.metadata.create_all(bind=engine)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/")
def home():
    return {
        "message": "Compliance AI Backend Running",
        "version": "1.0.0",
        "status": "operational"
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(document_type: str, file: UploadFile = File(...)):
    """Upload a PDF document for processing."""
    try:
        file_path = os.path.join(
            UPLOAD_FOLDER,
            file.filename
        )

        with open(file_path, "wb") as f:
            f.write(await file.read())

        text = extract_text(file_path)
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text found in PDF."
            )
        
        chunks = chunk_text(text)
        store_chunks(chunks, file.filename, document_type)

        logger.info(f"Successfully uploaded {file.filename}")

        return UploadResponse(
            status="success",
            filename=file.filename,
            document_type=document_type,
            characters=len(text),
            chunks=len(chunks)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask", response_model=QuestionResponse)
async def ask_question(question: str):
    """Ask a question about uploaded documents."""
    try:
        results = search_chunks(question)
        chunks = results.get("documents", [])

        if not chunks:
            return QuestionResponse(
                question=question,
                answer="No documents have been uploaded yet.",
                sources=[]
            )

        answer = generate_answer(question, chunks)

        sources = [
            item
            for item in results.get("metadata", [])
            if item is not None
        ]

        logger.info(f"Question answered: {question}")

        return QuestionResponse(
            question=question,
            answer=answer,
            sources=sources
        )
    except Exception as e:
        logger.error(f"Ask error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{document_type}", response_model=DocumentResponse)
def get_documents(document_type: str):
    """Get documents by type."""
    try:
        docs = get_documents_by_type(document_type)

        return DocumentResponse(
            document_type=document_type,
            documents_found=len(docs)
        )
    except Exception as e:
        logger.error(f"Get documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-compliance", response_model=AnalysisResponse)
def analyze():
    """Analyze compliance between policy and regulation documents."""
    try:
        policy_docs = get_documents_by_type("policy")
        regulation_docs = get_documents_by_type("regulation")

        if not policy_docs:
            raise HTTPException(
                status_code=400,
                detail="No policy documents found"
            )

        if not regulation_docs:
            raise HTTPException(
                status_code=400,
                detail="No regulation documents found"
            )

        analysis = analyze_compliance(policy_docs, regulation_docs)

        logger.info("Compliance analysis completed")

        return AnalysisResponse(analysis=analysis)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compliance-report", response_model=ComplianceReportResponse)
def compliance_report(db: Session = Depends(get_db)):
    """Generate compliance report and save to database."""
    try:
        policy_docs = get_documents_by_type("policy")
        regulation_docs = get_documents_by_type("regulation")

        if not policy_docs:
            raise HTTPException(
                status_code=400,
                detail="No policy documents found"
            )

        if not regulation_docs:
            raise HTTPException(
                status_code=400,
                detail="No regulation documents found"
            )

        report = generate_compliance_report(policy_docs, regulation_docs)
        
        if "raw_response" in report:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate valid compliance report"
            )

        saved_report = save_audit_report(db, report)

        logger.info(f"Compliance report generated and saved: ID={saved_report.id}")

        return ComplianceReportResponse(
            violation=report.get("violation", False),
            issues=json.loads(saved_report.issues),
            recommendations=json.loads(saved_report.recommendations),
            risk=saved_report.risk,
            compliance_score=saved_report.compliance_score,
            violation_count=saved_report.violation_count,
            audit_timestamp=saved_report.audit_timestamp,
            auditor=saved_report.auditor,
            id=saved_report.id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance report error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/risk-assessment", response_model=RiskAssessmentResponse)
def risk_assessment():
    """Assess risk based on compliance issues."""
    try:
        policy_docs = get_documents_by_type("policy")
        regulation_docs = get_documents_by_type("regulation")

        if not policy_docs or not regulation_docs:
            raise HTTPException(
                status_code=400,
                detail="Both policy and regulation documents are required"
            )

        report = generate_compliance_report(policy_docs, regulation_docs)

        if "raw_response" in report:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate valid risk assessment"
            )

        risk = assess_risk(report.get("issues", []))
        score = calculate_compliance_score(report.get("issues", []))

        logger.info(f"Risk assessment completed: Risk={risk}, Score={score}")

        return RiskAssessmentResponse(
            risk=risk,
            issue_count=len(report.get("issues", [])),
            compliance_score=score
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk assessment error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit-history", response_model=list[AuditReportListResponse])
def audit_history(db: Session = Depends(get_db)):
    """Get all audit reports."""
    try:
        reports = get_all_audit_reports(db)

        logger.info(f"Retrieved {len(reports)} audit reports")

        return reports
    except Exception as e:
        logger.error(f"Audit history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit-history/{report_id}", response_model=AuditReportResponse)
def get_audit_history(report_id: int, db: Session = Depends(get_db)):
    """Get a specific audit report by ID."""
    try:
        report = get_audit_report_by_id(db, report_id)

        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Audit report with ID {report_id} not found"
            )

        logger.info(f"Retrieved audit report: ID={report_id}")

        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get audit history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/audit-history/{report_id}")
def delete_audit(report_id: int, db: Session = Depends(get_db)):
    """Delete an audit report by ID."""
    try:
        success = delete_audit_report(db, report_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Audit report with ID {report_id} not found"
            )

        logger.info(f"Deleted audit report: ID={report_id}")

        return {
            "status": "success",
            "message": f"Audit report {report_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete audit error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard-stats", response_model=DashboardStatsResponse)
def dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    try:
        stats = get_dashboard_stats(db)

        logger.info("Retrieved dashboard statistics")

        return DashboardStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Dashboard stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Service is running"
    }
