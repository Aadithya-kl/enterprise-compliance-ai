# Google Drive Integration Setup

This document covers the complete configuration required to enable the Google Drive MCP connector for the Enterprise Compliance AI Platform.

---

## Architecture

The Google Drive connector is an MCP (Model Context Protocol) source that:
1. Authenticates with Google Drive using a Service Account (no OAuth user flow required).
2. Lists all PDF files in the configured folder, including sub-folders recursively.
3. Downloads and extracts text from each PDF.
4. Chunks the text and stores it in ChromaDB for RAG retrieval.
5. Tracks already-ingested files so subsequent syncs only process new documents.

---

## Prerequisites

- A Google account with access to Google Cloud Console.
- Owner or Editor access to the Google Drive folder containing compliance documents.
- Python environment with the `google-api-python-client` and `google-auth` packages installed:

```
pip install google-api-python-client google-auth
```

---

## Step 1 — Create a Google Cloud Project

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com).
2. Click **Select a project** in the top navigation bar.
3. Click **New Project**.
4. Enter a project name (e.g., `compliance-ai-platform`) and click **Create**.
5. Ensure the new project is selected in the top bar.

---

## Step 2 — Enable the Google Drive API

1. In the Cloud Console, go to **APIs & Services > Library**.
2. Search for **Google Drive API**.
3. Click on **Google Drive API** and click **Enable**.

---

## Step 3 — Create a Service Account

1. Go to **APIs & Services > Credentials**.
2. Click **Create Credentials > Service Account**.
3. Fill in:
   - **Service account name**: `compliance-ai-drive-reader`
   - **Service account ID**: auto-filled
   - **Description**: Read-only access to compliance document folder
4. Click **Create and Continue**.
5. Under **Grant this service account access to project**, click **Continue** (no role required for Drive access — access is granted at folder level).
6. Click **Done**.

---

## Step 4 — Generate a Service Account Key

1. In **APIs & Services > Credentials**, click on the service account you just created.
2. Go to the **Keys** tab.
3. Click **Add Key > Create new key**.
4. Select **JSON** and click **Create**.
5. A JSON key file will be downloaded automatically (e.g., `compliance-ai-drive-reader-<id>.json`).
6. Store this file securely — it grants API access to your project.
7. Copy this file to a safe location on the server running the backend, for example:
   ```
   backend/credentials/service-account.json
   ```

---

## Step 5 — Share the Drive Folder with the Service Account

The service account does not have access to any Drive files by default. You must explicitly share the folder.

1. Open [Google Drive](https://drive.google.com) in your browser.
2. Navigate to the folder containing your compliance PDFs.
3. Right-click the folder and select **Share**.
4. In the **Share** dialog, paste the service account's email address. It looks like:
   ```
   compliance-ai-drive-reader@<your-project-id>.iam.gserviceaccount.com
   ```
   This email is visible on the service account details page in Cloud Console.
5. Set the permission to **Viewer** (read-only is sufficient).
6. Click **Send** (or **Share**).

---

## Step 6 — Find the Folder ID

1. Open the shared folder in Google Drive.
2. Look at the URL in your browser address bar:
   ```
   https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ
   ```
3. The long alphanumeric string at the end is the Folder ID:
   ```
   1aBcDeFgHiJkLmNoPqRsTuVwXyZ
   ```

---

## Step 7 — Configure Environment Variables

Open `backend/.env` and set:

```env
GOOGLE_DRIVE_ENABLED=true
GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/service-account.json
GOOGLE_DRIVE_FOLDER_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ
```

If using a relative path, it must be relative to the directory from which `uvicorn` is started (typically `backend/`).

---

## Step 8 — Verify the Connection

After restarting the backend, verify that the credentials work:

```bash
curl -X GET http://localhost:8000/api/v1/mcp/google-drive/verify \
  -H "Authorization: Bearer <your-admin-jwt>"
```

Expected response:
```json
{
  "connected": true,
  "message": "Connected. Folder: 'Compliance Documents' (id=1aBcDeFgHiJkLmNoPqRsTuVwXyZ)"
}
```

---

## Step 9 — Trigger a Sync

Sync PDF documents from Google Drive into ChromaDB:

```bash
curl -X POST http://localhost:8000/api/v1/mcp/google-drive/sync \
  -H "Authorization: Bearer <your-admin-jwt>"
```

Expected response:
```json
{
  "documents_found": 12,
  "documents_processed": 12,
  "chunks_created": 247,
  "status": "success"
}
```

Subsequent syncs will skip already-processed files. Only new files added to the folder will be downloaded.

---

## Document Naming Convention

The connector infers the document type from the filename:

| Filename contains | Inferred type |
|---|---|
| `policy`, `pol` | `policy` |
| `regulation`, `reg` | `regulation` |
| anything else | `general` |

Name your files accordingly. For example:
- `data-protection-policy-2024.pdf` → type `policy`
- `gdpr-regulation-v3.pdf` → type `regulation`

---

## Troubleshooting

### `Connection failed: <HttpError 403>`
The service account does not have access to the folder. Verify Step 5 was completed and the correct service account email was shared.

### `Service account file not found`
The path specified in `GOOGLE_SERVICE_ACCOUNT_FILE` does not exist on the server. Use an absolute path.

### `GOOGLE_DRIVE_ENABLED is false`
Set `GOOGLE_DRIVE_ENABLED=true` in `.env` and restart the backend.

### Documents ingested but not appearing in RAG search
Check the inferred document type. The workflow uses type `policy` and `regulation` specifically. If your files are ingested as `general`, rename them to include `policy` or `regulation` in the filename.

### `documents_found: 0`
Verify that:
1. The folder contains PDF files (not Google Docs or Sheets — those are not supported).
2. The folder ID in `.env` is correct.
3. The service account has been granted at least Viewer access to the folder.

---

## Security Notes

- The service account key JSON file must not be committed to version control. Add it to `.gitignore`.
- Use the narrowest possible permissions: the service account only needs `drive.readonly` scope.
- Rotate the service account key periodically (quarterly recommended for production).
- In production deployments, prefer storing the key contents as a Secret Manager secret rather than a file on disk, and update `_build_drive_service()` accordingly.
