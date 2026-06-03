"""
Google Drive MCP source.
Downloads PDF files from a configured Google Drive folder.

Configuration (in .env):
    GOOGLE_DRIVE_CREDENTIALS_JSON=<path to service account JSON>
    GOOGLE_DRIVE_FOLDER_ID=<folder ID from Drive URL>

Requires: pip install google-api-python-client google-auth
"""

import io
import os
import tempfile

from app.core.config import settings
from app.core.logging import get_logger
from app.mcp.base import MCPDocument, MCPSource

logger = get_logger(__name__)


class GoogleDriveMCPSource(MCPSource):
    """Fetches PDF documents from a Google Drive folder via Service Account."""

    @property
    def source_name(self) -> str:
        return "google_drive"

    def is_configured(self) -> bool:
        return bool(
            settings.GOOGLE_DRIVE_CREDENTIALS_JSON
            and settings.GOOGLE_DRIVE_FOLDER_ID
        )

    def fetch_documents(self) -> list[MCPDocument]:
        if not self.is_configured():
            logger.info(
                "Google Drive MCP: not configured "
                "(GOOGLE_DRIVE_CREDENTIALS_JSON or GOOGLE_DRIVE_FOLDER_ID missing). "
                "Skipping."
            )
            return []

        try:
            service = self._build_drive_service()
        except Exception as exc:
            logger.error(f"Google Drive MCP: authentication failed: {exc}")
            return []

        try:
            files = self._list_pdf_files(service)
        except Exception as exc:
            logger.error(f"Google Drive MCP: failed to list files: {exc}")
            return []

        from app.services.rag_service import extract_text_from_pdf

        documents: list[MCPDocument] = []
        for file_meta in files:
            file_id = file_meta["id"]
            filename = file_meta["name"]
            try:
                pdf_bytes = self._download_file(service, file_id)
                with tempfile.NamedTemporaryFile(
                    suffix=".pdf", delete=False
                ) as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name

                text = extract_text_from_pdf(tmp_path)
                os.unlink(tmp_path)

                if not text.strip():
                    logger.warning(
                        f"Google Drive MCP: no text in {filename}, skipping."
                    )
                    continue

                documents.append(
                    MCPDocument(
                        title=filename,
                        content=text,
                        source=self.source_name,
                        document_type=self._infer_type(filename),
                        metadata={
                            "drive_file_id": file_id,
                            "filename": filename,
                        },
                    )
                )
                logger.info(f"Google Drive MCP: loaded {filename}")
            except Exception as exc:
                logger.error(
                    f"Google Drive MCP: failed to process {filename}: {exc}",
                    exc_info=True,
                )

        logger.info(
            f"Google Drive MCP: fetched {len(documents)} documents "
            f"from folder {settings.GOOGLE_DRIVE_FOLDER_ID}"
        )
        return documents

    def _build_drive_service(self):
        """Build an authenticated Google Drive API service."""
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            settings.GOOGLE_DRIVE_CREDENTIALS_JSON,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    def _list_pdf_files(self, service) -> list[dict]:
        """List all PDF files in the configured folder."""
        query = (
            f"'{settings.GOOGLE_DRIVE_FOLDER_ID}' in parents "
            f"and mimeType='application/pdf' "
            f"and trashed=false"
        )
        response = (
            service.files()
            .list(q=query, fields="files(id, name)", pageSize=100)
            .execute()
        )
        return response.get("files", [])

    def _download_file(self, service, file_id: str) -> bytes:
        """Download a file by ID and return raw bytes."""
        from googleapiclient.http import MediaIoBaseDownload

        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buffer.getvalue()

    def _infer_type(self, filename: str) -> str:
        lower = filename.lower()
        if "policy" in lower or "pol" in lower:
            return "policy"
        if "regulation" in lower or "reg" in lower:
            return "regulation"
        return "general"
