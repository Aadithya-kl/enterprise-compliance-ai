import chromadb
import ollama
import logging
from pypdf import PdfReader
from uuid import uuid4

logger = logging.getLogger(__name__)

client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_or_create_collection(name="documents")


def extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    logger.debug(f"Extracted {len(text)} characters from {pdf_path}")
    return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """Split text into overlapping chunks for embedding."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():  # Skip empty chunks
            chunks.append(chunk)
        start += chunk_size - overlap
    logger.debug(f"Created {len(chunks)} chunks from {len(text)} characters")
    return chunks


def delete_document(filename: str) -> None:
    """Remove all chunks for a given filename from ChromaDB."""
    try:
        collection.delete(where={"filename": filename})
        logger.info(f"Deleted existing chunks for: {filename}")
    except Exception as e:
        # If no documents exist yet, ChromaDB may raise — safe to ignore
        logger.debug(f"delete_document non-fatal: {e}")


def store_chunks(chunks: list, filename: str, document_type: str) -> None:
    """Store document chunks into ChromaDB with metadata."""
    if not chunks:
        logger.warning(f"No chunks to store for {filename}")
        return

    # Remove old version of this file first
    delete_document(filename)

    collection.add(
        documents=chunks,
        metadatas=[
            {"filename": filename, "document_type": document_type}
            for _ in chunks
        ],
        ids=[str(uuid4()) for _ in chunks]
    )
    logger.info(
        f"Stored {len(chunks)} chunks for {filename} "
        f"(type={document_type})"
    )


def search_chunks(query: str, n_results: int = 3) -> dict:
    """
    Search ChromaDB for chunks relevant to the query.
    Safely handles collections with fewer documents than n_results.
    """
    try:
        # Clamp n_results to avoid ChromaDB error when collection is small
        total_docs = collection.count()
        if total_docs == 0:
            return {"documents": [], "metadata": []}

        safe_n = min(n_results, total_docs)

        results = collection.query(
            query_texts=[query],
            n_results=safe_n
        )

        if not results["documents"] or not results["documents"][0]:
            return {"documents": [], "metadata": []}

        logger.debug(f"Search returned {len(results['documents'][0])} chunks")
        return {
            "documents": results["documents"][0],
            "metadata": results["metadatas"][0],
        }
    except Exception as e:
        logger.error(f"ChromaDB search error: {e}")
        return {"documents": [], "metadata": []}


def get_documents_by_type(document_type: str) -> list:
    """
    Retrieve all document text chunks of a given document_type.
    Returns empty list if none found.
    """
    try:
        results = collection.get(
            where={"document_type": document_type}
        )
        docs = results.get("documents") or []
        logger.debug(
            f"Found {len(docs)} chunks for document_type={document_type}"
        )
        return docs
    except Exception as e:
        logger.error(f"get_documents_by_type error: {e}")
        return []


def generate_answer(question: str, chunks: list) -> str:
    """
    Generate an answer from document context using Llama3 via Ollama.
    """
    context = "\n\n".join(chunks)

    prompt = f"""
You are an Enterprise Compliance Assistant.

Rules:
1. Use ONLY the provided context.
2. If the answer is not found, say:
   "The uploaded documents do not contain enough information."
3. Never invent information.
4. Keep answers concise.

Context:
{context}

Question:
{question}
"""

    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response["message"]["content"]
        logger.info(f"Generated answer for question: {question[:80]}")
        return answer
    except Exception as e:
        logger.error(f"Ollama generate_answer error: {e}")
        raise RuntimeError(f"LLM call failed: {e}") from e