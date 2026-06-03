from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime


class AuditReportCreate(BaseModel):
    """Schema for creating a new audit report."""
    risk: str
    compliance_score: int
    violation_count: int
    issues: List[str]
    recommendations: List[str]
    audit_timestamp: str
    auditor: str


class AuditReportResponse(BaseModel):
    """
    Full audit report response.
    issues and recommendations are stored as JSON text in DB,
    but returned as parsed lists here.
    """
    id: int
    risk: str
    compliance_score: int
    violation_count: int
    issues: List[str]           # Parsed from JSON text
    recommendations: List[str]  # Parsed from JSON text
    audit_timestamp: str
    auditor: str
    created_at: Optional[datetime] = None

    @field_validator("issues", "recommendations", mode="before")
    @classmethod
    def parse_json_string(cls, v):
        """Auto-parse JSON strings into lists when reading from DB."""
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                return []
        return v if v is not None else []

    class Config:
        from_attributes = True


class AuditReportListResponse(BaseModel):
    """Lightweight audit report response for list views."""
    id: int
    risk: str
    compliance_score: int
    violation_count: int
    audit_timestamp: str
    auditor: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics aggregated from all audit reports."""
    total_audits: int
    high_risk: int
    medium_risk: int
    low_risk: int
    average_compliance_score: float


class ComplianceReportResponse(BaseModel):
    """Response returned after generating a compliance report."""
    violation: bool
    issues: List[str]
    recommendations: List[str]
    risk: str
    compliance_score: int
    violation_count: int
    audit_timestamp: str
    auditor: str
    id: Optional[int] = None


class AnalysisResponse(BaseModel):
    """Response for compliance analysis (free-text narrative)."""
    analysis: str


class DocumentResponse(BaseModel):
    """Response for document type queries."""
    document_type: str
    documents_found: int


class QuestionResponse(BaseModel):
    """Response for Q&A questions."""
    question: str
    answer: str
    sources: List[dict]


class UploadResponse(BaseModel):
    """Response after a successful PDF upload."""
    status: str
    filename: str
    document_type: str
    characters: int
    chunks: int


class RiskAssessmentResponse(BaseModel):
    """Response for risk assessment."""
    risk: str
    issue_count: int
    compliance_score: int
