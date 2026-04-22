from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import httpx

from app.config import settings

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_SCHEMES = {"file", "gopher", "dict", "ftp"}
METADATA_IPS = {"169.254.169.254"}
DEFAULT_OUTBOUND_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)


class SSRFBlocked(ValueError):
    """Raised when an outbound URL resolves to a blocked target."""


class DownloadTooLargeError(ValueError):
    """Raised when a streamed download exceeds the configured byte ceiling."""


def _default_max_download_bytes() -> int:
    raw_value = int(getattr(settings, "OPENCLAW_MAX_DOWNLOAD_BYTES", 10 * 1024 * 1024) or 10 * 1024 * 1024)
    return max(1, raw_value)


def _resolve_host_ips(hostname: str) -> list[ipaddress._BaseAddress]:
    resolved: list[ipaddress._BaseAddress] = []
    for family, _socktype, _proto, _canonname, sockaddr in socket.getaddrinfo(hostname, None):
        host = sockaddr[0]
        address = ipaddress.ip_address(host)
        if address not in resolved:
            resolved.append(address)
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
    return resolved


def _is_blocked_ip(address: ipaddress._BaseAddress) -> bool:
    return (
        str(address) in METADATA_IPS
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def validate_external_url(
    url: str,
    *,
    resolver=_resolve_host_ips,
) -> str:
    parsed = urlparse(str(url or "").strip())
    scheme = parsed.scheme.lower()
    if scheme in BLOCKED_SCHEMES or scheme not in ALLOWED_SCHEMES:
        raise SSRFBlocked(f"blocked URL scheme: {scheme or '<missing>'}")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlocked("missing URL hostname")
    if hostname.lower() == "localhost":
        raise SSRFBlocked("blocked localhost target")

    addresses = list(resolver(hostname))
    if not addresses:
        raise SSRFBlocked("unable to resolve target hostname")
    for address in addresses:
        if _is_blocked_ip(address):
            raise SSRFBlocked(f"blocked outbound target: {address}")
    return url


def validate_content_length(headers: httpx.Headers | dict[str, str], *, max_bytes: int) -> None:
    raw_length = headers.get("Content-Length")
    if raw_length is None:
        return
    try:
        content_length = int(raw_length)
    except (TypeError, ValueError) as exc:
        raise DownloadTooLargeError("invalid Content-Length header") from exc
    if content_length > max_bytes:
        raise DownloadTooLargeError(f"download exceeds limit ({content_length} > {max_bytes})")


async def stream_download_to_path(
    download_url: str,
    destination_path: str | Path,
    *,
    max_bytes: int | None = None,
    resolver=_resolve_host_ips,
    client_factory=httpx.AsyncClient,
) -> str:
    safe_url = validate_external_url(download_url, resolver=resolver)
    limit = max_bytes or _default_max_download_bytes()
    destination = Path(destination_path)

    async with client_factory(timeout=DEFAULT_OUTBOUND_TIMEOUT, follow_redirects=True) as client:
        async with client.stream("GET", safe_url) as response:
            response.raise_for_status()
            validate_content_length(response.headers, max_bytes=limit)

            written = 0
            with destination.open("wb") as outfile:
                async for chunk in response.aiter_bytes():
                    written += len(chunk)
                    if written > limit:
                        raise DownloadTooLargeError(f"download exceeds limit ({written} > {limit})")
                    outfile.write(chunk)

    return str(destination)
