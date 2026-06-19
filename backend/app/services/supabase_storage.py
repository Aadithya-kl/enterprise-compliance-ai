import os
from supabase import create_client, Client
from app.core.config import settings
from app.core.logging import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = get_logger(__name__)

class SupabaseStorageService:
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            logger.warning("Supabase URL or Service Role Key missing. Storage operations will fail.")
            self.client: Client | None = None
        else:
            self.client: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    def is_configured(self) -> bool:
        return self.client is not None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def upload_file(self, file_path: str, storage_path: str) -> bool:
        """Upload a local file to Supabase Storage."""
        if not self.is_configured():
            logger.error("Supabase Storage not configured.")
            return False

        try:
            res = self.client.storage.from_(self.bucket).upload(
                path=storage_path,
                file=file_path,
                file_options={"content-type": "application/octet-stream", "upsert": "true"}
            )
            
            logger.info(f"Successfully uploaded to Supabase: {storage_path}")
            return True
        except Exception as exc:
            logger.error(f"Failed to upload {file_path} to Supabase storage_path={storage_path}: {exc}")
            raise

    def delete_file(self, storage_path: str) -> bool:
        """Delete a file from Supabase Storage."""
        if not self.is_configured():
            return False

        try:
            self.client.storage.from_(self.bucket).remove([storage_path])
            logger.info(f"Successfully deleted from Supabase: {storage_path}")
            return True
        except Exception as exc:
            logger.error(f"Failed to delete {storage_path} from Supabase: {exc}")
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def download_file(self, storage_path: str, local_path: str) -> bool:
        """Download a file from Supabase Storage to local disk."""
        if not self.is_configured():
            logger.error("Supabase Storage not configured.")
            return False

        try:
            with open(local_path, 'wb+') as f:
                res = self.client.storage.from_(self.bucket).download(storage_path)
                f.write(res)
            logger.info(f"Successfully downloaded from Supabase: {storage_path}")
            return True
        except Exception as exc:
            logger.error(f"Failed to download {storage_path} from Supabase: {exc}")
            return False

supabase_storage_service = SupabaseStorageService()
