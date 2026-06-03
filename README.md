# Enterprise Compliance & Audit Intelligence Platform

A production-grade, AI-powered enterprise compliance and audit platform built with FastAPI, React, and Ollama.

---

## Architecture Overview

```
compliance-ai/
├── backend/           FastAPI + SQLAlchemy + ChromaDB + Ollama
│   └── app/
│       ├── api/v1/    Versioned REST API endpoints
│       ├── agents/    Multi-agent AI pipeline (LangGraph)
│       ├── core/      Configuration, security, logging
│       ├── crud/      Database CRUD layer
│       ├── db/        Session management, migrations
│       ├── mcp/       Model Context Protocol integrations
│       ├── models/    SQLAlchemy ORM models
│       ├── schemas/   Pydantic request/response schemas
│       └── services/  Business logic layer
└── frontend/          React 18 + TypeScript + Tailwind CSS
    └── src/
        ├── api/       Axios client modules
        ├── pages/     Full-page route components
        ├── components/Reusable UI components
        ├── store/     Auth context
        └── types/     TypeScript interfaces
```

---

## Quick Start (Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Ollama running locally with `llama3` model
- Supabase PostgreSQL database

### Backend

```powershell
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env: set DATABASE_URL, SECRET_KEY

# Run database migrations
# Open Supabase SQL Editor and run: app/db/migrations/initial.sql

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or press **F5** in VS Code to launch with the debugger.

API documentation available at: `http://localhost:8000/docs`

### Frontend

```powershell
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Application available at: `http://localhost:5173`

---

## Default Credentials

On first startup, a default admin account is created:

| Field    | Value                 |
|----------|-----------------------|
| Email    | `admin@company.com`   |
| Password | `Admin123!`           |

**Change this password immediately** using the User Management page.

---

## API Endpoints

| Method | Path                                    | Description                    | Auth Required |
|--------|-----------------------------------------|--------------------------------|---------------|
| POST   | `/api/v1/auth/login`                    | Obtain JWT tokens              | No            |
| POST   | `/api/v1/auth/register`                 | Create user (admin only)       | Admin         |
| GET    | `/api/v1/auth/me`                       | Current user profile           | Yes           |
| POST   | `/api/v1/documents/upload`              | Upload and ingest PDF          | Yes           |
| POST   | `/api/v1/documents/ask`                 | RAG question answering         | Yes           |
| POST   | `/api/v1/compliance/report`             | Generate compliance report     | Yes           |
| GET    | `/api/v1/compliance/history`            | List audit reports             | Yes           |
| GET    | `/api/v1/dashboard/stats`               | Aggregate statistics           | Yes           |
| GET    | `/api/v1/dashboard/trend`               | Monthly audit trend            | Yes           |
| GET    | `/api/v1/dashboard/risk-distribution`   | Risk breakdown                 | Yes           |
| POST   | `/api/v1/workflow/run`                  | Full multi-agent pipeline      | Yes           |
| POST   | `/api/v1/mcp/sync`                      | Sync MCP document sources      | Admin         |
| GET    | `/api/v1/users`                         | List users                     | Admin         |

---

## User Roles

| Role                  | Access                                                |
|-----------------------|-------------------------------------------------------|
| `admin`               | Full access, user management, MCP sync, delete audits |
| `auditor`             | Upload documents, generate reports, view all data     |
| `compliance_officer`  | View reports and analytics, read-only                 |

---

## Docker Deployment

```bash
# Build and start all services
docker compose up --build -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

Services:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:80`

---

## MCP Integration Configuration

Configure in `backend/.env`:

```env
# Local file system (no credentials needed)
MCP_LOCAL_FILES_DIR=./mcp_documents

# Google Drive (Service Account JSON)
GOOGLE_DRIVE_CREDENTIALS_JSON=/path/to/service-account.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id

# Notion
NOTION_API_TOKEN=secret_xxx
NOTION_DATABASE_ID=your_database_id
```

Trigger sync: `POST /api/v1/mcp/sync` (admin token required)

---

## AI Workflow

The full compliance pipeline runs via `POST /api/v1/workflow/run`:

1. **Document Retrieval** — fetches policy and regulation chunks from ChromaDB
2. **Compliance Agent** — compares policy against regulation, identifies gaps
3. **Risk Agent** — classifies issue severity, generates mitigation roadmap
4. **Report Agent** — synthesises executive summary and structured findings
5. **Persist** — saves the final report to Supabase

---

## Environment Variables Reference

See `backend/.env.example` for the full list with documentation.

Key required variables:

| Variable         | Required | Description                           |
|------------------|----------|---------------------------------------|
| `DATABASE_URL`   | Yes      | PostgreSQL connection string          |
| `SECRET_KEY`     | Yes      | JWT signing key (32+ random bytes)    |
| `ADMIN_EMAIL`    | Yes      | Bootstrap admin email                 |
| `ADMIN_PASSWORD` | Yes      | Bootstrap admin password              |
