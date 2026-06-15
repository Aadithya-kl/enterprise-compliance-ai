# Duplicate File Prevention Report

## Overview
Duplicate document uploads and version conflicts are resolved through a robust hashing and matching system in the backend and an interactive conflict-resolution modal in the frontend.

---

## Technical Mechanism

### 1. Ingestion Pipeline Duplicate Detection (SHA-256 Hashing)
* **File Hashing**: Every uploaded file is processed to generate a SHA-256 hex digest:
  ```python
  def compute_file_hash(file_path: str) -> str:
      sha256 = hashlib.sha256()
      with open(file_path, "rb") as f:
          for block in iter(lambda: f.read(8192), b""):
              sha256.update(block)
      return sha256.hexdigest()
  ```
* **ChromaDB Metadata Search**: When a document is uploaded:
  1. The SHA-256 hash is compared against all existing chunk metadatas stored in ChromaDB.
  2. If an identical hash is found, the backend returns early with status `"duplicate"`, avoiding chunk recalculations, DB storage duplication, or Google Drive file pollution.
  3. If the filename matches an existing record but the SHA-256 hash is different, it triggers a `"version_conflict"`.

### 2. Version Overwrite vs. Concurrent Ingestion
* **Replace Option**: If a version conflict occurs, the API expects a `replace: bool` query parameter.
  * If `replace=true`, the backend deletes all existing chunks corresponding to that filename in ChromaDB before storing the new file chunks.
  * If `replace=false` or missing, the API halts ingestion and returns a `version_conflict` status.

---

## Frontend Integration & User Experience

### 1. Duplicate Ingestion Message
When the API returns `status: "duplicate"`, the frontend displays a message panel highlighting that the exact file content has already been indexed.

### 2. Version Conflict Resolution Modal
When the API returns `status: "version_conflict"`, the frontend displays an interactive dialog offering three options:
1. **Replace Existing**: Re-triggers the upload API with the `replace=true` query parameter, overwriting the document in both the local system and ChromaDB.
2. **Keep Both (Rename)**: Re-creates the file object locally by appending a `_v2` suffix to its filename (e.g. `Privacy_Policy_v2.pdf`) and uploads it.
3. **Cancel**: Closes the conflict resolution dialog without making changes.
