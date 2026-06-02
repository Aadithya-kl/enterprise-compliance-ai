# Quick Start Guide - Phase 2 Backend

## 30-Second Setup

### 1. Configure Database
```bash
# Create .env file
cp .env.example .env

# Edit .env and add your Supabase credentials:
# DATABASE_URL=postgresql://user:password@project.supabase.co:5432/postgres
```

### 2. Install & Run
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

### 3. Test
```bash
# Open in browser
http://localhost:8000/docs

# Or use curl
curl http://localhost:8000/health
```

**✓ Done!** Your backend is running.

---

## Common Tasks

### Generate Compliance Report
```bash
curl -X POST http://localhost:8000/compliance-report
```

Response includes saved report ID and all compliance data.

### Get All Audit History
```bash
curl http://localhost:8000/audit-history
```

Returns list of all saved compliance reports.

### Get Single Audit Report
```bash
curl http://localhost:8000/audit-history/1
```

Returns specific report with detailed issues and recommendations.

### Delete Audit Report
```bash
curl -X DELETE http://localhost:8000/audit-history/1
```

### Get Dashboard Stats
```bash
curl http://localhost:8000/dashboard-stats
```

Returns aggregated statistics:
- Total audits
- Risk breakdown (High/Medium/Low)
- Average compliance score

### Upload PDF
```bash
curl -F "document_type=policy" -F "file=@document.pdf" \
  http://localhost:8000/upload
```

### Ask Question
```bash
curl "http://localhost:8000/ask?question=What%20are%20the%20main%20policies"
```

---

## Useful Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| / | GET | Health check |
| /health | GET | Detailed health |
| /docs | GET | Swagger UI (Interactive) |
| /openapi.json | GET | OpenAPI spec |

---

## API Documentation

**Interactive API Docs:**
```
http://localhost:8000/docs
```

This provides:
- Full endpoint documentation
- Try-it-out functionality
- Request/response schemas
- Error documentation

---

## Development Tips

### Enable Auto-Reload
```bash
uvicorn app:app --reload
```

The server automatically restarts on code changes.

### View Logs
```bash
# Logs show all operations
# Filter for specific endpoint:
uvicorn app:app --reload | grep "compliance-report"
```

### Test Specific Endpoint
```bash
# Python
import requests
resp = requests.get("http://localhost:8000/dashboard-stats")
print(resp.json())

# Or use curl
curl http://localhost:8000/dashboard-stats | jq
```

---

## Troubleshooting

### Database Connection Error
```
Error: "could not connect to server"
```
**Solution:** Verify `DATABASE_URL` in `.env`

### Port Already in Use
```
Error: "Address already in use"
```
**Solution:** Use different port
```bash
uvicorn app:app --port 8001
```

### Module Not Found
```
Error: "ModuleNotFoundError"
```
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Import Error with SQLAlchemy
```
Error: "Class directly inherits TypingOnly"
```
**Solution:** Update to latest versions
```bash
pip install -U sqlalchemy psycopg
```

---

## File Structure

```
backend/
├── app.py              # FastAPI routes
├── models.py           # Database models
├── schemas.py          # Request/response validation
├── crud.py             # Database operations
├── database.py         # Connection setup
├── compliance.py       # Compliance logic
├── rag.py             # Document processing
└── requirements.txt    # Dependencies
```

---

## Database Operations

### Direct Query (Python)
```python
from database import SessionLocal
from models import AuditReport

db = SessionLocal()
reports = db.query(AuditReport).all()
for report in reports:
    print(f"ID: {report.id}, Risk: {report.risk}")
db.close()
```

### Using CRUD Functions
```python
from crud import get_all_audit_reports
from database import SessionLocal

db = SessionLocal()
reports = get_all_audit_reports(db)
db.close()
```

---

## Phase 1 Features (Still Works!)

All original features are preserved:

✓ PDF Upload & Extraction
✓ Document Chunking (ChromaDB)
✓ Semantic Search
✓ RAG with Ollama/Llama 3
✓ Compliance Analysis
✓ Risk Assessment

---

## Phase 2 New Features

✓ Database Persistence (PostgreSQL)
✓ Audit History Tracking
✓ Dashboard Statistics
✓ Report Management (CRUD)
✓ Error Handling & Logging

---

## Next Steps

1. **Read Full Documentation**
   - See `PHASE2_README.md` for comprehensive details
   - See `IMPLEMENTATION_SUMMARY.md` for technical overview

2. **Deploy to Production**
   - Configure environment variables
   - Use Gunicorn: `gunicorn app:app`
   - Or Docker (add Dockerfile)

3. **Extend Features**
   - Add authentication
   - Add pagination
   - Add caching
   - Add scheduled jobs

---

## Performance Notes

For production deployments with many audits:

1. **Add Pagination**
   ```python
   @app.get("/audit-history")
   def audit_history(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
       return get_all_audit_reports(db, skip, limit)
   ```

2. **Add Caching**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def get_dashboard_stats():
       # Cache for 5 minutes
   ```

3. **Use Connection Pooling**
   ```python
   # Already configured in database.py
   # SessionLocal uses SQLAlchemy's connection pool
   ```

---

## Support Resources

- **API Docs**: http://localhost:8000/docs
- **GitHub Issues**: [Link to repo]
- **Documentation**: `PHASE2_README.md`
- **Tests**: `python test_implementation.py`

---

## Success Indicators

✓ `GET /health` returns 200
✓ `POST /compliance-report` saves to database
✓ `GET /audit-history` returns list of saved reports
✓ `GET /dashboard-stats` returns aggregated data
✓ Swagger UI loads at `/docs`

All green? You're ready to go! 🚀
