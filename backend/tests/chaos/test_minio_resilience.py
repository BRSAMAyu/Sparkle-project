"""
MinIO / document storage resilience tests.

Covers OBS-020 chaos scenarios:
- Complete MinIO outage (all operations fail)
- Slow MinIO responses (high latency)
- Intermittent failures (some requests fail)
- Authentication failures (invalid credentials)
- Bucket not found (wrong bucket name)
- Recovery after MinIO restart

Pattern: unit-level tests with mocked S3 clients (no live MinIO needed).
"""
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

_MOD = "app.services.document_upload_storage"


# ── Fake S3 clients simulating failure modes ─────────────────────


class _FailingS3Client:
    """Simulates a MinIO that throws on every operation."""

    def generate_presigned_url(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "ConnectionRefused", "Message": "connection refused"}},
            "generate_presigned_url",
        )

    def copy_object(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "ConnectionRefused", "Message": "connection refused"}},
            "copy_object",
        )

    def delete_object(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "ConnectionRefused", "Message": "connection refused"}},
            "delete_object",
        )

    def head_object(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "ConnectionRefused", "Message": "connection refused"}},
            "head_object",
        )

    def get_object(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "ConnectionRefused", "Message": "connection refused"}},
            "get_object",
        )


class _SlowS3Client:
    """Simulates a slow MinIO by injecting latency into every call."""

    latency: float = 0.1

    def generate_presigned_url(self, *a, **kw):
        time.sleep(self.latency)
        return "https://minio.local/sparkle-files/test-key?presigned=true"

    def copy_object(self, *a, **kw):
        time.sleep(self.latency)

    def delete_object(self, *a, **kw):
        time.sleep(self.latency)

    def head_object(self, *a, **kw):
        time.sleep(self.latency)
        return {"LastModified": datetime.now(UTC), "ContentLength": 1024}

    def get_object(self, *a, **kw):
        time.sleep(self.latency)
        body = MagicMock()
        body.read.return_value = b"x" * 512
        body.close.return_value = None
        return {"Body": body}


class _IntermittentS3Client:
    """Fails every Nth call to simulate intermittent MinIO issues."""

    def __init__(self, fail_every: int = 3):
        self._count = 0
        self._fail_every = fail_every

    def _maybe_fail(self, operation: str):
        self._count += 1
        if self._count % self._fail_every == 0:
            raise ClientError(
                {"Error": {"Code": "ServiceUnavailable", "Message": "slow down"}},
                operation,
            )

    def generate_presigned_url(self, *a, **kw):
        self._maybe_fail("generate_presigned_url")
        return "https://minio.local/sparkle-files/test-key?presigned=true"

    def copy_object(self, *a, **kw):
        self._maybe_fail("copy_object")

    def delete_object(self, *a, **kw):
        self._maybe_fail("delete_object")

    def head_object(self, *a, **kw):
        self._maybe_fail("head_object")
        return {"LastModified": datetime.now(UTC), "ContentLength": 1024}

    def get_object(self, *a, **kw):
        self._maybe_fail("get_object")
        body = MagicMock()
        body.read.return_value = b"x" * 512
        body.close.return_value = None
        return {"Body": body}


class _AuthFailS3Client:
    """Simulates invalid credentials / access denied."""

    def generate_presigned_url(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "InvalidAccessKeyId", "Message": "access denied"}},
            "generate_presigned_url",
        )

    def copy_object(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "access denied"}},
            "copy_object",
        )

    def delete_object(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "access denied"}},
            "delete_object",
        )

    def head_object(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "access denied"}},
            "head_object",
        )

    def get_object(self, *a, **kw):
        raise ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "access denied"}},
            "get_object",
        )


class _NotFoundS3Client:
    """Simulates bucket/object not found (404)."""

    def generate_presigned_url(self, *a, **kw):
        return "https://minio.local/sparkle-files/test-key?presigned=true"

    def copy_object(self, *a, **kw):
        raise ClientError(
            {
                "Error": {"Code": "NoSuchKey", "Message": "not found"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            },
            "copy_object",
        )

    def delete_object(self, *a, **kw):
        pass

    def head_object(self, *a, **kw):
        raise ClientError(
            {
                "Error": {"Code": "404", "Message": "Not Found"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            },
            "head_object",
        )

    def get_object(self, *a, **kw):
        raise ClientError(
            {
                "Error": {"Code": "NoSuchKey", "Message": "not found"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            },
            "get_object",
        )


def _patched_storage(client):
    """Return a context manager that patches both S3 client factories and yields a DocumentUploadStorage."""
    from app.services.document_upload_storage import DocumentUploadStorage

    return _patched_storage_inner(client, DocumentUploadStorage)


@contextmanager
def _patched_storage_inner(client, cls):
    with patch(f"{_MOD}._internal_client", return_value=client), \
         patch(f"{_MOD}._presign_client", return_value=client):
        yield cls()


# ── Tests: Complete Outage ───────────────────────────────────────


class TestMinIOCompleteOutage:
    """All MinIO operations fail — system must not crash."""

    def test_presigned_put_url_raises_connection_error(self):
        with _patched_storage(_FailingS3Client()) as storage:
            with pytest.raises(ClientError) as exc_info:
                storage.create_presigned_put_url(
                    object_key="test.pdf", mime_type="application/pdf", file_size=1024,
                )
            assert exc_info.value.response["Error"]["Code"] == "ConnectionRefused"

    def test_presigned_get_url_raises_connection_error(self):
        with _patched_storage(_FailingS3Client()) as storage:
            with pytest.raises(ClientError) as exc_info:
                storage.create_presigned_get_url(object_key="test.pdf")
            assert exc_info.value.response["Error"]["Code"] == "ConnectionRefused"

    def test_copy_object_raises_connection_error(self):
        with _patched_storage(_FailingS3Client()) as storage:
            with pytest.raises(ClientError):
                storage.copy_object(source_object_key="a.pdf", destination_object_key="b.pdf")

    def test_delete_object_raises_connection_error(self):
        with _patched_storage(_FailingS3Client()) as storage:
            with pytest.raises(ClientError):
                storage.delete_object(object_key="test.pdf")

    def test_object_exists_raises_on_connection_error(self):
        with _patched_storage(_FailingS3Client()) as storage:
            with pytest.raises(ClientError):
                storage.object_exists(object_key="test.pdf")

    def test_object_last_modified_returns_none_on_connection_error(self):
        with _patched_storage(_FailingS3Client()) as storage:
            result = storage.object_last_modified(object_key="test.pdf")
            assert result is None


# ── Tests: Slow MinIO ────────────────────────────────────────────


class TestMinIOSlowResponse:
    """MinIO is slow — verify latency propagation."""

    def test_head_object_latency_propagates(self):
        client = _SlowS3Client()
        client.latency = 0.1
        with _patched_storage(client) as storage:
            start = time.monotonic()
            result = storage.head_object(object_key="test.pdf")
            elapsed = time.monotonic() - start
            assert elapsed >= 0.09
            assert "LastModified" in result

    def test_read_header_latency_propagates(self):
        client = _SlowS3Client()
        client.latency = 0.1
        with _patched_storage(client) as storage:
            start = time.monotonic()
            data = storage.read_header(object_key="test.pdf", max_bytes=128)
            elapsed = time.monotonic() - start
            assert elapsed >= 0.09
            assert len(data) > 0


# ── Tests: Intermittent Failures ─────────────────────────────────


class TestMinIOIntermittentFailure:
    """Some requests fail — verify retry/fallback behavior."""

    def test_presigned_url_succeeds_despite_intermittent(self):
        client = _IntermittentS3Client(fail_every=3)
        with _patched_storage(client) as storage:
            successes = 0
            for i in range(4):
                if i == 2:
                    with pytest.raises(ClientError):
                        storage.create_presigned_put_url(
                            object_key="test.pdf", mime_type="application/pdf", file_size=1024,
                        )
                else:
                    url = storage.create_presigned_put_url(
                        object_key="test.pdf", mime_type="application/pdf", file_size=1024,
                    )
                    assert "presigned=true" in url
                    successes += 1
            assert successes == 3

    def test_object_exists_handles_404_gracefully(self):
        with _patched_storage(_NotFoundS3Client()) as storage:
            assert storage.object_exists(object_key="missing.pdf") is False


# ── Tests: Auth Failure ──────────────────────────────────────────


class TestMinIOAuthFailure:
    """Invalid credentials — verify ClientError with correct code."""

    def test_presigned_put_raises_access_denied(self):
        with _patched_storage(_AuthFailS3Client()) as storage:
            with pytest.raises(ClientError) as exc_info:
                storage.create_presigned_put_url(
                    object_key="test.pdf", mime_type="application/pdf", file_size=1024,
                )
            assert exc_info.value.response["Error"]["Code"] == "InvalidAccessKeyId"

    def test_delete_raises_access_denied(self):
        with _patched_storage(_AuthFailS3Client()) as storage:
            with pytest.raises(ClientError) as exc_info:
                storage.delete_object(object_key="test.pdf")
            assert exc_info.value.response["Error"]["Code"] == "AccessDenied"

    def test_object_last_modified_returns_none_on_auth_error(self):
        with _patched_storage(_AuthFailS3Client()) as storage:
            result = storage.object_last_modified(object_key="test.pdf")
            assert result is None


# ── Tests: Bucket / Object Not Found ─────────────────────────────


class TestMinIONotFound:
    """Objects or buckets don't exist — graceful 404 handling."""

    def test_object_exists_returns_false_for_missing(self):
        with _patched_storage(_NotFoundS3Client()) as storage:
            assert storage.object_exists(object_key="nonexistent.pdf") is False

    def test_copy_object_raises_no_such_key(self):
        with _patched_storage(_NotFoundS3Client()) as storage:
            with pytest.raises(ClientError) as exc_info:
                storage.copy_object(source_object_key="old.pdf", destination_object_key="new.pdf")
            assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    def test_read_header_raises_not_found(self):
        with _patched_storage(_NotFoundS3Client()) as storage:
            with pytest.raises(ClientError) as exc_info:
                storage.read_header(object_key="missing.pdf")
            assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"

    def test_delete_object_succeeds_for_missing(self):
        with _patched_storage(_NotFoundS3Client()) as storage:
            storage.delete_object(object_key="missing.pdf")


# ── Tests: Recovery After Outage ─────────────────────────────────


class TestMinIORecovery:
    """Verify system works normally after MinIO comes back online."""

    def test_operations_succeed_after_recovery(self):
        healthy_client = MagicMock()
        healthy_client.generate_presigned_url.return_value = "https://minio.local/fake?sig=abc"
        healthy_client.head_object.return_value = {
            "LastModified": datetime.now(UTC),
            "ContentLength": 2048,
        }

        with _patched_storage(_FailingS3Client()) as storage:
            with pytest.raises(ClientError):
                storage.create_presigned_put_url(
                    object_key="test.pdf", mime_type="application/pdf", file_size=1024,
                )

        with _patched_storage(healthy_client) as storage:
            url = storage.create_presigned_put_url(
                object_key="test.pdf", mime_type="application/pdf", file_size=1024,
            )
            assert "sig=abc" in url

            head = storage.head_object(object_key="test.pdf")
            assert head["ContentLength"] == 2048
