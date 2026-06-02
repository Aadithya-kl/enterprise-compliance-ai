from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class AuditReportCreate(BaseModel):
    risk: str
    compliance_score: int
    violation_count: int
    issues: List[str]
    recommendations: List[str]
    audit_timestamp: str
    auditor: str


class AuditReportResponse(BaseModel):
    id: int
    risk: str
    compliance_score: int
    violation_count: int
    issues: str
    recommendations: str
    audit_timestamp: str
    auditor: str

    class Config:
        from_attributes = True


class AuditReportListResponse(BaseModel):
    id: int
    risk: str
    compliance_score: int
    violation_count: int
    audit_timestamp: str
    auditor: str

    class Config:
        from_attributes = True


class DashboardStatsResponse(BaseModel):
    total_audits: int
    high_risk: int
    medium_risk: int
    low_risk: int
    average_compliance_score: float


class ComplianceReportResponse(BaseModel):
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
    analysis: str


class DocumentResponse(BaseModel):
    document_type: str
    documents_found: int


class QuestionResponse(BaseModel):
    question: str
    answer: str
    sources: List[dict]


class UploadResponse(BaseModel):
    status: str
    filename: str
    document_type: str
    characters: int
    chunks: int


class RiskAssessmentResponse(BaseModel):
    risk: str
    issue_count: int
    compliance_score: int
