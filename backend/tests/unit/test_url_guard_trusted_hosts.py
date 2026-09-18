"""受信内部主机（MinIO）SSRF 放行回归。

背景：process_stored_file 下载服务端生成的 MinIO presigned URL，dev 环境
指向 127.0.0.1/localhost，被通用 SSRF 守卫误拦（SSRFBlocked: blocked
localhost target）导致文件处理永久 retry。守卫默认行为必须保持严格。
"""

import ipaddress

import pytest

from app.services.openclaw import url_guard


def _resolver_static(ip: str):
    def _resolve(hostname: str):
        return [ipaddress.ip_address(ip)]

    return _resolve


TRUSTED = frozenset({"localhost", "minio.internal"})


class TestTrustedHostExemption:
    def test_trusted_localhost_passes(self):
        url = "http://localhost:9000/bucket/key?X-Amz-Signature=abc"
        assert (
            url_guard.validate_external_url(url, resolver=_resolver_static("127.0.0.1"), trusted_hosts=TRUSTED)
            == url
        )

    def test_trusted_named_host_with_private_ip_passes(self):
        url = "http://minio.internal:9000/bucket/key"
        assert (
            url_guard.validate_external_url(url, resolver=_resolver_static("10.0.0.5"), trusted_hosts=TRUSTED)
            == url
        )

    def test_untrusted_localhost_still_blocked(self):
        with pytest.raises(url_guard.SSRFBlocked, match="blocked localhost target"):
            url_guard.validate_external_url(
                "http://localhost:9000/x", resolver=_resolver_static("127.0.0.1")
            )

    def test_untrusted_private_ip_still_blocked(self):
        with pytest.raises(url_guard.SSRFBlocked, match="blocked outbound target"):
            url_guard.validate_external_url(
                "http://evil.internal:9000/x",
                resolver=_resolver_static("10.0.0.5"),
                trusted_hosts=TRUSTED,
            )

    def test_scheme_check_not_bypassed_for_trusted_host(self):
        with pytest.raises(url_guard.SSRFBlocked, match="blocked URL scheme"):
            url_guard.validate_external_url(
                "file://localhost/etc/passwd", resolver=_resolver_static("127.0.0.1"), trusted_hosts=TRUSTED
            )

    def test_network_backend_connect_allows_trusted_host(self):
        backend = url_guard.SSRFGuardedNetworkBackend(
            resolver=_resolver_static("127.0.0.1"), trusted_hosts=TRUSTED
        )
        assert backend._safe_connect_hosts("localhost") == ["localhost"]

    def test_network_backend_connect_blocks_untrusted_localhost(self):
        backend = url_guard.SSRFGuardedNetworkBackend(resolver=_resolver_static("127.0.0.1"))
        with pytest.raises(url_guard.SSRFBlocked, match="blocked localhost target"):
            backend._safe_connect_hosts("localhost")

    def test_settings_minio_endpoint_parses_to_hosts(self):
        hosts = url_guard._trusted_hosts_from_settings()
        raw = getattr(url_guard.settings, "MINIO_ENDPOINT", "") or ""
        expected = {part.split(":", 1)[0].strip().lower() for part in raw.split(",") if part.strip()}
        assert hosts == frozenset(expected)
