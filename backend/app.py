from fastapi import FastAPI, UploadFile, File
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
    generate_compliance_report,
    assess_risk
)
import os

app = FastAPI()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/")
def home():
    return {
        "message": "Compliance AI Backend Running"
    }


@app.post("/upload")
async def upload_pdf(document_type: str, file: UploadFile = File(...)):

    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(file_path, "wb") as f:
        f.write(await file.read())

    text = extract_text(file_path)
    if not text.strip():
        return {
            "status": "error",
            "message": "No readable text found in PDF."
                }
    chunks = chunk_text(text)
    store_chunks(chunks, file.filename, document_type)

    return {
        "status": "success",
        "filename": file.filename,
        "document_type": document_type,
        "characters": len(text),
        "chunks": len(chunks)
    }
@app.post("/ask")
async def ask_question(question: str):

    results = search_chunks(question)
    chunks = results["documents"]

    if not chunks:
        return {
            "question": question,
            "answer": "No documents have been uploaded yet.",
            "sources": []
        }

    answer = generate_answer(
        question,
        chunks
    )

    sources = [
        item
        for item in results["metadata"]
        if item is not None
    ]

    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }

@app.get("/documents/{document_type}")
def get_documents(document_type: str):

    docs = get_documents_by_type(
        document_type
    )

    return {
        "document_type": document_type,
        "documents_found": len(docs)
    }

@app.post("/analyze-compliance")
def analyze():

    policy_docs = get_documents_by_type(
        "policy"
    )

    regulation_docs = get_documents_by_type(
        "regulation"
    )

    if not policy_docs:

        return {
            "error": "No policy documents found"
        }

    if not regulation_docs:

        return {
            "error": "No regulation documents found"
        }

    analysis = analyze_compliance(
        policy_docs,
        regulation_docs
    )

    return {
        "analysis": analysis
    }

@app.post("/compliance-report")
def compliance_report():

    policy_docs = get_documents_by_type(
        "policy"
    )

    regulation_docs = get_documents_by_type(
        "regulation"
    )

    if not policy_docs:
        return {
            "error": "No policy documents found"
        }

    if not regulation_docs:
        return {
            "error": "No regulation documents found"
        }

    report = generate_compliance_report(
        policy_docs,
        regulation_docs
    )

    return report

@app.post("/risk-assessment")
def risk_assessment():

    policy_docs = get_documents_by_type(
        "policy"
    )

    regulation_docs = get_documents_by_type(
        "regulation"
    )

    report = generate_compliance_report(
        policy_docs,
        regulation_docs
    )

    risk = assess_risk(
        report["issues"]
    )

    return {
        "risk": risk,
        "issue_count": len(report["issues"])
    }