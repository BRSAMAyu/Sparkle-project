from __future__ import annotations

import ipaddress
from pathlib import Path

import httpx
import pytest

from app.models.execution_schedule import ExecutionScheduleTriggerType
from app.services.execution_schedule_service import ExecutionScheduleService
from app.services.openclaw.url_guard import DownloadTooLargeError, SSRFBlocked, stream_download_to_path, validate_external_url


class _FakeStreamResponse:
    def __init__(self, *, status_code: int = 200, headers: dict[str, str] | None = None, chunks: list[bytes] | None = None):
        self.status_code = status_code
        self.headers = httpx.Headers(headers or {})
        self._chunks = list(chunks or [])
        self.request = httpx.Request("GET", "https://example.com/resource")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("request failed", request=self.request, response=httpx.Response(self.status_code))

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


class _FakeAsyncClient:
    def __init__(self, *, response: _FakeStreamResponse | None = None, text: str = "", status_code: int = 200, **kwargs):
        del kwargs
        self._response = response
        self._text = text
        self._status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, method: str, url: str):
        del method, url
        if self._response is None:
            raise AssertionError("stream() called without a fake response")
        return self._response

    async def get(self, url: str):
        request = httpx.Request("GET", url)
        return httpx.Response(self._status_code, request=request, text=self._text)


def _public_resolver(_hostname: str):
    return [ipaddress.ip_address("93.184.216.34")]


@pytest.mark.parametrize(
    "url",
    [
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.1/internal",
        "http://localhost/admin",
    ],
)
def test_openclaw_url_guard_blocks_private_targets(url: str):
    with pytest.raises(SSRFBlocked):
        validate_external_url(url, resolver=lambda _hostname: [ipaddress.ip_address(url.split("/")[2].split(":")[0])] if "localhost" not in url else [ipaddress.ip_address("127.0.0.1")])


def test_openclaw_url_guard_blocks_file_scheme():
    with pytest.raises(SSRFBlocked):
        validate_external_url("file:///etc/passwd", resolver=_public_resolver)


@pytest.mark.asyncio
async def test_stream_download_blocks_oversized_payload(tmp_path: Path):
    fake_client = lambda **kwargs: _FakeAsyncClient(  # noqa: E731
        response=_FakeStreamResponse(chunks=[b"a" * (6 * 1024 * 1024), b"b" * (6 * 1024 * 1024)]),
        **kwargs,
    )

    with pytest.raises(DownloadTooLargeError):
        await stream_download_to_path(
            "https://example.com/big.bin",
            tmp_path / "big.bin",
            max_bytes=10 * 1024 * 1024,
            resolver=_public_resolver,
            client_factory=fake_client,
        )


@pytest.mark.asyncio
async def test_execution_schedule_allows_safe_public_check_url(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.execution_schedule_service.validate_external_url",
        lambda url: validate_external_url(url, resolver=_public_resolver),
    )
    monkeypatch.setattr(
        "app.services.execution_schedule_service.httpx.AsyncClient",
        lambda **kwargs: _FakeAsyncClient(text="service ready", status_code=200, **kwargs),
    )

    service = ExecutionScheduleService(db_session)

    matched = await service._condition_matches(
        {
            "check_url": "https://example.com/health",
            "condition": "contains('ready')",
        }
    )

    assert matched is True
