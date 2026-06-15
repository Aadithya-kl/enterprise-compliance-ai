# Ask Questions Bug Report — Root Cause Analysis

## Symptom
When users submitted questions on the **Ask Questions** page, the API returned an HTTP 500 `Internal Server Error` response:
```text
Internal Server Error
```

---

## Technical Analysis of Root Causes

### 1. Bug A: Metadata Shadowing (Scope Collision)
* **File**: `backend/app/api/v1/documents.py`
* **Line**: 296 (prior to fix)
* **Code snippet**:
  ```python
  for doc, meta, dist in zip(chunks, metadatas, distances):
      meta = getattr(doc, "metadata", {}) or {}  # ← SHADOWS the loop variable
  ```
* **Explanation**: The loop variable `meta` contains the retrieved chunk's metadata dictionary returned by ChromaDB. However, the first statement inside the loop reassigned `meta` using `getattr(doc, "metadata", {})`. Since `doc` is a plain Python string containing the text content of the chunk, it does not have a `metadata` attribute. Thus, `getattr` always returned `{}`. This effectively wiped out the actual metadata retrieved from the database and replaced it with an empty dictionary for every iteration.

### 2. Bug B: Undefined Variable (NameError)
* **File**: `backend/app/api/v1/documents.py`
* **Line**: 302 (prior to fix)
* **Code snippet**:
  ```python
  header = f"[File Name: {fname} | ...]"  # ← `fname` is undefined
  ```
* **Explanation**: The string formatting expression referenced `fname`, but no variable named `fname` existed in the scope of the `ask_question` function. This caused Python to raise a `NameError: name 'fname' is not defined` immediately upon execution, aborting the request and causing a 500 error.

### 3. Lack of Resilience and Connectivity Checks
* **File**: `backend/app/api/v1/documents.py`
* **Explanation**: The Q&A pipeline directly invoked the Ollama client via `generate_answer()` without validating if the Ollama service was reachable or running the `llama3` model. If Ollama was offline or loading, it raised a socket connection exception, which propagated upwards unhandled. Additionally, the route lacked a comprehensive try/except handler at the top level, allowing any internal runtime errors to bubble up to FastAPI's default handler as a generic HTTP 500 Internal Server Error instead of returning a detailed, user-friendly error payload.
