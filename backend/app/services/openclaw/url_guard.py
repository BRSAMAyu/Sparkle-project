from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import settings

ALLOWED_SCHEMES = {"http", "https"}
BLOCKED_SCHEMES = {"file", "gopher", "dict", "ftp"}
METADATA_IPS = {"169.254.169.254"}
DEFAULT_OUTBOUND_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=5.0)
MAX_REDIRECTS = 5
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


class SSRFBlocked(ValueError):
    """Raised when an outbound URL resolves to a blocked target."""


class DownloadTooLargeError(ValueError):
    """Raised when a streamed download exceeds the configured byte ceiling."""


def _default_max_download_bytes() -> int:
    raw_value = int(getattr(settings, "OPENCLAW_MAX_DOWNLOAD_BYTES", 10 * 1024 * 1024) or 10 * 1024 * 1024)
    return max(1, raw_value)


def _resolve_host_ips(hostname: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    # ip_address() 恒返 IPv4/IPv6 具体类型；_BaseAddress 上没有 is_private 等
    # 判别属性（它们定义在两个具体类上），收窄到联合具体类型。
    resolved: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for family, _socktype, _proto, _canonname, sockaddr in socket.getaddrinfo(hostname, None):
        host = sockaddr[0]
        address = ipaddress.ip_address(host)
        if address not in resolved:
            resolved.append(address)
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
    return resolved


def _trusted_hosts_from_settings() -> frozenset[str]:
    """Internal infrastructure hosts (e.g. MinIO) exempt from private/loopback blocking.

    The file-processing pipeline downloads from presigned MinIO URLs that legitimately
    resolve to loopback/private addresses in dev; these URLs are server-generated, not
    user input, so the SSRF check does not apply to them.
    """
    raw = str(getattr(settings, "MINIO_ENDPOINT", "") or "")
    hosts = {part.split(":", 1)[0].strip().lower() for part in raw.split(",") if part.strip()}
    return frozenset(h for h in hosts if h)


def _is_trusted_host(hostname: str | None, trusted_hosts: frozenset[str] | None) -> bool:
    if not hostname or not trusted_hosts:
        return False
    return hostname.strip().lower() in trusted_hosts


def _is_blocked_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        str(address) in METADATA_IPS
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def _validate_resolved_addresses(
    hostname: str,
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address],
    trusted_hosts: frozenset[str] | None = None,
) -> None:
    if _is_trusted_host(hostname, trusted_hosts):
        return
    if not addresses:
        raise SSRFBlocked("unable to resolve target hostname")
    for address in addresses:
        if _is_blocked_ip(address):
            raise SSRFBlocked(f"blocked outbound target: {address}")


def validate_external_url(
    url: str,
    *,
    resolver=_resolve_host_ips,
    trusted_hosts: frozenset[str] | None = None,
) -> str:
    parsed = urlparse(str(url or "").strip())
    scheme = parsed.scheme.lower()
    if scheme in BLOCKED_SCHEMES or scheme not in ALLOWED_SCHEMES:
        raise SSRFBlocked(f"blocked URL scheme: {scheme or '<missing>'}")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlocked("missing URL hostname")
    if hostname.lower() == "localhost" and not _is_trusted_host(hostname, trusted_hosts):
        raise SSRFBlocked("blocked localhost target")

    addresses = list(resolver(hostname))
    _validate_resolved_addresses(hostname, addresses, trusted_hosts=trusted_hosts)
    return url


class SSRFGuardedNetworkBackend:
    """httpcore network backend that resolves and validates hosts at connect time."""

    def __init__(self, *, resolver=_resolve_host_ips, trusted_hosts: frozenset[str] | None = None):
        from httpcore._backends.auto import AutoBackend

        self._resolver = resolver
        self._trusted_hosts = trusted_hosts
        self._backend = AutoBackend()

    def _safe_connect_hosts(self, host: str | bytes) -> list[str]:
        hostname = host.decode("ascii") if isinstance(host, bytes) else str(host)
        if hostname.lower() == "localhost" and not _is_trusted_host(hostname, self._trusted_hosts):
            raise SSRFBlocked("blocked localhost target")

        if not _is_trusted_host(hostname, self._trusted_hosts):
            try:
                literal_address = ipaddress.ip_address(hostname)
            except ValueError:
                addresses = list(self._resolver(hostname))
            else:
                addresses = [literal_address]

            _validate_resolved_addresses(hostname, addresses)
            return [str(address) for address in addresses]

        try:
            literal = ipaddress.ip_address(hostname)
            return [str(literal)]
        except ValueError:
            return [hostname]

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ):
        last_error: Exception | None = None
        for connect_host in self._safe_connect_hosts(host):
            try:
                return await self._backend.connect_tcp(
                    connect_host,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise SSRFBlocked("unable to resolve target hostname")

    async def connect_unix_socket(self, path: str, timeout: float | None = None, socket_options=None):
        raise SSRFBlocked("unix socket connections are not allowed for outbound downloads")

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)


class SSRFGuardedAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """HTTP transport that validates DNS again immediately before TCP connect."""

    def __init__(self, *, resolver=_resolve_host_ips, trusted_hosts: frozenset[str] | None = None) -> None:
        import httpcore
        from httpx._config import DEFAULT_LIMITS, create_ssl_context

        ssl_context = create_ssl_context(verify=True, cert=None, trust_env=True)
        limits = DEFAULT_LIMITS
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_context,
            max_connections=limits.max_connections,
            max_keepalive_connections=limits.max_keepalive_connections,
            keepalive_expiry=limits.keepalive_expiry,
            http1=True,
            http2=False,
            retries=0,
            network_backend=SSRFGuardedNetworkBackend(resolver=resolver, trusted_hosts=trusted_hosts),
        )


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
    trusted_hosts: frozenset[str] | None = None,
) -> str:
    safe_url = validate_external_url(download_url, resolver=resolver, trusted_hosts=trusted_hosts)
    limit = max_bytes or _default_max_download_bytes()
    destination = Path(destination_path)

    transport = SSRFGuardedAsyncHTTPTransport(resolver=resolver, trusted_hosts=trusted_hosts)
    async with client_factory(
        timeout=DEFAULT_OUTBOUND_TIMEOUT,
        follow_redirects=False,
        transport=transport,
    ) as client:
        current_url = safe_url
        for _redirect_count in range(MAX_REDIRECTS + 1):
            current_url = validate_external_url(current_url, resolver=resolver, trusted_hosts=trusted_hosts)
            async with client.stream("GET", current_url) as response:
                if response.status_code in REDIRECT_STATUS_CODES:
                    location = response.headers.get("Location")
                    if not location:
                        raise SSRFBlocked("redirect response missing Location header")
                    current_url = str(httpx.URL(current_url).join(location))
                    continue

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

        raise SSRFBlocked("too many redirects while validating outbound download")
