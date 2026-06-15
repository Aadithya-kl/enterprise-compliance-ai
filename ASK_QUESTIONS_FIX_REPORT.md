# Ask Questions Fix Report

## Overview
To resolve the `Internal Server Error` failures and build a robust, resilient Q&A pipeline, we applied fixes to the router, schema, and service modules.

---

## Code Modification Details

### 1. Fix for Metadata Shadowing and NameError
* **File**: [documents.py](file:///c:/Users/loges/compliance-ai/backend/app/api/v1/documents.py)
* **Changes**:
  * Removed the line `meta = getattr(doc, "metadata", {}) or {}` to prevent clearing retrieved database records.
  * Extracted the filename safely using `filename = meta.get("filename", "Unknown")`.
  * Updated the header formatting to use `filename` instead of the undefined `fname` variable.

```python
        for doc, meta, dist in zip(chunks, metadatas, distances):
            if not meta:
                meta = {}
            filename = meta.get("filename", "Unknown")
            chunk_id = meta.get("id", str(uuid.uuid4())[:8])
            conf = max(0.0, 100.0 - (float(dist) * 100.0)) if dist is not None else 0.0
            page_num = meta.get("page_number", "N/A")
            heading = meta.get("section_heading", "N/A")

            header = (
                f"[File Name: {filename} | Page Number: {page_num} | "
                f"Chunk ID: {chunk_id} | Section Heading: {heading} | "
                f"Confidence Score: {conf:.1f}%]"
            )
            formatted_chunks.append(f"{header}\n{doc}")
```

### 2. Graceful Error Handling and Exception Boundaries
* **File**: [documents.py](file:///c:/Users/loges/compliance-ai/backend/app/api/v1/documents.py)
* **Changes**:
  * Wrapped the entire router logic in a try-except structure.
  * Added active Ollama availability checks using `ollama.list()` before calling the language model.
  * If the model or service is offline, it returns a structured response explaining that the service is down, rather than triggering a generic HTTP 500.

```python
        # ---- Check Ollama availability before LLM call ----
        try:
            ollama_client.list()
        except Exception as ollama_err:
            logger.error(f"Ollama is not reachable: {ollama_err}")
            return QuestionResponse(
                question=payload.question,
                answer=(
                    "The AI language model (Ollama) is currently unavailable. "
                    "Please ensure Ollama is running and try again."
                ),
                sources=enhanced_sources,
                diagnostics=diagnostics,
            )
```

---

## Validation Summary
* The backend API was verified to compile and run successfully.
* The `/ask` endpoint now correctly catches NameErrors, connection errors, and missing metadata scenarios, returning a clean JSON error response structure.
* Frontend Q&A page handles errors gracefully without page crashes.
