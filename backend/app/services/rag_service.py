"""
RAG (Retrieval-Augmented Generation) service.
Wraps ChromaDB operations: ingestion, retrieval, and Q&A generation.
"""

import os
from uuid import uuid4

import chromadb
import ollama
from pypdf import PdfReader

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# ChromaDB client (module-level singleton)
# ---------------------------------------------------------------------------

_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
_collection = _client.get_or_create_collection(
    name=settings.CHROMA_COLLECTION_NAME
)


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all readable text from a PDF file using pypdf."""
    reader = PdfReader(pdf_path)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    result = "\n".join(pages_text)
    logger.debug(f"Extracted {len(result)} characters from {pdf_path}")
    return result


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    """Split text into overlapping windows for embedding."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        chunk = text[start : start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    logger.debug(f"Produced {len(chunks)} chunks from {len(text)} characters")
    return chunks


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _delete_document_chunks(filename: str) -> None:
    """Remove all existing chunks for a given filename."""
    try:
        _collection.delete(where={"filename": filename})
        logger.debug(f"Cleared existing chunks for: {filename}")
    except Exception as exc:
        # ChromaDB may raise if no documents match — safe to ignore
        logger.debug(f"Chunk deletion non-fatal: {exc}")


def store_document_chunks(
    chunks: list[str],
    filename: str,
    document_type: str,
) -> None:
    """Upsert document chunks into ChromaDB with metadata."""
    if not chunks:
        logger.warning(f"No chunks to store for {filename}")
        return

    _delete_document_chunks(filename)

    _collection.add(
        documents=chunks,
        metadatas=[
            {"filename": filename, "document_type": document_type}
            for _ in chunks
        ],
        ids=[str(uuid4()) for _ in chunks],
    )
    logger.info(
        f"Stored {len(chunks)} chunks | filename={filename} | type={document_type}"
    )


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve_chunks(query: str, n_results: int = 5) -> dict:
    """
    Retrieve the most relevant chunks for a query.
    Clamps n_results to the collection size to prevent ChromaDB errors.
    """
    try:
        total = _collection.count()
        if total == 0:
            return {"documents": [], "metadata": []}

        safe_n = min(n_results, total)
        results = _collection.query(query_texts=[query], n_results=safe_n)

        if not results["documents"] or not results["documents"][0]:
            return {"documents": [], "metadata": []}

        return {
            "documents": results["documents"][0],
            "metadata": results["metadatas"][0],
        }
    except Exception as exc:
        logger.error(f"ChromaDB retrieval error: {exc}", exc_info=True)
        return {"documents": [], "metadata": []}


def get_chunks_by_type(document_type: str) -> list[str]:
    """Return all stored chunks of a given document type."""
    try:
        results = _collection.get(where={"document_type": document_type})
        docs = results.get("documents") or []
        logger.debug(f"Retrieved {len(docs)} chunks for type={document_type}")
        return docs
    except Exception as exc:
        logger.error(f"ChromaDB get_by_type error: {exc}", exc_info=True)
        return []


# ---------------------------------------------------------------------------
# Q&A generation
# ---------------------------------------------------------------------------

def generate_answer(question: str, context_chunks: list[str]) -> str:
    """
    Generate a grounded answer using Llama3 via Ollama.
    The model is instructed to cite only the provided context.
    """
    context = "\n\n".join(context_chunks)
    prompt = f"""You are an Enterprise Compliance Assistant.

Instructions:
1. Answer using ONLY the provided context.
2. If the answer is not in the context, respond with:
   "The uploaded documents do not contain sufficient information to answer this question."
3. Do not speculate or fabricate information.
4. Be concise and professional.

Context:
{context}

Question:
{question}"""

    try:
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]
    except Exception as exc:
        logger.error(f"Ollama Q&A generation error: {exc}", exc_info=True)
        raise RuntimeError(f"LLM call failed: {exc}") from exc
