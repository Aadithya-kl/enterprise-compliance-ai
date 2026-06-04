"""
Google Drive configuration diagnostic script.
Run from backend/ directory:
    .\\venv\\Scripts\\python.exe diagnose_gdrive.py
"""
import os
import sys

print("=" * 60)
print("GOOGLE DRIVE CONFIGURATION DIAGNOSTIC")
print("=" * 60)

# ---- 1. Raw .env parsing ----
print("\n[1] RAW .env LINES (GOOGLE* vars):")
try:
    with open(".env", "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.rstrip("\n")
            if "GOOGLE" in stripped.upper() or "SERVICE" in stripped.upper():
                print(f"  Line {lineno:02d}: {repr(stripped)}")
except Exception as e:
    print(f"  ERROR reading .env: {e}")

# ---- 2. Pydantic-settings loaded values (fresh instance) ----
print("\n[2] PYDANTIC SETTINGS (fresh, no lru_cache):")
try:
    from app.core.config import Settings
    s = Settings()
    print(f"  GOOGLE_DRIVE_ENABLED       : {repr(s.GOOGLE_DRIVE_ENABLED)}")
    print(f"  GOOGLE_SERVICE_ACCOUNT_FILE: {repr(s.GOOGLE_SERVICE_ACCOUNT_FILE)}")
    print(f"  GOOGLE_DRIVE_FOLDER_ID     : {repr(s.GOOGLE_DRIVE_FOLDER_ID)}")
    print(f"  GOOGLE_DRIVE_CREDENTIALS_JSON: {repr(s.GOOGLE_DRIVE_CREDENTIALS_JSON)}")
except Exception as e:
    print(f"  ERROR loading settings: {e}")
    sys.exit(1)

# ---- 3. Path existence checks ----
print("\n[3] PATH EXISTENCE CHECKS:")
path = s.GOOGLE_SERVICE_ACCOUNT_FILE
print(f"  Raw value           : {repr(path)}")
print(f"  len(path)           : {len(path)}")
print(f"  os.path.exists()    : {os.path.exists(path)}")
print(f"  os.path.abspath()   : {os.path.abspath(path)}")

normed = os.path.normpath(path)
print(f"  os.path.normpath()  : {repr(normed)}")
print(f"  normpath exists     : {os.path.exists(normed)}")

expanded = os.path.expandvars(os.path.expanduser(path))
print(f"  expandvars/user     : {repr(expanded)}")
print(f"  expanded exists     : {os.path.exists(expanded)}")

# ---- 4. Direct known path check ----
print("\n[4] DIRECT PATH CHECK:")
direct = "C:\\Users\\loges\\compliance-ai\\backend\\compliance-ai-498415-870bf0a6da98.json"
print(f"  Direct path         : {repr(direct)}")
print(f"  Direct exists       : {os.path.exists(direct)}")
if os.path.exists(direct):
    print(f"  File size           : {os.path.getsize(direct)} bytes")

# Same with forward slashes
forward = "C:/Users/loges/compliance-ai/backend/compliance-ai-498415-870bf0a6da98.json"
print(f"  Forward slash path  : {repr(forward)}")
print(f"  Forward slash exists: {os.path.exists(forward)}")

# ---- 5. Try Google auth ----
print("\n[5] GOOGLE AUTHENTICATION TEST:")
cred_path = direct if os.path.exists(direct) else path
try:
    from google.oauth2 import service_account
    credentials = service_account.Credentials.from_service_account_file(
        cred_path,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    print(f"  Credentials loaded  : OK")
    print(f"  Service account     : {credentials.service_account_email}")
except Exception as e:
    print(f"  Credentials load FAILED: {e}")
    sys.exit(1)

# ---- 6. Try Drive API client ----
print("\n[6] DRIVE API CLIENT TEST:")
try:
    from googleapiclient.discovery import build
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    print("  Drive client built  : OK")
except Exception as e:
    print(f"  Drive client FAILED : {e}")
    sys.exit(1)

# ---- 7. Try folder access ----
folder_id = s.GOOGLE_DRIVE_FOLDER_ID
print(f"\n[7] FOLDER ACCESS TEST (id={folder_id}):")
if not folder_id:
    print("  SKIPPED — GOOGLE_DRIVE_FOLDER_ID is empty")
else:
    try:
        folder = (
            service.files()
            .get(fileId=folder_id, fields="id, name, mimeType")
            .execute()
        )
        print(f"  Folder name         : {folder.get('name')}")
        print(f"  Folder ID           : {folder.get('id')}")
        print(f"  Folder type         : {folder.get('mimeType')}")
        print("  Folder access       : OK")
    except Exception as e:
        print(f"  Folder access FAILED: {e}")

# ---- 8. List PDF files ----
print(f"\n[8] PDF FILE LISTING:")
if not folder_id:
    print("  SKIPPED — no folder ID")
else:
    try:
        query = (
            f"'{folder_id}' in parents "
            f"and mimeType='application/pdf' "
            f"and trashed=false"
        )
        response = service.files().list(
            q=query,
            fields="files(id, name, size)",
            pageSize=20
        ).execute()
        files = response.get("files", [])
        print(f"  PDF files found     : {len(files)}")
        for f in files:
            print(f"    - {f.get('name')} (id={f.get('id')})")
        if not files:
            print("  NOTE: No PDF files in folder. Upload a PDF to test sync.")
    except Exception as e:
        print(f"  File listing FAILED : {e}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
