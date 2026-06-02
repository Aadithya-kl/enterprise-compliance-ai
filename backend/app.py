from fastapi import FastAPI, UploadFile, File
from rag import (
    extract_text,
    chunk_text,
    store_chunks,
    search_chunks,
    generate_answer   
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
async def upload_pdf(file: UploadFile = File(...)):

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
    store_chunks(chunks,file.filename)

    return {
        "status": "success",
        "filename": file.filename,
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