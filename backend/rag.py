import chromadb
import ollama
from pypdf import PdfReader

client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_or_create_collection(
    name="documents"
)

def extract_text(pdf_path):

    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text

    return text

def chunk_text(text, chunk_size=1000, overlap=200):

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk)

        start += chunk_size - overlap

    return chunks

from uuid import uuid4

def delete_document(filename):

    collection.delete(
        where={
            "filename": filename
        }
    )

def store_chunks(
    chunks,
    filename,
    document_type
):

    delete_document(filename)

    collection.add(
        documents=chunks,
        metadatas=[
            {
                "filename": filename,
                "document_type": document_type
            }
            for _ in chunks
        ],
        ids=[str(uuid4()) for _ in chunks]
    )

def search_chunks(query):

    results = collection.query(
        query_texts=[query],
        n_results=3
    )

    if not results["documents"] or not results["documents"][0]:
        return {
        "documents": [],
        "metadata": []
    }

    return {
    "documents": results["documents"][0],
    "metadata": results["metadatas"][0]
}

def get_documents_by_type(document_type):

    results = collection.get(
        where={
            "document_type": document_type
        }
    )

    return results["documents"]

def generate_answer(question, chunks):

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

    response = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]