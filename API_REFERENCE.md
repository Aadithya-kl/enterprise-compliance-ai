# API Reference - Enterprise Compliance AI Platform

## Base URL
```
http://localhost:8000
```

## Authentication
Not implemented in Phase 2. Add in Phase 3.

---

## System Endpoints

### 1. Health Check
Check if the service is running.

**Endpoint:**
```
GET /health
```

**Response (200):**
```json
{
  "status": "healthy",
  "message": "Service is running"
}
```

---

### 2. Home
Get service information.

**Endpoint:**
```
GET /
```

**Response (200):**
```json
{
  "message": "Compliance AI Backend Running",
  "version": "1.0.0",
  "status": "operational"
}
```

---

## Document Management

### 3. Upload PDF
Upload a document for processing.

**Endpoint:**
```
POST /upload
```

**Parameters:**
- `document_type` (query, required): "policy" | "regulation" | "standard"
- `file` (form, required): PDF file

**Example:**
```bash
curl -F "document_type=policy" -F "file=@policy.pdf" \
  http://localhost:8000/upload
```

**Response (200):**
```json
{
  "status": "success",
  "filename": "policy.pdf",
  "document_type": "policy",
  "characters": 5234,
  "chunks": 6
}
```

**Status Codes:**
- 200: Success
- 400: Invalid PDF (no readable text)
- 500: Server error

---

### 4. Get Documents by Type
Retrieve count of documents by type.

**Endpoint:**
```
GET /documents/{document_type}
```

**Parameters:**
- `document_type` (path, required): "policy" | "regulation" | "standard"

**Example:**
```bash
curl http://localhost:8000/documents/policy
```

**Response (200):**
```json
{
  "document_type": "policy",
  "documents_found": 3
}
```

---

## Question & Answer

### 5. Ask Question
Ask a question about uploaded documents using RAG.

**Endpoint:**
```
POST /ask
```

**Parameters:**
- `question` (query, required): Your question

**Example:**
```bash
curl "http://localhost:8000/ask?question=What%20is%20the%20policy%20on%20data%20retention"
```

**Response (200):**
```json
{
  "question": "What is the policy on data retention?",
  "answer": "According to the policy documents...",
  "sources": [
    {
      "filename": "policy.pdf",
      "document_type": "policy"
    }
  ]
}
```

**Response (200) - No Documents:**
```json
{
  "question": "What is the policy on data retention?",
  "answer": "No documents have been uploaded yet.",
  "sources": []
}
```

---

## Compliance Analysis

### 6. Analyze Compliance
Analyze policy against regulations.

**Endpoint:**
```
POST /analyze-compliance
```

**Parameters:**
None required. Uses uploaded policy and regulation documents.

**Example:**
```bash
curl -X POST http://localhost:8000/analyze-compliance
```

**Response (200):**
```json
{
  "analysis": "Comparing the company policy against regulations...\n\nCompliance Violations Found:\n1. Data Retention: Policy allows 5 years, regulation requires 7 years\n..."
}
```

**Errors:**
- 400: No policy documents found
- 400: No regulation documents found
- 500: Analysis failed

---

### 7. Generate Compliance Report
Generate comprehensive compliance report and save to database.

**Endpoint:**
```
POST /compliance-report
```

**Parameters:**
None required. Uses uploaded policy and regulation documents.

**Example:**
```bash
curl -X POST http://localhost:8000/compliance-report
```

**Response (200):**
```json
{
  "violation": true,
  "issues": [
    "Data retention period mismatch",
    "Missing encryption requirement",
    "Insufficient audit logging"
  ],
  "recommendations": [
    "Update data retention policy to 7 years",
    "Add encryption requirements",
    "Implement comprehensive audit logging"
  ],
  "risk": "High",
  "compliance_score": 42,
  "violation_count": 3,
  "audit_timestamp": "2024-01-15 14:30:00",
  "auditor": "Compliance AI Auditor",
  "id": 1
}
```

**Status Codes:**
- 200: Success (report generated and saved)
- 400: Missing documents
- 500: Report generation failed

---

### 8. Risk Assessment
Assess risk level based on compliance issues.

**Endpoint:**
```
POST /risk-assessment
```

**Parameters:**
None required. Uses uploaded policy and regulation documents.

**Example:**
```bash
curl -X POST http://localhost:8000/risk-assessment
```

**Response (200):**
```json
{
  "risk": "High",
  "issue_count": 5,
  "compliance_score": 50
}
```

**Risk Levels:**
- "Low": 0-1 issues
- "Medium": 2-4 issues
- "High": 5+ issues

**Status Codes:**
- 200: Success
- 400: Missing documents
- 500: Assessment failed

---

## Audit History Management

### 9. Get All Audit Reports
Retrieve all compliance reports from database.

**Endpoint:**
```
GET /audit-history
```

**Parameters:**
None

**Example:**
```bash
curl http://localhost:8000/audit-history
```

**Response (200):**
```json
[
  {
    "id": 1,
    "risk": "High",
    "compliance_score": 42,
    "violation_count": 3,
    "audit_timestamp": "2024-01-15 14:30:00",
    "auditor": "Compliance AI Auditor"
  },
  {
    "id": 2,
    "risk": "Medium",
    "compliance_score": 65,
    "violation_count": 2,
    "audit_timestamp": "2024-01-14 10:15:00",
    "auditor": "Compliance AI Auditor"
  }
]
```

**Response (200) - Empty:**
```json
[]
```

---

### 10. Get Single Audit Report
Retrieve a specific audit report with full details.

**Endpoint:**
```
GET /audit-history/{report_id}
```

**Parameters:**
- `report_id` (path, required): ID of the audit report

**Example:**
```bash
curl http://localhost:8000/audit-history/1
```

**Response (200):**
```json
{
  "id": 1,
  "risk": "High",
  "compliance_score": 42,
  "violation_count": 3,
  "issues": "[\"Issue 1\", \"Issue 2\", \"Issue 3\"]",
  "recommendations": "[\"Fix 1\", \"Fix 2\", \"Fix 3\"]",
  "audit_timestamp": "2024-01-15 14:30:00",
  "auditor": "Compliance AI Auditor"
}
```

**Status Codes:**
- 200: Success
- 404: Report not found
- 500: Server error

---

### 11. Delete Audit Report
Delete an audit report from database.

**Endpoint:**
```
DELETE /audit-history/{report_id}
```

**Parameters:**
- `report_id` (path, required): ID of the audit report

**Example:**
```bash
curl -X DELETE http://localhost:8000/audit-history/1
```

**Response (200):**
```json
{
  "status": "success",
  "message": "Audit report 1 deleted successfully"
}
```

**Status Codes:**
- 200: Success
- 404: Report not found
- 500: Server error

---

## Dashboard

### 12. Get Dashboard Statistics
Get aggregated compliance statistics.

**Endpoint:**
```
GET /dashboard-stats
```

**Parameters:**
None

**Example:**
```bash
curl http://localhost:8000/dashboard-stats
```

**Response (200):**
```json
{
  "total_audits": 5,
  "high_risk": 1,
  "medium_risk": 2,
  "low_risk": 2,
  "average_compliance_score": 58.4
}
```

**Response (200) - No Data:**
```json
{
  "total_audits": 0,
  "high_risk": 0,
  "medium_risk": 0,
  "low_risk": 0,
  "average_compliance_score": 0.0
}
```

---

## Error Responses

### Standard Error Format
All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

#### 400 Bad Request
Missing required documents:
```json
{
  "detail": "No policy documents found"
}
```

#### 404 Not Found
Audit report doesn't exist:
```json
{
  "detail": "Audit report with ID 999 not found"
}
```

#### 500 Internal Server Error
Database or processing error:
```json
{
  "detail": "Failed to generate valid compliance report"
}
```

---

## Data Types

### Compliance Score
- Range: 0-100
- Calculation: 100 - (issues_count * 10), min 0
- Represents compliance percentage

### Risk Level
- "Low": 0-1 issues
- "Medium": 2-4 issues
- "High": 5+ issues

### Timestamps
- Format: "YYYY-MM-DD HH:MM:SS"
- Example: "2024-01-15 14:30:00"

### Issues & Recommendations
- Stored as JSON arrays
- Example: `["Issue 1", "Issue 2"]`

---

## Rate Limiting
Not implemented in Phase 2. Add in Phase 3.

---

## Pagination
Not implemented in Phase 2. Add in Phase 3.

---

## Filtering
Not fully implemented in Phase 2. Basic endpoints available:
- Filter by risk level: Not yet available
- Filter by date range: Not yet available
- Search in issues: Not yet available

---

## Sorting
Audit reports are sorted by:
- **Default**: Latest first (by `created_at`)
- **Other sorts**: Not yet available

---

## Authentication
Not implemented in Phase 2. Add in Phase 3.

---

## CORS
Not restricted. Configure before production deployment.

---

## Examples by Use Case

### Example 1: Generate and Save Report
```bash
# 1. Upload documents
curl -F "document_type=policy" -F "file=@policy.pdf" \
  http://localhost:8000/upload

curl -F "document_type=regulation" -F "file=@regulation.pdf" \
  http://localhost:8000/upload

# 2. Generate and save report
curl -X POST http://localhost:8000/compliance-report

# Response includes ID: 1
```

### Example 2: View Audit History
```bash
# Get all reports
curl http://localhost:8000/audit-history

# Get specific report
curl http://localhost:8000/audit-history/1

# Parse issues and recommendations
curl http://localhost:8000/audit-history/1 | jq '.issues'
```

### Example 3: Monitor Dashboard
```bash
# Get statistics
curl http://localhost:8000/dashboard-stats

# Response:
# {
#   "total_audits": 10,
#   "high_risk": 2,
#   "medium_risk": 5,
#   "low_risk": 3,
#   "average_compliance_score": 62.5
# }
```

### Example 4: Ask About Compliance
```bash
# Ask specific question
curl "http://localhost:8000/ask?question=What%20is%20the%20policy%20on%20encryption"

# Response includes answer from documents
```

---

## Integration Examples

### Python
```python
import requests

# Generate report
resp = requests.post("http://localhost:8000/compliance-report")
report = resp.json()
print(f"Report ID: {report['id']}, Risk: {report['risk']}")

# Get history
resp = requests.get("http://localhost:8000/audit-history")
reports = resp.json()
print(f"Total reports: {len(reports)}")

# Get stats
resp = requests.get("http://localhost:8000/dashboard-stats")
stats = resp.json()
print(f"Average score: {stats['average_compliance_score']}")
```

### JavaScript
```javascript
// Generate report
const response = await fetch('http://localhost:8000/compliance-report', {
  method: 'POST'
});
const report = await response.json();
console.log(`Report ID: ${report.id}, Risk: ${report.risk}`);

// Get history
const histResp = await fetch('http://localhost:8000/audit-history');
const reports = await histResp.json();
console.log(`Total reports: ${reports.length}`);

// Get stats
const statsResp = await fetch('http://localhost:8000/dashboard-stats');
const stats = await statsResp.json();
console.log(`Average score: ${stats.average_compliance_score}`);
```

---

## OpenAPI/Swagger
Interactive API documentation available at:
```
http://localhost:8000/docs
```

Download OpenAPI specification:
```
http://localhost:8000/openapi.json
```

---

## Version
Current API Version: **1.0.0**

## Last Updated
Phase 2 Completion: January 2024
