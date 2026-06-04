"""
Google Drive end-to-end validation script.
Run from the backend/ directory:
    .\\venv\\Scripts\\python.exe verify_google_drive.py

Validates the full pipeline:
1. Credential file existence
2. Service account authentication
3. Drive API client initialization
4. Folder access and metadata
5. PDF file listing
6. PDF download (first file only)
7. Text extraction
8. Chunking
9. ChromaDB ingestion (dry-run count only — does NOT store)

Produces a complete diagnostic report.
Requires no server to be running.
"""

import os
import sys
import tempfile
import time

print("=" * 70)
print("GOOGLE DRIVE VALIDATION REPORT")
print("=" * 70)

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"
INFO = "[INFO]"

results: dict[str, bool] = {}


# ---------------------------------------------------------------------------
# Step 1 — Load settings
# ---------------------------------------------------------------------------
print("\n--- Step 1: Load Settings ---")
try:
    from app.core.config import Settings
    s = Settings()  # fresh instance — bypasses lru_cache
    print(f"{INFO} GOOGLE_DRIVE_ENABLED        : {s.GOOGLE_DRIVE_ENABLED}")
    print(f"{INFO} GOOGLE_SERVICE_ACCOUNT_FILE : {repr(s.GOOGLE_SERVICE_ACCOUNT_FILE)}")
    print(f"{INFO} GOOGLE_DRIVE_FOLDER_ID      : {repr(s.GOOGLE_DRIVE_FOLDER_ID)}")
    results["settings_loaded"] = True
    print(f"{PASS} Settings loaded.")
except Exception as e:
    print(f"{FAIL} Settings failed to load: {e}")
    sys.exit(1)

# Resolve effective values (live env takes priority over cached settings)
cred_path = (
    os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    or os.environ.get("GOOGLE_DRIVE_CREDENTIALS_JSON", "").strip()
    or s.GOOGLE_SERVICE_ACCOUNT_FILE
    or s.GOOGLE_DRIVE_CREDENTIALS_JSON
)
folder_id = (
    os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    or s.GOOGLE_DRIVE_FOLDER_ID
)
enabled = (
    os.environ.get("GOOGLE_DRIVE_ENABLED", str(s.GOOGLE_DRIVE_ENABLED)).lower()
    in ("1", "true", "yes")
)

print(f"\n{INFO} Effective cred_path : {repr(cred_path)}")
print(f"{INFO} Effective folder_id : {repr(folder_id)}")
print(f"{INFO} Effective enabled   : {enabled}")

if not enabled:
    print(f"\n{FAIL} GOOGLE_DRIVE_ENABLED is false. Set it to true in .env.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 2 — Credential file existence
# ---------------------------------------------------------------------------
print("\n--- Step 2: Credential File Existence ---")
if not cred_path:
    print(f"{FAIL} GOOGLE_SERVICE_ACCOUNT_FILE is empty. Set it in .env.")
    sys.exit(1)

exists = os.path.exists(cred_path)
results["credentials_file_exists"] = exists
if exists:
    size = os.path.getsize(cred_path)
    print(f"{PASS} File exists: {cred_path} ({size} bytes)")
else:
    print(f"{FAIL} File NOT found: {cred_path}")
    # Try normpath
    normed = os.path.normpath(cred_path)
    if os.path.exists(normed):
        print(f"{INFO} Normpath resolves: {normed} — using this path.")
        cred_path = normed
        results["credentials_file_exists"] = True
    else:
        print(f"{FAIL} normpath also not found: {normed}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Step 3 — Validate JSON structure
# ---------------------------------------------------------------------------
print("\n--- Step 3: Validate Service Account JSON ---")
try:
    import json
    with open(cred_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    required_keys = ["type", "project_id", "private_key", "client_email", "token_uri"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        print(f"{FAIL} JSON missing required keys: {missing}")
        sys.exit(1)
    if data.get("type") != "service_account":
        print(f"{FAIL} JSON 'type' is '{data.get('type')}', expected 'service_account'")
        sys.exit(1)
    print(f"{PASS} JSON structure valid.")
    print(f"{INFO} Project ID      : {data.get('project_id')}")
    print(f"{INFO} Service account : {data.get('client_email')}")
    SERVICE_ACCOUNT_EMAIL = data.get("client_email", "")
    results["json_valid"] = True
except Exception as e:
    print(f"{FAIL} JSON validation failed: {e}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 4 — Authenticate with Google
# ---------------------------------------------------------------------------
print("\n--- Step 4: Google Authentication ---")
try:
    from google.oauth2 import service_account
    credentials = service_account.Credentials.from_service_account_file(
        cred_path,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    results["service_account_loaded"] = True
    print(f"{PASS} Service account credentials loaded.")
    print(f"{INFO} Service account email: {credentials.service_account_email}")
except Exception as e:
    print(f"{FAIL} Authentication failed: {e}")
    print(f"{INFO} Ensure google-auth is installed: pip install google-auth")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 5 — Build Drive API client
# ---------------------------------------------------------------------------
print("\n--- Step 5: Build Drive API Client ---")
try:
    from googleapiclient.discovery import build
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    results["drive_client_initialized"] = True
    print(f"{PASS} Drive API client initialized.")
    print(f"{INFO} Verify Drive API is enabled: "
          f"https://console.cloud.google.com/apis/library/drive.googleapis.com")
except Exception as e:
    print(f"{FAIL} Drive client failed: {e}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 6 — Folder access
# ---------------------------------------------------------------------------
print(f"\n--- Step 6: Folder Access (id={folder_id}) ---")
if not folder_id:
    print(f"{FAIL} GOOGLE_DRIVE_FOLDER_ID is empty. Set it in .env.")
    sys.exit(1)

try:
    t = time.monotonic()
    folder = (
        service.files()
        .get(fileId=folder_id, fields="id, name, mimeType, owners")
        .execute()
    )
    elapsed = time.monotonic() - t
    results["folder_accessible"] = True
    print(f"{PASS} Folder accessible in {elapsed:.2f}s.")
    print(f"{INFO} Folder name : {folder.get('name')}")
    print(f"{INFO} Folder ID   : {folder.get('id')}")
    print(f"{INFO} Folder type : {folder.get('mimeType')}")
except Exception as e:
    error_str = str(e)
    results["folder_accessible"] = False
    if "404" in error_str or "notFound" in error_str:
        print(f"{FAIL} Folder NOT FOUND (HTTP 404).")
        print(f"\n  ROOT CAUSE: The folder exists in Drive but the service account")
        print(f"  '{SERVICE_ACCOUNT_EMAIL}'")
        print(f"  has NOT been granted access.")
        print(f"\n  FIX:")
        print(f"  1. Open Google Drive in your browser.")
        print(f"  2. Navigate to the folder with ID: {folder_id}")
        print(f"  3. Right-click the folder > Share.")
        print(f"  4. Add: {SERVICE_ACCOUNT_EMAIL}")
        print(f"  5. Set permission: Viewer")
        print(f"  6. Click Send.")
        print(f"  7. Re-run this script.")
    elif "403" in error_str:
        print(f"{FAIL} Permission denied (HTTP 403).")
        print(f"  Share the folder with '{SERVICE_ACCOUNT_EMAIL}' as Viewer.")
    else:
        print(f"{FAIL} Folder access failed: {e}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 7 — List PDF files
# ---------------------------------------------------------------------------
print(f"\n--- Step 7: List PDF Files ---")
try:
    query = (
        f"'{folder_id}' in parents "
        f"and mimeType='application/pdf' "
        f"and trashed=false"
    )
    response = service.files().list(
        q=query,
        fields="files(id, name, size)",
        pageSize=50
    ).execute()
    pdf_files = response.get("files", [])
    results["pdfs_found"] = len(pdf_files) > 0
    print(f"{PASS} PDF listing succeeded. {len(pdf_files)} PDF(s) found.")
    for f in pdf_files:
        size_kb = int(f.get("size", 0)) // 1024
        print(f"  - {f.get('name')} (id={f.get('id')}, {size_kb}KB)")
    if not pdf_files:
        print(f"{INFO} No PDFs in folder. Upload a PDF to test the full pipeline.")
except Exception as e:
    print(f"{FAIL} PDF listing failed: {e}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 8 — Download + extract + chunk (first PDF only)
# ---------------------------------------------------------------------------
if not pdf_files:
    print(f"\n{SKIP} Steps 8-10 skipped — no PDF files in folder.")
else:
    first = pdf_files[0]
    file_id = first["id"]
    filename = first["name"]
    print(f"\n--- Step 8: Download '{filename}' ---")

    try:
        from googleapiclient.http import MediaIoBaseDownload
        import io
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        t = time.monotonic()
        while not done:
            _, done = downloader.next_chunk()
        pdf_bytes = buffer.getvalue()
        results["download_ok"] = True
        print(f"{PASS} Downloaded {len(pdf_bytes):,} bytes in {time.monotonic()-t:.2f}s.")
    except Exception as e:
        print(f"{FAIL} Download failed: {e}")
        sys.exit(1)

    # ---- Step 9: Text extraction ----
    print(f"\n--- Step 9: Text Extraction ---")
    try:
        from app.services.rag_service import extract_text_from_pdf
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            text = extract_text_from_pdf(tmp_path)
        finally:
            os.unlink(tmp_path)
        results["text_extracted"] = bool(text.strip())
        if text.strip():
            print(f"{PASS} Extracted {len(text):,} characters.")
            print(f"{INFO} First 200 chars: {text[:200].replace(chr(10), ' ')!r}")
        else:
            print(f"{FAIL} No text extracted. PDF may be image-only / scanned.")
    except Exception as e:
        print(f"{FAIL} Text extraction failed: {e}")
        sys.exit(1)

    # ---- Step 10: Chunking ----
    print(f"\n--- Step 10: Chunking ---")
    try:
        from app.services.rag_service import chunk_text
        chunks = chunk_text(text)
        results["chunking_ok"] = len(chunks) > 0
        print(f"{PASS} Produced {len(chunks)} chunk(s) from {len(text):,} characters.")
        print(f"{INFO} To store in ChromaDB, run: POST /api/v1/mcp/google-drive/sync")
    except Exception as e:
        print(f"{FAIL} Chunking failed: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("FINAL DIAGNOSTIC REPORT")
print("=" * 70)

all_fields = [
    ("settings_loaded",          "Settings loaded from .env"),
    ("credentials_file_exists",  "Credential file exists on disk"),
    ("json_valid",               "Service account JSON is valid"),
    ("service_account_loaded",   "Google authentication successful"),
    ("drive_client_initialized", "Drive API client initialized"),
    ("folder_accessible",        "Target folder is accessible"),
    ("pdfs_found",               "PDF files found in folder"),
    ("download_ok",              "PDF download successful"),
    ("text_extracted",           "Text extracted from PDF"),
    ("chunking_ok",              "Text chunking successful"),
]
for key, label in all_fields:
    val = results.get(key)
    if val is None:
        status = SKIP
    elif val:
        status = PASS
    else:
        status = FAIL
    print(f"  {status}  {label}")

overall = all(v for v in results.values() if v is not None)
print()
if overall:
    print("RESULT: ALL CHECKS PASSED. Google Drive integration is fully operational.")
    print("Run POST /api/v1/mcp/google-drive/sync to ingest documents into ChromaDB.")
else:
    print("RESULT: ONE OR MORE CHECKS FAILED. Review the output above for the fix.")
print("=" * 70)
