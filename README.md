<div align="center">

# Enterprise Compliance & Audit Intelligence Platform

**AI-powered compliance analysis, risk assessment, and audit reporting — built on RAG and multi-agent orchestration.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-FF6B35?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-Google_AI-4285F4?style=flat-square&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![Railway](https://img.shields.io/badge/Backend-Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)](https://railway.app)
[![Vercel](https://img.shields.io/badge/Frontend-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)](https://vercel.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

[Report Bug](https://github.com/Aadithya-kl/enterprise-compliance-ai/issues) · [Request Feature](https://github.com/Aadithya-kl/enterprise-compliance-ai/issues)

</div>

---
[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Try_the_Platform-success?style=for-the-badge)](https://enterprise-compliance-ai-swart.vercel.app/login)

## Overview

Enterprise Compliance & Audit Intelligence Platform is a production-grade system that automates the analysis of organizational policies against regulatory frameworks using Retrieval-Augmented Generation (RAG) and a multi-agent AI architecture.

Instead of manually reviewing hundreds of policy documents against regulatory standards, compliance officers can ingest documents from PDF, Google Drive, or Notion, and receive AI-generated risk scores, gap analyses, and audit-ready reports — in minutes.

**Who is this for?**
- Compliance officers managing regulatory obligations (GDPR, SOC 2, ISO 27001, etc.)
- Legal and audit teams that need fast gap analysis across large document sets
- Organizations onboarding to new regulatory frameworks

---

## Screenshots


| Dashboard | Compliance Report | Risk Assessment |
|-----------|------------------|-----------------|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Report](docs/screenshots/report.png) | ![Risk](docs/screenshots/risk.png) |

---

## Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        UI[React Frontend<br/>Vercel]
    end

    subgraph Auth["Auth Layer"]
        JWT[JWT Authentication]
        RBAC[Role-Based Access Control]
    end

    subgraph API["API Layer"]
        BE[FastAPI Backend<br/>Railway]
    end

    subgraph Ingestion["Document Ingestion"]
        PDF[PDF Adapter]
        GD[Google Drive Sync]
        NO[Notion Sync]
    end

    subgraph RAG["RAG Pipeline"]
        EMB[Embedding Service<br/>Gemini Embeddings]
        VS[Qdrant Cloud<br/>Vector Store]
        RET[Semantic Retriever]
    end

    subgraph Agents["Multi-Agent Orchestration · LangGraph"]
        CA[Compliance Agent]
        RA[Risk Assessment Agent]
        RGA[Report Generation Agent]
    end

    subgraph DB["Persistence"]
        SB[Supabase PostgreSQL]
    end

    UI --> JWT --> BE
    RBAC --> BE
    BE --> PDF & GD & NO --> EMB --> VS
    BE --> RET --> VS
    RET --> CA --> RA --> RGA
    RGA --> SB
    SB --> BE --> UI
```

### Agent Workflow

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant ING as Ingestion Pipeline
    participant VS as Qdrant Vector Store
    participant CA as Compliance Agent
    participant RA as Risk Agent
    participant RG as Report Agent
    participant DB as Supabase

    U->>API: Upload documents / select source
    API->>ING: Trigger ingestion (PDF / Drive / Notion)
    ING->>VS: Chunk, embed, and store vectors
    U->>API: Request compliance assessment
    API->>VS: Semantic retrieval of relevant chunks
    VS-->>CA: Return context
    CA->>RA: Pass compliance findings
    RA->>RG: Pass risk scores and gaps
    RG->>DB: Persist report
    DB-->>API: Return structured report
    API-->>U: Deliver audit-ready report
```

---

## Features

- **Multi-source document ingestion** — PDF upload, Google Drive sync, Notion workspace sync via modular adapter pattern
- **Semantic search** — Qdrant vector store with Gemini embeddings for contextual retrieval across large document repositories
- **Multi-agent compliance analysis** — LangGraph-orchestrated agents for compliance checking, risk scoring, and report generation
- **Audit-ready reports** — structured outputs with risk scores, identified gaps, and remediation recommendations
- **JWT authentication and RBAC** — role-based access control for multi-user enterprise environments
- **MCP integrations** — Model Context Protocol for structured tool use by the LLM agents
- **Full-stack deployment** — FastAPI backend on Railway, React frontend on Vercel

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Tailwind CSS |
| Backend | Python 3.11, FastAPI |
| AI Model | Gemini 2.5 Flash |
| Agent Orchestration | LangGraph |
| Vector Store | Qdrant Cloud |
| Relational DB | Supabase (PostgreSQL) |
| Document Sources | PDF, Google Drive API, Notion API |
| Auth | JWT, RBAC |
| Backend Deployment | Railway |
| Frontend Deployment | Vercel |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Qdrant Cloud](https://cloud.qdrant.io) account (free tier works)
- A [Supabase](https://supabase.com) project
- A [Google AI Studio](https://aistudio.google.com) API key (Gemini)
- Google Drive API credentials (optional, for Drive sync)
- Notion API token (optional, for Notion sync)

### 1. Clone the repository

```bash
git clone https://github.com/Aadithya-kl/enterprise-compliance-ai.git
cd enterprise-compliance-ai
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in `/backend`:

```env
GEMINI_API_KEY=your_gemini_api_key
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
JWT_SECRET=your_jwt_secret
GOOGLE_CLIENT_ID=your_google_client_id          # optional
GOOGLE_CLIENT_SECRET=your_google_client_secret  # optional
NOTION_API_TOKEN=your_notion_token              # optional
```

Start the backend:

```bash
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### 3. Frontend setup

```bash
cd frontend
npm install
```

Create a `.env.local` file in `/frontend`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
```

Open `http://localhost:3000`

### 4. Docker Compose (recommended for local full-stack)

```bash
docker-compose up --build
```

---

## Deployment

### Backend — Railway

1. Connect your GitHub repository to [Railway](https://railway.app)
2. Set all environment variables from the `.env` template above in the Railway dashboard
3. Railway auto-detects the Python app and deploys on push to `main`

### Frontend — Vercel

1. Import the repository into [Vercel](https://vercel.com)
2. Set `NEXT_PUBLIC_API_URL` to your Railway backend URL
3. Vercel deploys automatically on push to `main`

---

## Project Structure

```
enterprise-compliance-ai/
├── backend/
│   ├── main.py                  # FastAPI application entry point
│   ├── agents/
│   │   ├── compliance_agent.py  # LangGraph compliance checking agent
│   │   ├── risk_agent.py        # Risk scoring and gap analysis agent
│   │   └── report_agent.py      # Audit report generation agent
│   ├── ingestion/
│   │   ├── pdf_adapter.py       # PDF document ingestion
│   │   ├── drive_adapter.py     # Google Drive sync
│   │   └── notion_adapter.py    # Notion workspace sync
│   ├── rag/
│   │   ├── embedder.py          # Gemini embedding pipeline
│   │   └── retriever.py         # Qdrant semantic search
│   ├── auth/
│   │   ├── jwt_handler.py       # JWT token management
│   │   └── rbac.py              # Role-based access control
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js app router pages
│   │   ├── components/          # React UI components
│   │   └── lib/                 # API client and utilities
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Roadmap

- [ ] Support for additional regulatory frameworks (HIPAA, PCI-DSS, NIST)
- [ ] Slack and Microsoft Teams notifications for compliance alerts
- [ ] Scheduled automated compliance re-assessment
- [ ] Multi-tenant organization support
- [ ] Exportable audit reports in PDF and DOCX formats
- [ ] Audit trail and version history for document changes
- [ ] Fine-tuned compliance domain model

---

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request for significant changes.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## Author

**K L Aadithya**
B.Tech Computer Science and Data Science, Sai University

[![GitHub](https://img.shields.io/badge/GitHub-Aadithya--kl-181717?style=flat-square&logo=github)](https://github.com/Aadithya-kl)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-k--l--aadithya-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/k-l-aadithya-62b018295)

---
**Shrinidhi**
B.Tech Computer Science and Data Science, Sai University

[![GitHub](https://img.shields.io/badge/GitHub-shrinithisk-181717?style=flat-square&logo=github)](https://github.com/shrinithisk)


---
**Sankeerthana**
B.Tech Computer Science and Data Science, Sai University

[![GitHub](https://img.shields.io/badge/GitHub-KoletiSankeerthana-181717?style=flat-square&logo=github)](https://github.com/KoletiSankeerthana)


---
## License

Distributed under the MIT License. See `LICENSE` for more information.
