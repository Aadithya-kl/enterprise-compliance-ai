"""
Enterprise Compliance AI Platform - FastAPI Application
Provides endpoints for PDF ingestion, RAG Q&A, compliance analysis,
audit report management, and dashboard statistics.
"""

import json
import logging
import os

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from rag import (
    extract_text,
    chunk_text,
    store_chunks,
    search_chunks,
    generate_answer,
    get_documents_by_type,
)
from compliance import (
    analyze_compliance,
    calculate_compliance_score,
    generate_compliance_report,
    assess_risk,
)
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
    AnalysisResponse,
)
from crud import (
    save_audit_report,
    get_all_audit_reports,
    get_audit_report_by_id,
    delete_audit_report,
    get_dashboard_stats,
)

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Enterprise Compliance AI Platform",
    version="1.0.0",
    description=(
        "Autonomous platform for compliance analysis, audit reporting, "
        "and risk assessment powered by LLMs and RAG."
    ),
)

# Create tables on startup (idempotent — safe to run every time)
Base.metadata.create_all(bind=engine)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _parse_json_field(value) -> list:
    """
    Parse a field that may be a JSON string or already a list.
    Returns an empty list on failure.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except (json.JSONDecodeError, TypeError):
            return []
    return []


# ---------------------------------------------------------------------------
# Root / Health
# ---------------------------------------------------------------------------

@app.get("/")
def home():
    """Root endpoint — confirms the service is running."""
    return {
        "message": "Compliance AI Backend Running",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/health")
def health_check():
    """Health check endpoint for load balancers and uptime monitors."""
    return {"status": "healthy", "message": "Service is running"}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(document_type: str, file: UploadFile = File(...)):
    """
    Upload a PDF document.
    Extracts text, chunks it, and stores chunks in ChromaDB.
    Query param: document_type — e.g. 'policy' or 'regulation'
    """
    logger.info(f"Upload request: filename={file.filename}, type={document_type}")
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported."
            )

        file_path = os.path.join(UPLOAD_FOLDER, file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())
        logger.info(f"Saved file to {file_path}")

        text = extract_text(file_path)
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="No readable text found in the uploaded PDF."
            )

        chunks = chunk_text(text)
        store_chunks(chunks, file.filename, document_type)

        logger.info(
            f"Upload complete: {file.filename} | "
            f"{len(chunks)} chunks | {len(text)} chars"
        )

        return UploadResponse(
            status="success",
            filename=file.filename,
            document_type=document_type,
            characters=len(text),
            chunks=len(chunks),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error [{file.filename}]: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Ask
# ---------------------------------------------------------------------------

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(question: str):
    """Ask a question against all uploaded documents using RAG."""
    logger.info(f"Question received: {question[:120]}")
    try:
        results = search_chunks(question)
        chunks = results.get("documents", [])

        if not chunks:
            return QuestionResponse(
                question=question,
                answer="No documents have been uploaded yet.",
                sources=[],
            )

        answer = generate_answer(question, chunks)

        sources = [
            item
            for item in results.get("metadata", [])
            if item is not None
        ]

        logger.info(f"Answer generated for: {question[:80]}")
        return QuestionResponse(question=question, answer=answer, sources=sources)

    except Exception as e:
        logger.error(f"Ask error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

@app.get("/documents/{document_type}", response_model=DocumentResponse)
def get_documents(document_type: str):
    """Return count of stored chunks for a given document type."""
    try:
        docs = get_documents_by_type(document_type)
        logger.info(
            f"Documents query: type={document_type}, found={len(docs)}"
        )
        return DocumentResponse(
            document_type=document_type,
            documents_found=len(docs),
        )
    except Exception as e:
        logger.error(f"Get documents error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Analyze Compliance (narrative)
# ---------------------------------------------------------------------------

@app.post("/analyze-compliance", response_model=AnalysisResponse)
def analyze():
    """
    Generate a free-text compliance analysis narrative.
    Requires at least one 'policy' and one 'regulation' document uploaded.
    """
    try:
        policy_docs = get_documents_by_type("policy")
        regulation_docs = get_documents_by_type("regulation")

        if not policy_docs:
            raise HTTPException(
                status_code=400,
                detail="No policy documents found. Please upload a policy PDF first."
            )
        if not regulation_docs:
            raise HTTPException(
                status_code=400,
                detail="No regulation documents found. Please upload a regulation PDF first."
            )

        analysis = analyze_compliance(policy_docs, regulation_docs)
        logger.info("Compliance analysis narrative generated")
        return AnalysisResponse(analysis=analysis)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Compliance Report (structured + saved)
# ---------------------------------------------------------------------------

@app.post("/compliance-report", response_model=ComplianceReportResponse)
def compliance_report(db: Session = Depends(get_db)):
    """
    Generate a structured JSON compliance report, save it to Supabase,
    and return the full report including the new database ID.
    """
    logger.info("Compliance report request received")
    try:
        policy_docs = get_documents_by_type("policy")
        regulation_docs = get_documents_by_type("regulation")

        if not policy_docs:
            raise HTTPException(
                status_code=400,
                detail="No policy documents found. Upload a policy PDF first."
            )
        if not regulation_docs:
            raise HTTPException(
                status_code=400,
                detail="No regulation documents found. Upload a regulation PDF first."
            )

        report = generate_compliance_report(policy_docs, regulation_docs)

        if "raw_response" in report:
            logger.error(
                "LLM returned unparseable response; "
                f"raw: {report['raw_response'][:300]}"
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "The AI model returned an invalid response. "
                    "Please try again."
                ),
            )

        saved_report = save_audit_report(db, report)
        logger.info(f"Compliance report saved: id={saved_report.id}")

        return ComplianceReportResponse(
            violation=report.get("violation", False),
            issues=_parse_json_field(saved_report.issues),
            recommendations=_parse_json_field(saved_report.recommendations),
            risk=saved_report.risk,
            compliance_score=saved_report.compliance_score,
            violation_count=saved_report.violation_count,
            audit_timestamp=saved_report.audit_timestamp,
            auditor=saved_report.auditor,
            id=saved_report.id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Risk Assessment
# ---------------------------------------------------------------------------

@app.post("/risk-assessment", response_model=RiskAssessmentResponse)
def risk_assessment():
    """
    Assess compliance risk without saving to the database.
    Returns risk level, issue count, and compliance score.
    """
    logger.info("Risk assessment request received")
    try:
        policy_docs = get_documents_by_type("policy")
        regulation_docs = get_documents_by_type("regulation")

        if not policy_docs or not regulation_docs:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Both policy and regulation documents are required. "
                    "Please upload both before running a risk assessment."
                ),
            )

        report = generate_compliance_report(policy_docs, regulation_docs)

        if "raw_response" in report:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate valid risk assessment. Please try again.",
            )

        issues = report.get("issues", [])
        risk = assess_risk(issues)
        score = calculate_compliance_score(issues)

        logger.info(f"Risk assessment: risk={risk}, score={score}, issues={len(issues)}")
        return RiskAssessmentResponse(
            risk=risk,
            issue_count=len(issues),
            compliance_score=score,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Risk assessment error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Audit History
# ---------------------------------------------------------------------------

@app.get("/audit-history", response_model=list[AuditReportListResponse])
def audit_history(db: Session = Depends(get_db)):
    """Return all audit reports ordered by most recent first."""
    try:
        reports = get_all_audit_reports(db)
        logger.info(f"Returning {len(reports)} audit reports")
        return reports

    except Exception as e:
        logger.error(f"Audit history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audit-history/{report_id}", response_model=AuditReportResponse)
def get_audit_history(report_id: int, db: Session = Depends(get_db)):
    """Return a single audit report by ID including full issues and recommendations."""
    try:
        report = get_audit_report_by_id(db, report_id)

        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Audit report with ID {report_id} not found.",
            )

        logger.info(f"Returning audit report id={report_id}")
        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get audit history error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/audit-history/{report_id}")
def delete_audit(report_id: int, db: Session = Depends(get_db)):
    """Delete an audit report by ID."""
    try:
        success = delete_audit_report(db, report_id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Audit report with ID {report_id} not found.",
            )

        logger.info(f"Deleted audit report id={report_id}")
        return {
            "status": "success",
            "message": f"Audit report {report_id} deleted successfully.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete audit error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Dashboard Statistics
# ---------------------------------------------------------------------------

@app.get("/dashboard-stats", response_model=DashboardStatsResponse)
def dashboard_stats(db: Session = Depends(get_db)):
    """Return aggregated statistics for the dashboard."""
    try:
        stats = get_dashboard_stats(db)
        logger.info(f"Dashboard stats: {stats}")
        return DashboardStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Dashboard stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
