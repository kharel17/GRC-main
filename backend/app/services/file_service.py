"""
File Storage Service — Abstracted interface for local and S3 storage.

Usage:
    from app.services.file_service import file_storage
    url = await file_storage.upload(file_bytes, filename, content_type)
    signed_url = await file_storage.get_download_url(file_key)
    await file_storage.delete(file_key)
"""
import os
import uuid
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger("grc.file_storage")


class FileStorageBackend(ABC):
    """Abstract base class for file storage."""

    @abstractmethod
    async def upload(self, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
        """Upload a file and return the storage key/path."""
        ...

    @abstractmethod
    async def get_download_url(self, file_key: str) -> str:
        """Return a URL (or path) to download the file."""
        ...

    @abstractmethod
    async def delete(self, file_key: str) -> bool:
        """Delete a file by its key. Returns True if successful."""
        ...


class LocalStorageBackend(FileStorageBackend):
    """Stores files on the local filesystem (Docker volume in production)."""

    def __init__(self, upload_dir: str):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
        # Generate a unique key to avoid collisions
        ext = Path(filename).suffix
        file_key = f"{uuid.uuid4().hex}{ext}"
        file_path = self.upload_dir / file_key

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        logger.info(f"File uploaded locally: {file_key} ({len(file_bytes)} bytes)")
        return file_key

    async def get_download_url(self, file_key: str) -> str:
        # For local storage, return a relative API path
        return f"/api/v1/files/{file_key}"

    async def delete(self, file_key: str) -> bool:
        file_path = self.upload_dir / file_key
        if file_path.exists():
            file_path.unlink()
            logger.info(f"File deleted locally: {file_key}")
            return True
        logger.warning(f"File not found for deletion: {file_key}")
        return False


class S3StorageBackend(FileStorageBackend):
    """Stores files in AWS S3 with presigned URLs for downloads."""

    def __init__(self):
        try:
            import boto3
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
            self.bucket = settings.S3_BUCKET_NAME
            self.expiry = settings.S3_PRESIGNED_URL_EXPIRY
            logger.info(f"S3 storage initialized: bucket={self.bucket}")
        except ImportError:
            raise RuntimeError("boto3 is required for S3 storage. Install it with: pip install boto3")

    async def upload(self, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
        ext = Path(filename).suffix
        file_key = f"evidence/{uuid.uuid4().hex}{ext}"

        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=file_key,
            Body=file_bytes,
            ContentType=content_type,
        )
        logger.info(f"File uploaded to S3: {file_key} ({len(file_bytes)} bytes)")
        return file_key

    async def get_download_url(self, file_key: str) -> str:
        url = self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": file_key},
            ExpiresIn=self.expiry,
        )
        return url

    async def delete(self, file_key: str) -> bool:
        self.s3_client.delete_object(Bucket=self.bucket, Key=file_key)
        logger.info(f"File deleted from S3: {file_key}")
        return True


class SupabaseStorageBackend(FileStorageBackend):
    """Stores files in Supabase Storage."""

    def __init__(self):
        self.url = f"{settings.SUPABASE_URL}/storage/v1"
        self.key = settings.SUPABASE_SERVICE_KEY
        self.bucket = settings.SUPABASE_BUCKET_NAME
        self.headers = {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
        }
        logger.info(f"Supabase storage initialized: bucket={self.bucket}")

    async def upload(self, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream") -> str:
        import httpx
        ext = Path(filename).suffix
        file_key = f"{uuid.uuid4().hex}{ext}"
        
        upload_url = f"{self.url}/object/{self.bucket}/{file_key}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                upload_url,
                content=file_bytes,
                headers={**self.headers, "Content-Type": content_type}
            )
            if resp.status_code != 200:
                logger.error(f"Supabase upload failed: {resp.status_code} {resp.text}")
                raise RuntimeError(f"Supabase upload failed: {resp.text}")

        logger.info(f"File uploaded to Supabase: {file_key} ({len(file_bytes)} bytes)")
        return file_key

    async def get_download_url(self, file_key: str) -> str:
        # Supabase allows public URLs or signed URLs. 
        # For now, we return the public URL if the bucket is public, or a signed one.
        # This implementation returns the public URL format.
        return f"{self.url}/object/public/{self.bucket}/{file_key}"

    async def delete(self, file_key: str) -> bool:
        import httpx
        delete_url = f"{self.url}/object/{self.bucket}"
        
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                "DELETE",
                delete_url,
                json={"prefixes": [file_key]},
                headers=self.headers
            )
            if resp.status_code != 200:
                logger.error(f"Supabase delete failed: {resp.status_code} {resp.text}")
                return False
        
        logger.info(f"File deleted from Supabase: {file_key}")
        return True


def _create_storage() -> FileStorageBackend:
    """Factory that returns the configured storage backend."""
    if settings.FILE_STORAGE_BACKEND == "s3":
        return S3StorageBackend()
    if settings.FILE_STORAGE_BACKEND == "supabase":
        return SupabaseStorageBackend()
    return LocalStorageBackend(settings.UPLOAD_DIR)


# Singleton instance
file_storage = _create_storage()
