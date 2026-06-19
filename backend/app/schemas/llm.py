from pydantic import BaseModel, Field
from typing import List, Optional

class EvidenceSchema(BaseModel):
    finding: str = Field(..., description="The generated finding based on evidence")
    evidence_snippet: str = Field(..., description="Exact quote from the text supporting the finding")
    source: str = Field(..., description="Source filename")
    confidence: str = Field(..., description="Confidence level of the finding (e.g., High, Medium, Low)")

class FindingSchema(BaseModel):
    finding_text: str = Field(..., description="The text of the finding")

class AuditResponseSchema(BaseModel):
    executive_summary: str = Field(..., description="Overview of the audit")
    findings: List[FindingSchema] = Field(default_factory=list, description="List of findings")
    evidence: List[EvidenceSchema] = Field(default_factory=list, description="Evidence mapping for the findings")
    risks: str = Field(..., description="Identified risks")
    recommendations: str = Field(..., description="Recommendations based on findings")
    sources: List[str] = Field(default_factory=list, description="List of source filenames")
