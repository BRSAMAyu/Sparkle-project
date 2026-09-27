"""O-06 · 统一操作面 internal API 测试 —— /api/internal/ops（鉴权/可观测/翻转/回滚/清单）.

形制沿 tests/api/test_slo_auto_degrade_api.py：独立 FastAPI app + INTERNAL_API_KEY
打桩 + fakeredis 注入 cache_service.redis（monkeypatch，用后还原）。
"""

from __future__ import annotations

from unittest.mock import patch

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.internal.ops_release import router
from app.core import ops_surface
from app.core.cache import cache_service
from app.db.session import get_db

AUTH = {"X-Internal-API-Key": "test-internal-key-12345"}
_CAPABILITY_COUNT = len(ops_surface.CAPABILITY_SPECS)


@pytest.fixture
def fake_redis(monkeypatch):
    # decode_responses=True 与生产 cache_service 客户端同构（cache.py:73）。
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    # 哨兵用户态键：翻转/回滚全程必须逐字不变（验收「切换不丢用户 state」）。
    import asyncio

    asyncio.run(client.set(_SENTINEL_KEY, _SENTINEL_VALUE))
    monkeypatch.setattr(cache_service, "redis", client)
    yield client
    monkeypatch.setattr(cache_service, "redis", None)


_SENTINEL_KEY = "aurora:stage39:user:7:state"
_SENTINEL_VALUE = "payload"


@pytest.fixture
def app(fake_redis):
    _app = FastAPI()
    _app.include_router(router, prefix="/api/internal")
    _app.dependency_overrides[get_db] = lambda: None
    return _app


@pytest.fixture
def client(app):
    with patch("app.api.internal.ops_release.settings") as mock_settings:
        mock_settings.INTERNAL_API_KEY = "test-internal-key-12345"
        with TestClient(app) as tc:
            yield tc


# ---------------------------------------------------------------------------
# 鉴权（与 auto_degrade 同语义：未配置 500 / 缺席 401 / 不符 401）
# ---------------------------------------------------------------------------


class TestAuth:
    def test_missing_key_returns_401(self, client):
        assert client.get("/api/internal/ops/capabilities").status_code == 401

    def test_wrong_key_returns_401(self, client):
        resp = client.get("/api/internal/ops/capabilities", headers={"X-Internal-API-Key": "wrong"})
        assert resp.status_code == 401

    def test_valid_key_passes(self, client):
        resp = client.get("/api/internal/ops/capabilities", headers=AUTH)
        assert resp.status_code == 200

    def test_unconfigured_key_fails_closed_500(self, app, fake_redis):
        with patch("app.api.internal.ops_release.settings") as mock_settings:
            mock_settings.INTERNAL_API_KEY = ""
            with TestClient(app) as tc:
                resp = tc.get("/api/internal/ops/capabilities", headers=AUTH)
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# 可观测（flag 状态主读面）
# ---------------------------------------------------------------------------


class TestObservability:
    def test_list_capabilities_shape(self, client):
        resp = client.get("/api/internal/ops/capabilities", headers=AUTH)
        body = resp.json()
        assert body["count"] == _CAPABILITY_COUNT
        assert len(body["capabilities"]) == _CAPABILITY_COUNT
        assert body["runtime_mode_available"] is True
        entry = body["capabilities"][0]
        assert {
            "capability_id",
            "domain",
            "mode",
            "settings_mode",
            "runtime_mode_available",
            "stage",
            "feature",
            "settings_attr",
            "fallback_mode",
            "redis_key",
            "description",
        } <= set(entry)

    def test_list_capabilities_covers_all_domains(self, client):
        body = client.get("/api/internal/ops/capabilities", headers=AUTH).json()
        domains = {entry["domain"] for entry in body["capabilities"]}
        assert domains == {"aurora", "memory", "fme", "infra"}

    def test_get_capability_with_history(self, client):
        cid = "dual_core_router.mode"
        resp = client.get(f"/api/internal/ops/capabilities/{cid}", headers=AUTH)
        assert resp.status_code == 200
        body = resp.json()
        assert body["capability_id"] == cid
        assert body["rollback_history"] == []

    def test_get_unknown_capability_404(self, client):
        resp = client.get("/api/internal/ops/capabilities/no.such", headers=AUTH)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 受控翻转 + 回滚
# ---------------------------------------------------------------------------


class TestSetMode:
    def test_set_mode_roundtrip_with_rollback(self, client):
        cid = "dual_core_router.mode"
        baseline = client.get(f"/api/internal/ops/capabilities/{cid}", headers=AUTH).json()["mode"]

        resp = client.post(
            f"/api/internal/ops/capabilities/{cid}/mode",
            json={"mode": "shadow", "actor": "tester", "reason": "api smoke"},
            headers=AUTH,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["previous_mode"] == baseline
        assert body["mode"] == "shadow"

        detail = client.get(f"/api/internal/ops/capabilities/{cid}", headers=AUTH).json()
        assert detail["mode"] == "shadow"
        assert detail["rollback_history"][0]["to"] == "shadow"
        assert detail["rollback_history"][0]["reason"] == "api smoke"

        rb = client.post(f"/api/internal/ops/capabilities/{cid}/rollback", json={"actor": "tester"}, headers=AUTH)
        assert rb.status_code == 200
        assert rb.json()["mode"] == baseline

    def test_set_mode_unknown_capability_404(self, client):
        resp = client.post("/api/internal/ops/capabilities/no.such/mode", json={"mode": "shadow"}, headers=AUTH)
        assert resp.status_code == 404

    def test_set_mode_invalid_vocabulary_400(self, client):
        resp = client.post(
            "/api/internal/ops/capabilities/dual_core_router.mode/mode",
            json={"mode": "bogus"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_set_mode_redis_unavailable_503(self, app, monkeypatch):
        monkeypatch.setattr(cache_service, "redis", None)
        with patch("app.api.internal.ops_release.settings") as mock_settings:
            mock_settings.INTERNAL_API_KEY = "test-internal-key-12345"
            with TestClient(app) as tc:
                resp = tc.post(
                    "/api/internal/ops/capabilities/dual_core_router.mode/mode",
                    json={"mode": "shadow"},
                    headers=AUTH,
                )
        assert resp.status_code == 503

    def test_rollback_without_history_409(self, client):
        resp = client.post(
            "/api/internal/ops/capabilities/dual_core_router.mode/rollback",
            json={},
            headers=AUTH,
        )
        assert resp.status_code == 409

    def test_rollback_unknown_capability_404(self, client):
        resp = client.post("/api/internal/ops/capabilities/no.such/rollback", json={}, headers=AUTH)
        assert resp.status_code == 404

    def test_mode_switch_does_not_touch_user_state_keys(self, client, fake_redis):
        """验收：翻转/回滚不丢用户 state——哨兵用户键逐字不变."""
        import asyncio

        client.post("/api/internal/ops/capabilities/39.mode/mode", json={"mode": "shadow"}, headers=AUTH)
        client.post("/api/internal/ops/capabilities/39.mode/rollback", json={}, headers=AUTH)
        value = asyncio.run(fake_redis.get(_SENTINEL_KEY))
        assert value == _SENTINEL_VALUE


# ---------------------------------------------------------------------------
# release manifest
# ---------------------------------------------------------------------------


class TestReleaseManifest:
    def test_manifest_shape(self, client):
        resp = client.get("/api/internal/ops/release-manifest", headers=AUTH)
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {"manifest_version", "generated_at", "model", "config", "migration"}
        assert body["model"]["llm_model_name"]
        assert body["config"]["capability_mode_count"] == _CAPABILITY_COUNT

    def test_manifest_requires_auth(self, app, fake_redis):
        with patch("app.api.internal.ops_release.settings") as mock_settings:
            mock_settings.INTERNAL_API_KEY = "test-internal-key-12345"
            with TestClient(app) as tc:
                assert tc.get("/api/internal/ops/release-manifest").status_code == 401
