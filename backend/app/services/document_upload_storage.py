"""
S3/MinIO helpers for user document uploads.
"""
from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from urllib.parse import urlparse

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings


def _endpoint_url(raw_endpoint: str, *, use_ssl: bool) -> str:
    endpoint = (raw_endpoint or "").strip()
    if not endpoint:
        endpoint = "localhost:9000"
    if "://" not in endpoint:
        scheme = "https" if use_ssl else "http"
        endpoint = f"{scheme}://{endpoint}"
    return endpoint


def _default_public_endpoint() -> str:
    if settings.MINIO_PUBLIC_ENDPOINT:
        return settings.MINIO_PUBLIC_ENDPOINT
    parsed = urlparse(_endpoint_url(settings.MINIO_ENDPOINT, use_ssl=settings.MINIO_USE_SSL))
    if parsed.hostname == "minio":
        scheme = "https" if settings.MINIO_USE_SSL else "http"
        return f"{scheme}://localhost:{parsed.port or 9000}"
    return settings.MINIO_ENDPOINT


def _client(endpoint: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name=settings.MINIO_REGION or "us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


@lru_cache(maxsize=1)
def _internal_client():
    return _client(_endpoint_url(settings.MINIO_ENDPOINT, use_ssl=settings.MINIO_USE_SSL))


@lru_cache(maxsize=1)
def _presign_client():
    return _client(_endpoint_url(_default_public_endpoint(), use_ssl=settings.MINIO_USE_SSL))


class DocumentUploadStorage:
    """Thin synchronous wrapper around boto3 for presigning and upload validation."""

    @property
    def bucket(self) -> str:
        return settings.MINIO_BUCKET

    @property
    def expires_in(self) -> int:
        return max(60, int(settings.FILE_PRESIGN_EXPIRES_SECONDS or 420))

    def create_presigned_put_url(self, *, object_key: str, mime_type: str, file_size: int) -> str:
        return _presign_client().generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=self.expires_in,
            HttpMethod="PUT",
        )

    def create_presigned_get_url(self, *, object_key: str) -> str:
        return _presign_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key},
            ExpiresIn=self.expires_in,
            HttpMethod="GET",
        )

    def copy_object(self, *, source_object_key: str, destination_object_key: str) -> None:
        _internal_client().copy_object(
            Bucket=self.bucket,
            Key=destination_object_key,
            CopySource={"Bucket": self.bucket, "Key": source_object_key},
        )

    def delete_object(self, *, object_key: str) -> None:
        _internal_client().delete_object(Bucket=self.bucket, Key=object_key)

    def head_object(self, *, object_key: str) -> dict:
        return _internal_client().head_object(Bucket=self.bucket, Key=object_key)

    def read_header(self, *, object_key: str, max_bytes: int = 512) -> bytes:
        response = _internal_client().get_object(
            Bucket=self.bucket,
            Key=object_key,
            Range=f"bytes=0-{max(0, max_bytes - 1)}",
        )
        body = response["Body"]
        try:
            return body.read(max_bytes)
        finally:
            body.close()

    def object_exists(self, *, object_key: str) -> bool:
        try:
            self.head_object(object_key=object_key)
            return True
        except ClientError as exc:
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status_code == 404:
                return False
            raise

    def object_last_modified(self, *, object_key: str) -> datetime | None:
        try:
            modified = self.head_object(object_key=object_key).get("LastModified")
        except ClientError:
            return None
        if not isinstance(modified, datetime):
            return None
        if modified.tzinfo is None:
            return modified.replace(tzinfo=UTC)
        return modified


def is_public_endpoint_configured() -> bool:
    public_endpoint = (settings.MINIO_PUBLIC_ENDPOINT or "").strip()
    if not public_endpoint:
        return False
    parsed = urlparse(_endpoint_url(public_endpoint, use_ssl=settings.MINIO_USE_SSL))
    return bool(parsed.scheme and parsed.netloc)


document_upload_storage = DocumentUploadStorage()
