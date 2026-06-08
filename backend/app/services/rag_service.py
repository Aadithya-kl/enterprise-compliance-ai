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
# Text extraction & Table Parsing
# ---------------------------------------------------------------------------

def table_to_markdown(table: list[list[str | None]]) -> str:
    """Convert a 2D list representing a table into a Markdown table string."""
    if not table:
        return ""
    # Filter out completely empty rows
    table = [row for row in table if any(cell is not None and str(cell).strip() for cell in row)]
    if not table:
        return ""
    
    # Pad columns to match the maximum row length
    max_cols = max(len(row) for row in table)
    
    markdown = []
    for i, row in enumerate(table):
        # Normalize cell values and escape pipe characters
        cells = [str(cell).replace("\n", " ").replace("|", "\\|").strip() if cell is not None else "" for cell in row]
        # Pad row cells to max_cols
        cells += [""] * (max_cols - len(cells))
        
        markdown.append("| " + " | ".join(cells) + " |")
        if i == 0:
            # Header separator
            markdown.append("| " + " | ".join(["---"] * max_cols) + " |")
            
    return "\n".join(markdown)


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text and tables (formatted as Markdown) from a PDF file using pdfplumber.
    Falls back to pytesseract OCR if page text is minimal (e.g. scanned image pages).
    """
    pages_text = []
    
    try:
        import pdfplumber
        import pypdfium2 as pdfium
        import pytesseract
        
        logger.info(f"Extracting text & tables from {pdf_path} using pdfplumber...")
        with pdfplumber.open(pdf_path) as pdf:
            pdfium_doc = None
            
            for page_idx, page in enumerate(pdf.pages):
                # 1. Extract plain text
                page_content = page.extract_text() or ""
                
                # 2. Extract tables and convert them to Markdown
                try:
                    tables = page.extract_tables()
                    formatted_tables = []
                    for table in tables:
                        md_table = table_to_markdown(table)
                        if md_table:
                            formatted_tables.append(md_table)
                    
                    if formatted_tables:
                        page_content += "\n\n### Tables Extracted (Page {}):\n".format(page_idx + 1) + "\n\n".join(formatted_tables)
                except Exception as table_exc:
                    logger.warning(f"Table extraction failed on page {page_idx + 1}: {table_exc}")
                
                # 3. If the page is mostly blank (scanned image or diagram), attempt OCR
                if len(page_content.strip()) < 50:
                    logger.debug(f"Page {page_idx + 1} has very little text. Attempting OCR...")
                    try:
                        if pdfium_doc is None:
                            pdfium_doc = pdfium.PdfDocument(pdf_path)
                        pdfium_page = pdfium_doc[page_idx]
                        
                        # Render page at 2x resolution to PIL Image for OCR
                        image = pdfium_page.render(scale=2).to_pil()
                        ocr_text = pytesseract.image_to_string(image)
                        
                        if ocr_text.strip():
                            page_content += "\n\n### OCR Extracted Text (Page {}):\n".format(page_idx + 1) + ocr_text.strip()
                    except Exception as ocr_exc:
                        # Log warning (Tesseract might not be installed on host system)
                        logger.warning(
                            f"OCR skipped on page {page_idx + 1}. Ensure 'tesseract' CLI tool is installed: {ocr_exc}"
                        )
                
                if page_content.strip():
                    pages_text.append(page_content)
                    
        result = "\n\n--- Page Break ---\n\n".join(pages_text)
        logger.debug(f"Extracted {len(result)} characters using pdfplumber + OCR from {pdf_path}")
        return result

    except Exception as exc:
        logger.error(f"pdfplumber extraction failed: {exc}. Falling back to basic pypdf reader.")
        # Fallback to simple pypdf extraction if pdfplumber fails
        try:
            reader = PdfReader(pdf_path)
            pages_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
            result = "\n".join(pages_text)
            logger.debug(f"Fallback extracted {len(result)} characters from {pdf_path}")
            return result
        except Exception as pypdf_exc:
            logger.error(f"Fallback pypdf extraction also failed: {pypdf_exc}")
            raise exc


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
    extra_metadata: dict | None = None,
) -> None:
    """
    Upsert document chunks into ChromaDB with metadata.

    Args:
        chunks:         List of text chunks to store.
        filename:       Source filename — used as the metadata key for retrieval.
        document_type:  Document category ('policy', 'regulation', 'general').
        extra_metadata: Optional additional key/value pairs merged into every
                        chunk's metadata dict. Use this to pass drive_file_id,
                        web_view_link, or other provenance information.
    """
    if not chunks:
        logger.warning(f"No chunks to store for {filename}")
        return

    _delete_document_chunks(filename)

    base_meta = {"filename": filename, "document_type": document_type}
    if extra_metadata:
        base_meta.update(extra_metadata)

    _collection.add(
        documents=chunks,
        metadatas=[dict(base_meta) for _ in chunks],
        ids=[str(uuid4()) for _ in chunks],
    )
    logger.info(
        f"Stored {len(chunks)} chunks | filename={filename} | type={document_type}"
        + (f" | extra={list(extra_metadata.keys())}" if extra_metadata else "")
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
