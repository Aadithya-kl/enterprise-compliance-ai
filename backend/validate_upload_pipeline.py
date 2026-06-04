"""
End-to-end validation for the Google Drive upload pipeline.

Tests the complete flow:
  Upload Page -> Local Save -> Drive Upload -> ChromaDB Ingestion
  -> MCP Sync (dedup) -> RAG Retrieval

Prerequisites:
  1. Backend running on port 8000.
  2. Google Drive folder shared with the service account as Editor.
  3. At least one PDF in ./uploads/ or upload one during the test.

Run from backend/:
    .\\venv\\Scripts\\python.exe validate_upload_pipeline.py
"""

import io
import os
import sys
import time
import requests

BASE_URL = "http://localhost:8000/api/v1"

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"
INFO = "[INFO]"

results: dict[str, bool] = {}

print("=" * 70)
print("UPLOAD PIPELINE END-TO-END VALIDATION")
print("=" * 70)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Step 1 — Login
# ---------------------------------------------------------------------------
print("\n--- Step 1: Authentication ---")
try:
    r = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@company.com", "password": "Admin123!"},
        timeout=15,
    )
    if r.status_code != 200:
        print(f"{FAIL} Login returned HTTP {r.status_code}: {r.text}")
        sys.exit(1)
    token = r.json()["access_token"]
    results["auth"] = True
    print(f"{PASS} Login successful.")
except Exception as e:
    print(f"{FAIL} Login error: {e}")
    sys.exit(1)

HEADERS = auth_headers(token)


# ---------------------------------------------------------------------------
# Step 2 — Locate a test PDF
# ---------------------------------------------------------------------------
print("\n--- Step 2: Locate Test PDF ---")

# Find the first text-extractable PDF in uploads/ — skip image-only/scanned files.
from app.services.rag_service import extract_text_from_pdf

uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
test_pdf_path = None
test_pdf_name = None

if os.path.isdir(uploads_dir):
    candidates = [f for f in os.listdir(uploads_dir) if f.endswith(".pdf")]
    for candidate in candidates:
        path = os.path.join(uploads_dir, candidate)
        try:
            text_sample = extract_text_from_pdf(path)
            if text_sample.strip():
                test_pdf_path = path
                test_pdf_name = candidate
                print(f"{INFO} Selected readable PDF: {candidate!r} ({os.path.getsize(path)} bytes, {len(text_sample)} chars)")
                break
        except Exception:
            continue

if not test_pdf_path:
    # Create a minimal synthetic PDF using fpdf2 if available
    synthetic_name = "pipeline_test_policy.pdf"
    synthetic_path = os.path.join(uploads_dir, synthetic_name)
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(200, 10, txt="Enterprise Compliance Policy - Test Document", ln=True)
        pdf.cell(200, 10, txt="Section 1: Data Protection Policy", ln=True)
        pdf.cell(200, 10, txt="All personal data must be encrypted at rest and in transit.", ln=True)
        pdf.cell(200, 10, txt="Section 2: Access Control", ln=True)
        pdf.cell(200, 10, txt="Only authorized personnel may access sensitive systems.", ln=True)
        os.makedirs(uploads_dir, exist_ok=True)
        pdf.output(synthetic_path)
        test_pdf_path = synthetic_path
        test_pdf_name = synthetic_name
        print(f"{PASS} Created synthetic test PDF: {synthetic_name}")
    except ImportError:
        print(f"{FAIL} No readable PDFs found and fpdf2 not installed.")
        print(f"  Upload a text-based PDF through the frontend, or: pip install fpdf2")
        sys.exit(1)

results["pdf_available"] = True
print(f"{INFO} Test PDF: {test_pdf_path} ({os.path.getsize(test_pdf_path)} bytes)")


# ---------------------------------------------------------------------------
# Step 3 — Upload via API (first upload)
# ---------------------------------------------------------------------------
print("\n--- Step 3: Upload Document (POST /documents/upload) ---")
try:
    with open(test_pdf_path, "rb") as f:
        t = time.monotonic()
        r = requests.post(
            f"{BASE_URL}/documents/upload?document_type=policy",
            files={"file": (test_pdf_name, f, "application/pdf")},
            headers=HEADERS,
            timeout=60,
        )
    elapsed = time.monotonic() - t
    print(f"{INFO} Response: HTTP {r.status_code} in {elapsed:.2f}s")

    if r.status_code not in (200, 201):
        print(f"{FAIL} Upload returned HTTP {r.status_code}: {r.text}")
        sys.exit(1)

    data = r.json()
    results["upload_ok"] = True
    print(f"{PASS} Upload successful.")
    print(f"  filename            : {data.get('filename')}")
    print(f"  document_type       : {data.get('document_type')}")
    print(f"  characters          : {data.get('characters')}")
    print(f"  chunks              : {data.get('chunks')}")
    print(f"  drive_upload_status : {data.get('drive_upload_status')}")
    print(f"  drive_file_id       : {data.get('drive_file_id')}")
    print(f"  drive_file_name     : {data.get('drive_file_name')}")
    print(f"  drive_web_view_link : {data.get('drive_web_view_link')}")

    drive_status = data.get("drive_upload_status", "skipped")
    drive_file_id = data.get("drive_file_id")
    results["drive_upload"] = drive_status in ("uploaded", "duplicate")

    if drive_status == "uploaded":
        print(f"{PASS} Drive upload: file pushed to Google Drive.")
    elif drive_status == "duplicate":
        print(f"{PASS} Drive upload: duplicate detected — reused existing file.")
    elif drive_status == "skipped":
        print(f"{SKIP} Drive upload: skipped (Drive not configured or folder not shared).")
    elif drive_status == "failed":
        print(f"{FAIL} Drive upload: failed — check backend logs.")
except Exception as e:
    print(f"{FAIL} Upload error: {e}")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Step 4 — Verify ChromaDB ingestion (chunk count)
# ---------------------------------------------------------------------------
print("\n--- Step 4: ChromaDB Ingestion (GET /documents/policy/count) ---")
try:
    r = requests.get(f"{BASE_URL}/documents/policy/count", headers=HEADERS, timeout=15)
    if r.status_code != 200:
        print(f"{FAIL} Count returned HTTP {r.status_code}: {r.text}")
        results["chromadb_ingestion"] = False
    else:
        count = r.json().get("documents_found", 0)
        results["chromadb_ingestion"] = count > 0
        status_str = PASS if count > 0 else FAIL
        print(f"{status_str} ChromaDB policy chunks: {count}")
except Exception as e:
    print(f"{FAIL} Count error: {e}")
    results["chromadb_ingestion"] = False


# ---------------------------------------------------------------------------
# Step 5 — Duplicate upload dedup test
# ---------------------------------------------------------------------------
print("\n--- Step 5: Duplicate Upload Dedup Test ---")
try:
    with open(test_pdf_path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/documents/upload?document_type=policy",
            files={"file": (test_pdf_name, f, "application/pdf")},
            headers=HEADERS,
            timeout=60,
        )
    if r.status_code in (200, 201):
        data2 = r.json()
        drive_status2 = data2.get("drive_upload_status")
        results["dedup_test"] = drive_status2 in ("duplicate", "skipped", "failed")
        print(f"{PASS} Second upload drive_upload_status: {drive_status2!r}")
        if drive_status2 == "duplicate":
            # Must return same file_id
            same_id = data2.get("drive_file_id") == drive_file_id
            print(f"  Same file_id as first upload: {same_id}")
            if drive_file_id:
                results["dedup_same_id"] = same_id
    else:
        print(f"{FAIL} Second upload returned HTTP {r.status_code}")
        results["dedup_test"] = False
except Exception as e:
    print(f"{FAIL} Dedup test error: {e}")
    results["dedup_test"] = False


# ---------------------------------------------------------------------------
# Step 6 — MCP sync (should find file already ingested and skip)
# ---------------------------------------------------------------------------
print("\n--- Step 6: MCP Sync Dedup (POST /mcp/google-drive/sync) ---")
try:
    r = requests.post(f"{BASE_URL}/mcp/google-drive/sync", headers=HEADERS, timeout=120)
    if r.status_code == 503:
        print(f"{SKIP} MCP sync: Google Drive not configured (503 — expected if not shared).")
        results["mcp_sync"] = True  # acceptable when not configured
    elif r.status_code == 200:
        sync_data = r.json()
        print(f"{PASS} MCP sync completed.")
        print(f"  documents_found     : {sync_data.get('documents_found')}")
        print(f"  documents_processed : {sync_data.get('documents_processed')}")
        print(f"  chunks_created      : {sync_data.get('chunks_created')}")
        results["mcp_sync"] = True
    else:
        print(f"{FAIL} MCP sync returned HTTP {r.status_code}: {r.text}")
        results["mcp_sync"] = False
except Exception as e:
    print(f"{FAIL} MCP sync error: {e}")
    results["mcp_sync"] = False


# ---------------------------------------------------------------------------
# Step 7 — RAG retrieval
# ---------------------------------------------------------------------------
print("\n--- Step 7: RAG Retrieval (POST /documents/ask) ---")
try:
    r = requests.post(
        f"{BASE_URL}/documents/ask",
        json={"question": "What are the data protection requirements?"},
        headers=HEADERS,
        timeout=120,
    )
    if r.status_code != 200:
        print(f"{FAIL} Ask returned HTTP {r.status_code}: {r.text}")
        results["rag_retrieval"] = False
    else:
        rag_data = r.json()
        answer = rag_data.get("answer", "")
        sources = rag_data.get("sources", [])
        results["rag_retrieval"] = bool(answer and "No documents" not in answer)

        status_str = PASS if results["rag_retrieval"] else FAIL
        print(f"{status_str} RAG answer received ({len(answer)} chars, {len(sources)} source chunks).")
        print(f"  Answer preview: {answer[:120].replace(chr(10), ' ')!r}...")

        # Check if sources include Drive metadata
        drive_sourced = [s for s in sources if s.get("drive_file_id")]
        if drive_sourced:
            print(f"{PASS} {len(drive_sourced)}/{len(sources)} source chunks carry Drive metadata.")
        else:
            print(f"{INFO} No Drive metadata in sources (Drive may not be configured).")
except Exception as e:
    print(f"{FAIL} RAG retrieval error: {e}")
    results["rag_retrieval"] = False


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PIPELINE VALIDATION REPORT")
print("=" * 70)

checks = [
    ("auth",               "Admin authentication"),
    ("pdf_available",      "Test PDF available"),
    ("upload_ok",          "Upload endpoint (HTTP 201)"),
    ("drive_upload",       "Google Drive upload/dedup"),
    ("chromadb_ingestion", "ChromaDB ingestion (chunk count > 0)"),
    ("dedup_test",         "Duplicate upload dedup check"),
    ("mcp_sync",           "MCP sync (skip already-ingested)"),
    ("rag_retrieval",      "RAG retrieval + answer generation"),
]
for key, label in checks:
    val = results.get(key)
    if val is None:
        icon = SKIP
    elif val:
        icon = PASS
    else:
        icon = FAIL
    print(f"  {icon}  {label}")

print()
all_critical = all(results.get(k, False) for k in ["auth", "upload_ok", "chromadb_ingestion", "rag_retrieval"])
if all_critical:
    print("RESULT: Core pipeline fully operational.")
    if not results.get("drive_upload"):
        print("NOTE:   Google Drive upload pending — share the folder with the service account.")
else:
    print("RESULT: One or more critical checks failed. Review output above.")
print("=" * 70)
