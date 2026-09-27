"""
Tests for FV-24: SLO auto-degrade webhook + ClientDisconnectGuard.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.internal.auto_degrade import (
    ALERT_NAME_MAP,
    SLO_AUTO_DEGRADE_BINDINGS,
    AlertType,
    ClientDisconnectGuard,
    _write_audit,
    execute_auto_response,
    router,
)


@pytest.fixture
def app():
    """Create test app with the auto-degrade router."""
    _app = FastAPI()
    _app.include_router(router, prefix="/api/internal")
    return _app


@pytest.fixture
def client(app):
    """Create test client with INTERNAL_API_KEY set."""
    with patch("app.api.internal.auto_degrade.settings") as mock_settings:
        mock_settings.INTERNAL_API_KEY = "test-internal-key-12345"
        with TestClient(app) as tc:
            yield tc


@pytest.fixture
def auth_headers():
    return {"X-Internal-API-Key": "test-internal-key-12345"}


# ---------------------------------------------------------------------------
# Webhook handler tests
# ---------------------------------------------------------------------------


class TestWebhookAuth:
    def test_missing_api_key_returns_401(self, client):
        resp = client.post("/api/internal/auto-degrade/webhook", json={})
        assert resp.status_code == 401

    def test_invalid_api_key_returns_401(self, client):
        resp = client.post(
            "/api/internal/auto-degrade/webhook",
            json={},
            headers={"X-Internal-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_valid_api_key_passes_auth(self, client, auth_headers):
        resp = client.post(
            "/api/internal/auto-degrade/webhook",
            json={"alerts": []},
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestWebhookPayload:
    def test_empty_alerts_returns_no_alerts(self, client, auth_headers):
        resp = client.post(
            "/api/internal/auto-degrade/webhook",
            json={"alerts": []},
            headers=auth_headers,
        )
        data = resp.json()
        assert data["status"] == "no_alerts"
        assert data["processed"] == 0

    def test_unmapped_alert_is_skipped(self, client, auth_headers):
        payload = {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "SomeOtherAlert"},
                }
            ],
        }
        with patch("app.api.internal.auto_degrade.execute_auto_response", new_callable=AsyncMock):
            resp = client.post(
                "/api/internal/auto-degrade/webhook",
                json=payload,
                headers=auth_headers,
            )
        data = resp.json()
        assert data["status"] == "processed"
        assert data["actions_taken"] == 0


class TestAlertNameMapping:
    def test_latency_maps_to_llm_degrade(self):
        assert ALERT_NAME_MAP["SparkleBackendP95LatencyHigh"] == AlertType.LLM_LATENCY_HIGH

    def test_5xx_maps_to_gw_high_5xx(self):
        assert ALERT_NAME_MAP["SparkleBackendHigh5xxRate"] == AlertType.GW_HIGH_5XX

    def test_event_lag_maps_correctly(self):
        assert ALERT_NAME_MAP["SparkleEventStreamLagHigh"] == AlertType.EVENT_BUS_LAG
        assert ALERT_NAME_MAP["SparkleEventBusConsumerLagHigh"] == AlertType.EVENT_BUS_LAG

    def test_db_pool_maps_correctly(self):
        assert ALERT_NAME_MAP["SparkleDatabasePoolExhaustion"] == AlertType.DB_CONNECTION_EXHAUST

    def test_memory_maps_to_redis(self):
        assert ALERT_NAME_MAP["SparkleContainerMemoryHigh"] == AlertType.REDIS_NEAR_FULL


# ---------------------------------------------------------------------------
# execute_auto_response tests
# ---------------------------------------------------------------------------


class TestExecuteAutoResponse:
    @pytest.mark.asyncio
    async def test_firing_sets_mode_to_live(self):
        mock_redis = AsyncMock()

        with patch("app.core.cache.cache_service") as mock_cs:
            mock_cs.redis = mock_redis
            with patch("app.api.internal.auto_degrade._write_audit", new_callable=AsyncMock):
                result = await execute_auto_response(
                    AlertType.LLM_LATENCY_HIGH,
                    "firing",
                    {"alertname": "SparkleBackendP95LatencyHigh"},
                )

        assert result["status"] == "success"
        assert result["action"] == "live"
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "sparkle:aurora:slo_auto:llm_degrade"
        assert call_args[0][1] == "live"

    @pytest.mark.asyncio
    async def test_resolved_sets_mode_to_off(self):
        mock_redis = AsyncMock()

        with patch("app.core.cache.cache_service") as mock_cs:
            mock_cs.redis = mock_redis
            with patch("app.api.internal.auto_degrade._write_audit", new_callable=AsyncMock):
                result = await execute_auto_response(
                    AlertType.LLM_LATENCY_HIGH,
                    "resolved",
                    {"alertname": "SparkleBackendP95LatencyHigh"},
                )

        assert result["status"] == "success"
        assert result["action"] == "off"
        call_args = mock_redis.set.call_args
        assert call_args[0][1] == "off"

    @pytest.mark.asyncio
    async def test_redis_failure_returns_error(self):
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = Exception("Redis connection failed")

        with patch("app.core.cache.cache_service") as mock_cs:
            mock_cs.redis = mock_redis
            with patch("app.api.internal.auto_degrade._write_audit", new_callable=AsyncMock):
                result = await execute_auto_response(
                    AlertType.EVENT_BUS_LAG,
                    "firing",
                    {"alertname": "SparkleEventStreamLagHigh"},
                )

        assert result["status"] == "error"
        assert "Redis connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_all_five_alert_types_have_bindings(self):
        for alert_type in AlertType:
            assert alert_type in SLO_AUTO_DEGRADE_BINDINGS
            binding = SLO_AUTO_DEGRADE_BINDINGS[alert_type]
            assert binding.stage == "slo_auto"
            assert binding.redis_key.startswith("aurora:slo_auto:")
            assert binding.fallback_mode == "off"


# ---------------------------------------------------------------------------
# Audit event publishing tests (V3-FIX-491)
# ---------------------------------------------------------------------------


class TestAuditEventPublishing:
    """V3-FIX-491: ``_write_audit`` must call ``event_bus.publish`` with the
    real ``(event_type: str, payload: dict)`` signature. 修前单实参传事件对象，
    publish 调用点直接 TypeError 且被本函数 ``except Exception`` 吞掉——SLO
    自动降级/升级的审计事件从未进入 Redis Stream。"""

    @pytest.mark.asyncio
    async def test_publish_called_with_event_type_str_and_dict_payload(self):
        with patch("app.core.event_bus.event_bus.publish", new_callable=AsyncMock) as mock_publish:
            await _write_audit(
                alert_type=AlertType.LLM_LATENCY_HIGH,
                alert_status="firing",
                action_taken="Degrading LLM to cheaper/faster model tier",
                alert_labels={"alertname": "SparkleBackendP95LatencyHigh"},
                result="mode=live",
                duration_s=0.123456,
            )

        mock_publish.assert_awaited_once()
        args, kwargs = mock_publish.await_args
        event_type = args[0] if args else kwargs["event_type"]
        payload = args[1] if len(args) > 1 else kwargs["payload"]

        assert isinstance(event_type, str), "publish 第一实参必须是 event_type 字符串（修前把事件对象当 event_type 传）"
        assert event_type == "slo_auto_response_audit"
        assert isinstance(payload, dict), "publish 第二实参必须是 payload dict"

        assert payload["event_type"] == "slo_auto_response_audit"
        assert payload["alert_type"] == "LLM_LATENCY_HIGH"
        assert payload["alert_status"] == "firing"
        assert payload["action_taken"] == "Degrading LLM to cheaper/faster model tier"
        assert payload["result"] == "mode=live"
        assert payload["duration_s"] == 0.1235  # round(…, 4)
        assert json.loads(payload["alert_labels"]) == {"alertname": "SparkleBackendP95LatencyHigh"}
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_audit_event_reaches_redis_stream(self):
        """端到端回归：真实 publish 路径把审计事件写入 sparkle_events 流。"""
        from app.core.event_bus import event_bus

        mock_redis = AsyncMock()
        mock_redis.xadd.return_value = "1758-0"
        mock_redis.xinfo_groups.return_value = [{"name": "test-group"}]

        with patch.object(event_bus, "redis", mock_redis):
            await _write_audit(
                alert_type=AlertType.GW_HIGH_5XX,
                alert_status="resolved",
                action_taken="Relaxing rate limits to normal",
                alert_labels={"alertname": "SparkleBackendHigh5xxRate"},
                result="mode=off",
                duration_s=0.05,
            )

        mock_redis.xadd.assert_awaited_once()
        call = mock_redis.xadd.await_args
        stream_name = call.args[0]
        body = call.args[1]
        assert stream_name == "sparkle_events"
        # _serialize_stream_body 会把所有值字符串化
        assert body["event_type"] == "slo_auto_response_audit"
        assert body["alert_type"] == "GW_HIGH_5XX"
        assert body["alert_status"] == "resolved"
        assert body["result"] == "mode=off"


# ---------------------------------------------------------------------------
# ClientDisconnectGuard tests
# ---------------------------------------------------------------------------


class TestClientDisconnectGuard:
    @pytest.mark.asyncio
    async def test_no_disconnect_completes_normally(self):
        mock_request = MagicMock()
        mock_request.is_disconnected = AsyncMock(return_value=False)
        save_fn = AsyncMock()

        async with ClientDisconnectGuard(mock_request, save_fn) as guard:
            await guard.check()

        save_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_disconnect_triggers_save_and_raises(self):
        mock_request = MagicMock()
        # First call returns False, second returns True
        mock_request.is_disconnected = AsyncMock(side_effect=[False, True])
        save_fn = AsyncMock()

        async with ClientDisconnectGuard(mock_request, save_fn) as guard:
            await guard.check()  # First check - OK
            with pytest.raises(ClientDisconnectGuard.ClientDisconnected):
                await guard.check()  # Second check - disconnected

        save_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_exit_saves_on_disconnect_even_without_check(self):
        mock_request = MagicMock()
        mock_request.is_disconnected = AsyncMock(return_value=True)
        save_fn = AsyncMock()

        async with ClientDisconnectGuard(mock_request, save_fn) as guard:
            # Never called check(), but exit should save if we set disconnected
            guard._disconnected = True

        save_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_failure_does_not_raise(self):
        mock_request = MagicMock()
        mock_request.is_disconnected = AsyncMock(return_value=True)
        save_fn = AsyncMock(side_effect=Exception("DB down"))

        async with ClientDisconnectGuard(mock_request, save_fn) as guard:
            guard._disconnected = True

        # Should not raise despite save failure
        save_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_save_prevented(self):
        mock_request = MagicMock()
        mock_request.is_disconnected = AsyncMock(return_value=True)
        save_fn = AsyncMock()

        async with ClientDisconnectGuard(mock_request, save_fn) as guard:
            guard._disconnected = True
            # __aexit__ will try to save
        # Only one save call
        save_fn.assert_called_once()


# ---------------------------------------------------------------------------
# Status endpoint tests
# ---------------------------------------------------------------------------


class TestStatusEndpoint:
    def test_status_returns_all_bindings(self, client, auth_headers):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.core.cache.cache_service") as mock_cs:
            mock_cs.redis = mock_redis
            with patch("app.api.internal.auto_degrade.settings") as mock_settings:
                mock_settings.INTERNAL_API_KEY = "test-internal-key-12345"
                mock_settings.SLO_AUTO_LLM_DEGRADE_MODE = "off"
                mock_settings.SLO_AUTO_REDIS_FALLBACK_MODE = "off"
                mock_settings.SLO_AUTO_DB_THROTTLE_MODE = "off"
                mock_settings.SLO_AUTO_EVENT_BUS_THROTTLE_MODE = "off"
                mock_settings.SLO_AUTO_RATE_LIMIT_TIGHTEN_MODE = "off"
                resp = client.get(
                    "/api/internal/auto-degrade/status",
                    headers=auth_headers,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "statuses" in data
        assert len(data["statuses"]) == 5
        for alert_type in AlertType:
            assert alert_type.value in data["statuses"]
            assert data["statuses"][alert_type.value]["degraded"] is False


# ---------------------------------------------------------------------------
# Integration: webhook → kill switch flip
# ---------------------------------------------------------------------------


class TestWebhookIntegration:
    def test_full_firing_flow(self, client, auth_headers):
        """Test complete flow: webhook → kill switch flip for LLM latency."""
        mock_redis = AsyncMock()

        payload = {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "SparkleBackendP95LatencyHigh",
                        "severity": "warning",
                    },
                }
            ],
        }

        with patch("app.core.cache.cache_service") as mock_cs:
            mock_cs.redis = mock_redis
            with patch("app.api.internal.auto_degrade._write_audit", new_callable=AsyncMock):
                resp = client.post(
                    "/api/internal/auto-degrade/webhook",
                    json=payload,
                    headers=auth_headers,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["actions_taken"] == 1
        assert data["results"][0]["status"] == "success"
        assert data["results"][0]["alert_type"] == "LLM_LATENCY_HIGH"
        assert data["results"][0]["action"] == "live"

    def test_resolved_flow(self, client, auth_headers):
        """Test alert resolved → kill switch back to off."""
        mock_redis = AsyncMock()

        payload = {
            "status": "resolved",
            "alerts": [
                {
                    "status": "resolved",
                    "labels": {
                        "alertname": "SparkleBackendHigh5xxRate",
                    },
                }
            ],
        }

        with patch("app.core.cache.cache_service") as mock_cs:
            mock_cs.redis = mock_redis
            with patch("app.api.internal.auto_degrade._write_audit", new_callable=AsyncMock):
                resp = client.post(
                    "/api/internal/auto-degrade/webhook",
                    json=payload,
                    headers=auth_headers,
                )

        assert resp.status_code == 200
        assert resp.json()["results"][0]["action"] == "off"
        assert resp.json()["results"][0]["alert_type"] == "GW_HIGH_5XX"

    def test_multiple_alerts_in_single_webhook(self, client, auth_headers):
        """Test multiple alerts processed in a single webhook call."""
        mock_redis = AsyncMock()

        payload = {
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "SparkleBackendP95LatencyHigh"},
                },
                {
                    "status": "firing",
                    "labels": {"alertname": "SparkleEventStreamLagHigh"},
                },
                {
                    "status": "firing",
                    "labels": {"alertname": "UnknownAlert"},
                },
            ],
        }

        with patch("app.core.cache.cache_service") as mock_cs:
            mock_cs.redis = mock_redis
            with patch("app.api.internal.auto_degrade._write_audit", new_callable=AsyncMock):
                resp = client.post(
                    "/api/internal/auto-degrade/webhook",
                    json=payload,
                    headers=auth_headers,
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_alerts"] == 3
        assert data["actions_taken"] == 2  # UnknownAlert skipped
