"""Execution orchestration service for OpenClaw handoff."""

from __future__ import annotations

import asyncio
import hashlib
import re
import socket
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
from loguru import logger
from sqlalchemy import String, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.openclaw import OpenClawClient, OpenClawConfig, IntentTranslator, ResultParser
from app.adapters.openclaw.client import OpenClawConfigurationError, OpenClawError, OpenClawTimeout
from app.adapters.openclaw.intent_translator import (
    IntentTranslationSafetyError,
    describe_tool_call,
    summarize_tool_input,
)
from app.config import settings
from app.core.event_bus import event_bus
from app.core.event_types import (
    EXECUTION_DELEGATED,
    EXECUTION_HANDED_BACK,
    EXECUTION_NODE_SELECTED,
    EXECUTION_QUALITY_RECORDED,
    EXECUTION_RESULT_INGESTED,
    EXECUTION_STATUS_CHANGED,
    EXECUTION_TEMPLATE_SELECTED,
)
from app.core.execution_router import ExecutionRouter, RoutingDecision
from app.core.execution_trust import ExecutionTrustEngine, TrustEvaluation
from app.core.task_monitor import task_monitor_service
from app.models.background_task import BackgroundTaskStatus, BackgroundTaskType
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionTargetEnv,
    ExecutorType,
    TrustLevel,
)
from app.models.execution_audit_log import ExecutionAuditLog
from app.models.execution_record import ExecutionRecord
from app.models.task import Task, TaskStatus, TaskType
from app.services.execution_ingestor import ExecutionIngestor
from app.services.execution_learning_service import ExecutionLearningService
from app.services.execution_node_service import ExecutionNode, ExecutionNodeService
from app.services.execution_preference_service import ExecutionPreferenceService
from app.services.execution_quality_service import ExecutionQualityService
from app.services.execution_risk_assessor import ExecutionRiskAssessor
from app.services.execution_result_validator import ExecutionResultValidator
from app.services.execution_template_service import ExecutionTemplateService
from app.services.openclaw_connection_profile_service import OpenClawConnectionProfileService
from app.services.plan_execution_record_service import PlanExecutionRecordService

ExecutionStreamSink = Callable[[str, dict[str, Any]], Awaitable[None] | None]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ExecutionService:
    """Phase 1 execution service for task handoff and synchronous dispatch."""

    _shared_classify_cache: dict[str, tuple[RoutingDecision, float]] = {}
    _classify_cache_ttl_seconds = 300.0
    _failure_counts: dict[str, int] = {}
    _degraded_users: dict[str, float] = {}
    _degradation_threshold = 3
    _degradation_window_seconds = 1800.0

    def __init__(self, db: AsyncSession, redis=None):
        self._db = db
        self._redis = redis
        self._base_config = OpenClawConfig.from_settings()
        self._config = self._base_config
        self._config_source = "global"
        self._router = ExecutionRouter(openclaw_enabled=self._config.enabled)
        self._trust_engine = ExecutionTrustEngine(
            auto_trust_min_history=settings.OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY,
            auto_trust_success_rate=settings.OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE,
        )
        self._client = OpenClawClient(self._config) if self._config.enabled else None
        self._translator = IntentTranslator()
        self._parser = ResultParser()
        self._plan_record_service = PlanExecutionRecordService(db)
        self._ingestor = ExecutionIngestor(db=db, redis=redis)
        self._learning_service = ExecutionLearningService(db=db, redis=redis)
        self._connection_profile_service = OpenClawConnectionProfileService(db, redis)
        self._preference_service = ExecutionPreferenceService(db, redis)
        self._template_service = ExecutionTemplateService()
        self._node_service = ExecutionNodeService(self._client)
        self._quality_service = ExecutionQualityService(db)
        self._risk_assessor = ExecutionRiskAssessor()
        self._result_validator = ExecutionResultValidator()
        self._classify_cache = self.__class__._shared_classify_cache
        self._classify_cache_ttl = self.__class__._classify_cache_ttl_seconds

    async def _ensure_runtime(self, *, user_id: UUID | None = None) -> OpenClawConfig:
        resolved_config, source = await self._connection_profile_service.resolve_config(
            user_id=user_id,
            fallback_config=self._base_config,
        )
        self._config = resolved_config
        self._config_source = source
        self._router = ExecutionRouter(openclaw_enabled=self._config.enabled)
        self._client = OpenClawClient(self._config) if self._config.enabled else None
        self._node_service = ExecutionNodeService(self._client)
        return self._config

    async def get_health(self, *, user_id: UUID | None = None) -> dict[str, Any]:
        await self._ensure_runtime(user_id=user_id)
        health_snapshot = await self._client.health_snapshot() if self._client else {"reachable": False}
        nodes = []
        if self._client:
            try:
                nodes = await self._node_service.list_nodes(connected_only=True)
            except OpenClawError as exc:
                health_snapshot["reachable"] = False
                health_snapshot["message"] = str(exc)
                logger.warning("OpenClaw node listing failed during health check: {}", exc)
            except Exception as exc:
                health_snapshot["reachable"] = False
                health_snapshot["message"] = str(exc)
                logger.exception("Unexpected OpenClaw node listing failure during health check")
        degradation = self.get_degradation_snapshot()
        return {
            "openclaw_enabled": self._config.enabled,
            "gateway_url": self._config.gateway_url if self._config.enabled else None,
            "transport": self._config.transport,
            "ws_url": self._config.ws_url if self._config.transport == "gateway_ws" else None,
            "reachable": bool(health_snapshot.get("reachable")),
            "latency_ms": health_snapshot.get("latency_ms"),
            "message": health_snapshot.get("message"),
            "supports_approvals": True,
            "ingestion_layer": "execution_ingestor",
            "connection_source": self._config_source,
            "connected_nodes": len(nodes),
            "supports_nodes": self._config.transport == "gateway_ws",
            "supports_templates": True,
            "supports_quality_loop": True,
            "capabilities": list(health_snapshot.get("capabilities") or []),
            "degraded_user_count": degradation["degraded_user_count"],
            "degradation_threshold": degradation["degradation_threshold"],
        }

    async def diagnose_connection(self, *, user_id: UUID | None = None) -> dict[str, Any]:
        await self._ensure_runtime(user_id=user_id)
        checks: list[dict[str, Any]] = []
        generated_at = _utcnow().isoformat()
        gateway_url = self._config.gateway_url or None
        ws_url = self._config.ws_url or None

        if not self._config.enabled:
            checks.append(
                self._build_diagnostic_check(
                    "configuration",
                    label="配置检查",
                    status="failed",
                    message="OpenClaw 集成尚未启用",
                    suggestion="先打开 OPENCLAW_ENABLED，再配置网关地址或设备配对信息。",
                    details={"enabled": False},
                )
            )
            return self._finalize_diagnostic_report(
                generated_at=generated_at,
                gateway_url=gateway_url,
                ws_url=ws_url,
                checks=checks,
            )

        endpoint_url = (
            self._config.ws_url
            if self._config.transport == "gateway_ws" and self._config.ws_url
            else self._config.gateway_url
        )
        parsed_endpoint = urlparse(endpoint_url or "")
        host = parsed_endpoint.hostname or ""
        port = parsed_endpoint.port or self._default_port_for_scheme(parsed_endpoint.scheme)
        has_credentials = bool(self._config.auth_token or self._config.ws_device_token)

        checks.append(
            self._build_diagnostic_check(
                "configuration",
                label="配置检查",
                status="passed" if endpoint_url and host else "failed",
                message=(
                    f"当前通过 {self._config_source} 使用 {self._config.transport} 连接 "
                    f"{endpoint_url or '(未配置地址)'}"
                ),
                suggestion=(
                    None
                    if endpoint_url and host
                    else "请先填写可访问的 OpenClaw 地址；公网场景优先填写可稳定访问的网关或 WS 地址。"
                ),
                details={
                    "transport": self._config.transport,
                    "connection_source": self._config_source,
                    "has_auth_token": bool(self._config.auth_token),
                    "has_device_token": bool(self._config.ws_device_token),
                    "has_credentials": has_credentials,
                },
            )
        )

        if not endpoint_url or not host:
            checks.append(
                self._build_diagnostic_check(
                    "dns",
                    label="DNS 解析",
                    status="skipped",
                    message="因为连接地址未配置完整，暂时跳过 DNS 检查",
                )
            )
            checks.append(
                self._build_diagnostic_check(
                    "tcp",
                    label="TCP 连通",
                    status="skipped",
                    message="因为连接地址未配置完整，暂时跳过端口连通检查",
                )
            )
            checks.append(
                self._build_diagnostic_check(
                    "protocol",
                    label="协议握手",
                    status="skipped",
                    message="因为连接地址未配置完整，暂时跳过协议握手检查",
                )
            )
            checks.append(
                self._build_diagnostic_check(
                    "auth",
                    label="认证检查",
                    status="skipped",
                    message="因为连接地址未配置完整，暂时跳过认证检查",
                )
            )
            checks.append(
                self._build_diagnostic_check(
                    "version",
                    label="版本兼容",
                    status="skipped",
                    message="因为连接地址未配置完整，暂时跳过版本兼容检查",
                )
            )
            return self._finalize_diagnostic_report(
                generated_at=generated_at,
                gateway_url=gateway_url,
                ws_url=ws_url,
                checks=checks,
            )

        dns_check = await self._diagnose_dns(host=host, port=port)
        checks.append(dns_check)

        tcp_check = await self._diagnose_tcp(host=host, port=port) if dns_check["status"] == "passed" else self._build_diagnostic_check(
            "tcp",
            label="TCP 连通",
            status="skipped",
            message="DNS 尚未通过，跳过端口连通检查",
        )
        checks.append(tcp_check)

        if self._config.transport == "gateway_ws":
            ws_checks = (
                await self._diagnose_gateway_ws()
                if tcp_check["status"] == "passed"
                else [
                    self._build_diagnostic_check(
                        "protocol",
                        label="协议握手",
                        status="skipped",
                        message="端口尚不可达，跳过 WebSocket 握手检查",
                    ),
                    self._build_diagnostic_check(
                        "auth",
                        label="认证检查",
                        status="skipped",
                        message="端口尚不可达，跳过设备或令牌认证检查",
                    ),
                    self._build_diagnostic_check(
                        "version",
                        label="版本兼容",
                        status="skipped",
                        message="端口尚不可达，跳过版本兼容检查",
                    ),
                ]
            )
            checks.extend(ws_checks)
        else:
            http_checks = (
                await self._diagnose_http_connection()
                if tcp_check["status"] == "passed"
                else [
                    self._build_diagnostic_check(
                        "protocol",
                        label="协议握手",
                        status="skipped",
                        message="端口尚不可达，跳过 HTTP 健康检查",
                    ),
                    self._build_diagnostic_check(
                        "auth",
                        label="认证检查",
                        status="skipped",
                        message="端口尚不可达，跳过执行权限检查",
                    ),
                    self._build_diagnostic_check(
                        "version",
                        label="版本兼容",
                        status="skipped",
                        message="端口尚不可达，跳过版本兼容检查",
                    ),
                ]
            )
            checks.extend(http_checks)

        return self._finalize_diagnostic_report(
            generated_at=generated_at,
            gateway_url=gateway_url,
            ws_url=ws_url,
            checks=checks,
        )

    async def classify_task(self, *, task_id: UUID, user_id: UUID) -> RoutingDecision:
        await self._ensure_runtime(user_id=user_id)
        task = await self._get_user_task(task_id=task_id, user_id=user_id)
        if self._is_user_degraded(user_id):
            return RoutingDecision(
                execution_mode=ExecutionMode.HUMAN,
                target_env=ExecutionTargetEnv.HUMAN,
                reason="execution_temporarily_degraded",
                confidence=0.98,
                risk_flags=["degraded_due_to_consecutive_failures"],
            )
        task_type = getattr(task.type, "value", task.type) or ""
        task_description = getattr(task, "description", "") or ""
        task_tags = getattr(task, "tags", None) or []
        cache_key = hashlib.md5(
            "|".join(
                [
                    str(task_type),
                    str(task.title or ""),
                    str(task_description),
                    ",".join(sorted(str(tag) for tag in task_tags)),
                ]
            ).encode("utf-8")
        ).hexdigest()
        now = time.time()
        cached = self._classify_cache.get(cache_key)
        if cached is not None:
            decision, cached_at = cached
            if now - cached_at < self._classify_cache_ttl:
                return decision

        decision = self._classify_task_entity(task)
        self._classify_cache[cache_key] = (decision, now)
        if len(self._classify_cache) > 100:
            cutoff = now - self._classify_cache_ttl
            self._classify_cache = {
                key: value for key, value in self._classify_cache.items() if value[1] >= cutoff
            }
        return decision

    async def _diagnose_dns(self, *, host: str, port: int) -> dict[str, Any]:
        try:
            infos = await asyncio.to_thread(
                socket.getaddrinfo,
                host,
                port,
                socket.AF_UNSPEC,
                socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            return self._build_diagnostic_check(
                "dns",
                label="DNS 解析",
                status="failed",
                message=f"无法解析主机 {host}",
                suggestion="请检查域名、局域网 DNS、Tailscale 名称或 Cloudflare Tunnel 地址是否正确。",
                details={"host": host, "port": port, "error": str(exc)},
            )

        addresses = sorted({str(item[4][0]) for item in infos if item[4]})
        return self._build_diagnostic_check(
            "dns",
            label="DNS 解析",
            status="passed",
            message=f"{host} 已解析到 {len(addresses)} 个地址",
            details={"host": host, "port": port, "addresses": addresses[:5]},
        )

    async def _diagnose_tcp(self, *, host: str, port: int) -> dict[str, Any]:
        writer = None
        started_at = time.monotonic()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0,
            )
            latency_ms = int((time.monotonic() - started_at) * 1000)
            return self._build_diagnostic_check(
                "tcp",
                label="TCP 连通",
                status="passed",
                message=f"{host}:{port} 可连通",
                details={"host": host, "port": port, "latency_ms": latency_ms},
            )
        except Exception as exc:
            return self._build_diagnostic_check(
                "tcp",
                label="TCP 连通",
                status="failed",
                message=f"无法连通 {host}:{port}",
                suggestion="请检查本机防火墙、端口映射、反向代理或远程网络链路是否真的开放。",
                details={"host": host, "port": port, "error": str(exc)},
            )
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

    async def _diagnose_http_connection(self) -> list[dict[str, Any]]:
        if not self._client:
            return [
                self._build_diagnostic_check(
                    "protocol",
                    label="协议握手",
                    status="failed",
                    message="OpenClaw HTTP 客户端尚未初始化",
                ),
                self._build_diagnostic_check(
                    "auth",
                    label="认证检查",
                    status="skipped",
                    message="客户端尚未初始化，跳过执行权限检查",
                ),
                self._build_diagnostic_check(
                    "version",
                    label="版本兼容",
                    status="skipped",
                    message="客户端尚未初始化，跳过版本兼容检查",
                ),
            ]

        started_at = time.monotonic()
        health_payload: dict[str, Any] | None = None
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as http:
                response = await http.get(
                    f"{self._config.gateway_url}/health",
                    headers=self._client._auth_headers(),
                )
            latency_ms = int((time.monotonic() - started_at) * 1000)
            if response.status_code == 200:
                health_payload = response.json() if response.content else {}
                if not isinstance(health_payload, dict):
                    health_payload = {}
                protocol_check = self._build_diagnostic_check(
                    "protocol",
                    label="协议握手",
                    status="passed",
                    message="HTTP /health 返回正常",
                    details={"latency_ms": latency_ms, "status_code": response.status_code},
                )
            else:
                protocol_check = self._build_diagnostic_check(
                    "protocol",
                    label="协议握手",
                    status="failed",
                    message=f"HTTP /health 返回 {response.status_code}",
                    suggestion="请确认 OpenClaw 网关本身已启动，并且反向代理没有拦截 /health。",
                    details={"status_code": response.status_code},
                )
        except Exception as exc:
            protocol_check = self._build_diagnostic_check(
                "protocol",
                label="协议握手",
                status="failed",
                message="无法完成 HTTP 健康检查",
                suggestion="请检查 gateway URL 是否可直连，以及 HTTPS 证书或代理配置是否匹配。",
                details={"error": str(exc)},
            )

        if protocol_check["status"] != "passed":
            return [
                protocol_check,
                self._build_diagnostic_check(
                    "auth",
                    label="认证检查",
                    status="skipped",
                    message="健康检查未通过，跳过执行权限检查",
                ),
                self._build_diagnostic_check(
                    "version",
                    label="版本兼容",
                    status="skipped",
                    message="健康检查未通过，跳过版本兼容检查",
                ),
            ]

        probe = await self._client._probe_http_execution_capability()
        auth_status = "passed" if probe.get("reachable") else "failed"
        auth_check = self._build_diagnostic_check(
            "auth",
            label="认证检查",
            status=auth_status,
            message=(
                "认证通过，执行入口可用"
                if auth_status == "passed"
                else str(probe.get("message") or "执行权限检查失败")
            ),
            suggestion=(
                None
                if auth_status == "passed"
                else "请检查令牌 scope、访客 preset、/v1/responses 代理转发和认证头是否一致。"
            ),
            details={
                "probe_status": probe.get("status"),
                "transport": self._config.transport,
            },
        )

        version_value = self._extract_diagnostic_version(health_payload)
        version_check = self._build_diagnostic_check(
            "version",
            label="版本兼容",
            status="passed" if version_value else "warning",
            message=(
                f"检测到 OpenClaw 版本 {version_value}"
                if version_value
                else "当前 /health 未暴露可识别版本，暂时按兼容模式处理"
            ),
            suggestion=(
                None
                if version_value
                else "如果后续出现协议异常，建议让网关在 /health 中暴露版本号，方便远程诊断。"
            ),
            details={
                "version": version_value,
                "health_keys": sorted(list((health_payload or {}).keys()))[:10],
            },
        )
        return [protocol_check, auth_check, version_check]

    async def _diagnose_gateway_ws(self) -> list[dict[str, Any]]:
        ws_client = getattr(self._client, "_ws_client", None) if self._client else None
        if ws_client is None:
            return [
                self._build_diagnostic_check(
                    "protocol",
                    label="协议握手",
                    status="failed",
                    message="Gateway WS 客户端尚未初始化",
                ),
                self._build_diagnostic_check(
                    "auth",
                    label="认证检查",
                    status="skipped",
                    message="客户端尚未初始化，跳过配对与认证检查",
                ),
                self._build_diagnostic_check(
                    "version",
                    label="版本兼容",
                    status="skipped",
                    message="客户端尚未初始化，跳过版本兼容检查",
                ),
            ]

        health_payload: dict[str, Any] | None = None
        try:
            async with ws_client._connect() as websocket:
                protocol_check = self._build_diagnostic_check(
                    "protocol",
                    label="协议握手",
                    status="passed",
                    message="WebSocket 已建立，开始进行 OpenClaw connect 握手",
                    details={"ws_url": self._config.ws_url},
                )
                try:
                    await ws_client._handshake(websocket)
                except Exception as exc:
                    return [
                        protocol_check,
                        self._build_diagnostic_check(
                            "auth",
                            label="认证检查",
                            status="failed",
                            message=str(exc),
                            suggestion=(
                                "如果你是远程用户，优先重新配对设备；如果只是本机调试，可确认 device token、"
                                "identity 文件和 operator 权限是否匹配。"
                            ),
                            details={
                                "ws_url": self._config.ws_url,
                                "has_device_token": bool(self._config.ws_device_token),
                                "has_auth_token": bool(self._config.auth_token),
                            },
                        ),
                        self._build_diagnostic_check(
                            "version",
                            label="版本兼容",
                            status="skipped",
                            message="认证未通过，跳过版本兼容检查",
                        ),
                    ]

                auth_check = self._build_diagnostic_check(
                    "auth",
                    label="认证检查",
                    status="passed",
                    message="Gateway WS 认证通过，设备或令牌可代表当前用户执行",
                    details={
                        "has_device_token": bool(self._config.ws_device_token),
                        "has_auth_token": bool(self._config.auth_token),
                    },
                )
                try:
                    health_payload = await ws_client._rpc(websocket, method="health", params={})
                except Exception as exc:
                    return [
                        protocol_check,
                        auth_check,
                        self._build_diagnostic_check(
                            "version",
                            label="版本兼容",
                            status="warning",
                            message="协议和认证都已通过，但 health RPC 未返回版本信息",
                            suggestion="通常不影响执行；如果跨版本出现兼容问题，再检查网关与节点版本。",
                            details={"error": str(exc)},
                        ),
                    ]
        except Exception as exc:
            return [
                self._build_diagnostic_check(
                    "protocol",
                    label="协议握手",
                    status="failed",
                    message=str(exc),
                    suggestion="请检查 WS 地址、反向代理升级头、TLS 配置和公网隧道是否正确转发 WebSocket。",
                    details={"ws_url": self._config.ws_url},
                ),
                self._build_diagnostic_check(
                    "auth",
                    label="认证检查",
                    status="skipped",
                    message="协议握手失败，跳过认证检查",
                ),
                self._build_diagnostic_check(
                    "version",
                    label="版本兼容",
                    status="skipped",
                    message="协议握手失败，跳过版本兼容检查",
                ),
            ]

        version_value = self._extract_diagnostic_version(health_payload)
        return [
            protocol_check,
            auth_check,
            self._build_diagnostic_check(
                "version",
                label="版本兼容",
                status="passed" if version_value else "warning",
                message=(
                    f"Gateway WS 版本信息已识别：{version_value}"
                    if version_value
                    else "Gateway WS 可执行，但 health RPC 没有可识别版本号"
                ),
                suggestion=(
                    None
                    if version_value
                    else "建议让远程网关暴露版本信息，这样跨公网排障时会更快定位兼容性问题。"
                ),
                details={
                    "version": version_value,
                    "health_keys": sorted(list((health_payload or {}).keys()))[:10],
                    "protocol_version": self._config.ws_protocol_version,
                },
            ),
        ]

    def _finalize_diagnostic_report(
        self,
        *,
        generated_at: str,
        gateway_url: str | None,
        ws_url: str | None,
        checks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        failed = next((check for check in checks if check.get("status") == "failed"), None)
        warning = next((check for check in checks if check.get("status") == "warning"), None)
        auth_ok = any(check.get("key") == "auth" and check.get("status") == "passed" for check in checks)
        protocol_ok = any(check.get("key") == "protocol" and check.get("status") == "passed" for check in checks)
        reachable = auth_ok and protocol_ok
        overall_status = "failed" if failed else "warning" if warning else "passed"
        if failed:
            summary = f"{failed.get('label')}未通过：{failed.get('message')}"
        elif warning:
            summary = f"主链路已通，但仍有提示：{warning.get('message')}"
        else:
            summary = "连接链路检查通过，OpenClaw 已准备好接收远程执行。"
        return {
            "reachable": reachable,
            "overall_status": overall_status,
            "summary": summary,
            "generated_at": generated_at,
            "transport": self._config.transport,
            "connection_source": self._config_source,
            "gateway_url": gateway_url,
            "ws_url": ws_url,
            "checks": checks,
        }

    def _build_diagnostic_check(
        self,
        key: str,
        *,
        label: str,
        status: str,
        message: str,
        suggestion: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "status": status,
            "message": message,
            "suggestion": suggestion,
            "details": details or {},
        }

    @staticmethod
    def _default_port_for_scheme(scheme: str | None) -> int:
        normalized = (scheme or "").lower()
        if normalized in {"https", "wss"}:
            return 443
        return 80

    @staticmethod
    def _extract_diagnostic_version(payload: dict[str, Any] | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        candidate = (
            payload.get("version")
            or payload.get("appVersion")
            or payload.get("app_version")
            or payload.get("gatewayVersion")
            or payload.get("gateway_version")
        )
        text = str(candidate or "").strip()
        return text or None

    async def create_intent(
        self,
        *,
        task_id: UUID,
        user_id: UUID,
        goal: str | None = None,
        instructions: list[str] | None = None,
        policy: dict[str, Any] | None = None,
        success_criteria: dict[str, Any] | None = None,
        result_contract: dict[str, Any] | None = None,
        template_id: str | None = None,
        preferred_node_id: str | None = None,
    ) -> ExecutionIntent:
        await self._ensure_runtime(user_id=user_id)
        task = await self._get_user_task(task_id=task_id, user_id=user_id)
        if self._is_user_degraded(user_id):
            task.execution_mode = ExecutionMode.HUMAN.value
            self._db.add(task)
            await self._db.commit()
            raise ValueError("AI execution is temporarily degraded after consecutive failures")
        await self._ensure_no_active_intent(task_id=task.id, user_id=user_id)
        execution_goal = (goal or task.title or "").strip()
        selected_template = None
        template_payload: dict[str, Any] | None = None
        if template_id:
            selected_template = self._template_service.get_definition(template_id)
            template_payload = self._template_service.apply_template(
                task=task,
                template_id=template_id,
                goal_override=execution_goal,
            )
        elif not success_criteria and not result_contract:
            auto_template = self._template_service.auto_select(task=task, goal_override=execution_goal)
            if auto_template is not None:
                selected_template = auto_template.definition
                template_payload = self._template_service.apply_template(
                    task=task,
                    template_id=auto_template.definition.template_id,
                    goal_override=execution_goal,
                )

        decision = self._router.classify(
            task_type=task.type.value if task.type else "",
            goal=execution_goal,
            has_side_effects=self._infer_side_effects(execution_goal),
            has_clear_criteria=bool(success_criteria or (template_payload or {}).get("success_criteria")),
            task_tags=task.tags or [],
        )
        if selected_template is not None and template_payload is not None:
            decision = RoutingDecision(
                execution_mode=template_payload["execution_mode"],
                target_env=template_payload["target_env"],
                reason=f"template_selected:{selected_template.template_id}",
                confidence=max(decision.confidence, 0.82),
                risk_flags=list(decision.risk_flags),
            )
        if decision.execution_mode == ExecutionMode.HUMAN:
            raise ValueError(f"Task is not eligible for AI execution: {decision.reason}")

        intent_instructions = self._build_instructions(
            task,
            template_instructions=(template_payload or {}).get("instructions"),
            extra_instructions=instructions,
        )
        intent_policy = self._merge_dicts(
            self._default_policy(decision.target_env),
            (template_payload or {}).get("policy"),
            policy or {},
        )
        if decision.target_env == ExecutionTargetEnv.SHELL and self._config.default_workdir:
            intent_policy.setdefault("working_directory", self._config.default_workdir)
        intent_success = self._merge_dicts(
            (template_payload or {}).get("success_criteria"),
            success_criteria or {"type": "non_empty"},
        )
        intent_contract = self._merge_dicts(
            (template_payload or {}).get("result_contract"),
            result_contract or {},
        )

        strategy = await self._quality_service.assign_strategy(
            user_id=user_id,
            target_env=decision.target_env.value if decision.target_env else "general",
            execution_mode=decision.execution_mode,
            template_id=selected_template.template_id if selected_template else None,
        )
        intent_policy["quality_strategy"] = strategy.to_policy_payload()
        self._apply_strategy_to_payload(
            strategy=strategy,
            instructions=intent_instructions,
            policy=intent_policy,
            result_contract=intent_contract,
        )
        await self._attach_duration_estimate(
            user_id=user_id,
            target_env=decision.target_env,
            policy=intent_policy,
            fallback_minutes=task.estimated_minutes,
        )
        await self._apply_user_execution_controls(
            user_id=user_id,
            target_env=decision.target_env,
            goal=execution_goal,
            instructions=intent_instructions,
            policy=intent_policy,
        )

        required_node_command = str(
            intent_policy.get("target_node_command")
            or intent_policy.get("required_node_command")
            or (template_payload or {}).get("required_node_command")
            or ""
        ) or None
        selected_node = None
        node_selection: dict[str, Any] = {}
        try:
            selected_node, node_selection = await self._select_best_node(
                user_id=user_id,
                preferred_node_id=preferred_node_id,
                required_command=required_node_command,
                target_env=decision.target_env,
                intent=None,
            )
        except OpenClawError as exc:
            logger.warning("Execution node discovery failed for task {}: {}", task.id, exc)
            raise ValueError(str(exc)) from exc
        except ValueError:
            raise
        except Exception as exc:
            logger.warning("Execution node discovery failed for task {}: {}", task.id, exc)
            if required_node_command:
                raise ValueError(
                    f"Task requires a node with {required_node_command} capability, but none is available."
                ) from exc
        if required_node_command and selected_node is None:
            raise ValueError(
                f"Task requires a node with {required_node_command} capability, but none is available."
            )
        if selected_node is not None:
            intent_policy = self._merge_dicts(
                intent_policy,
                self._node_service.build_policy_patch(
                    node=selected_node,
                    required_command=required_node_command,
                ),
            )
        if node_selection:
            intent_policy["node_selection"] = node_selection
        idempotency_key = self._build_idempotency_key(task)

        intent = ExecutionIntent(
            plan_id=task.plan_id,
            task_id=task.id,
            user_id=user_id,
            execution_mode=decision.execution_mode,
            executor=ExecutorType.OPENCLAW,
            goal=execution_goal,
            instructions=intent_instructions,
            target_env=decision.target_env,
            policy=intent_policy,
            success_criteria=intent_success,
            result_contract=intent_contract,
            timeout_seconds=self._config.default_timeout_seconds,
            status=ExecutionIntentStatus.READY,
            trust_level=TrustLevel.RAW,
            idempotency_key=idempotency_key,
        )
        self._db.add(intent)
        task.execution_mode = decision.execution_mode.value
        self._db.add(task)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._db.refresh(task)

        await self._publish_status_event(intent, old_status=None)
        await event_bus.publish(
            EXECUTION_DELEGATED,
            {
                "event_type": EXECUTION_DELEGATED,
                "user_id": str(user_id),
                "task_id": str(task.id),
                "plan_id": str(task.plan_id) if task.plan_id else None,
                "execution_intent_id": str(intent.id),
                "execution_mode": intent.execution_mode.value,
                "executor": intent.executor.value,
                "target_env": intent.target_env.value if intent.target_env else None,
                "timestamp": _utcnow().isoformat(),
            },
        )
        if selected_template is not None:
            await event_bus.publish(
                EXECUTION_TEMPLATE_SELECTED,
                {
                    "event_type": EXECUTION_TEMPLATE_SELECTED,
                    "user_id": str(user_id),
                    "task_id": str(task.id),
                    "execution_intent_id": str(intent.id),
                    "template_id": selected_template.template_id,
                    "template_name": selected_template.name,
                    "timestamp": _utcnow().isoformat(),
                },
            )
        if selected_node is not None:
            await event_bus.publish(
                EXECUTION_NODE_SELECTED,
                {
                    "event_type": EXECUTION_NODE_SELECTED,
                    "user_id": str(user_id),
                    "task_id": str(task.id),
                    "execution_intent_id": str(intent.id),
                    "node_id": selected_node.node_id,
                    "node_name": selected_node.name,
                    "node_platform": selected_node.platform,
                    "node_selection": intent.policy.get("node_selection") or {},
                    "timestamp": _utcnow().isoformat(),
                },
            )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.PENDING,
            progress=0.0,
            progress_message="Execution intent created",
        )
        return intent

    async def dispatch(
        self,
        *,
        intent_id: UUID,
        user_id: UUID,
        stream_sink: ExecutionStreamSink | None = None,
    ) -> ExecutionIntent:
        await self._ensure_runtime(user_id=user_id)
        intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
        if intent.status not in {
            ExecutionIntentStatus.DRAFT,
            ExecutionIntentStatus.READY,
            ExecutionIntentStatus.QUEUED,
        }:
            raise ValueError(f"Intent {intent_id} is in status {intent.status.value}, cannot dispatch")
        if not self._client:
            raise OpenClawError("OpenClaw integration is not enabled")
        budget_status = await self._preference_service.check_budget_allowance(user_id=user_id)
        if not budget_status.get("allowed", True):
            return await self._block_intent_due_to_budget(
                intent=intent,
                budget_status=budget_status,
            )
        active_total = await self._active_execution_count(user_id=user_id, intent_id=intent.id)
        if active_total >= self._config.max_concurrent_runs:
            return await self._queue_intent(
                intent=intent,
                active_total=active_total,
            )

        old_status = intent.status
        intent.status = ExecutionIntentStatus.DISPATCHED
        intent.dispatched_at = _utcnow()
        intent.error_category = None
        intent.error_message = None
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await self._record_execution_audit(
            intent=intent,
            action="dispatch",
            actor="system",
            details={
                "transport": self._config.transport,
                "target_env": intent.target_env.value if intent.target_env else None,
                "approval_policy": (intent.policy or {}).get("approval_policy"),
                "target_node_id": (intent.policy or {}).get("target_node_id"),
                "contains_sensitive_data": bool((intent.policy or {}).get("contains_sensitive_data")),
            },
        )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.RUNNING,
            progress=0.2,
            progress_message="Dispatching to OpenClaw",
        )

        try:
            request_body = self._build_dispatch_payload(intent)
            old_status = intent.status
            intent.status = ExecutionIntentStatus.RUNNING
            self._db.add(intent)
            await self._db.commit()
            await self._db.refresh(intent)
            await self._publish_status_event(intent, old_status=old_status)

            execute_kwargs: dict[str, Any] = {
                "timeout_seconds": intent.timeout_seconds,
            }
            if self._config.transport == "gateway_ws":
                execute_kwargs["event_callback"] = lambda frame: self._handle_gateway_stream_event(
                    intent,
                    frame,
                    stream_sink=stream_sink,
                )
            raw_response = await self._client.execute(request_body, **execute_kwargs)
            await self._ingestor.ingest(intent=intent, raw_result=raw_response)
            await self._db.refresh(intent)
            if intent.status in {
                ExecutionIntentStatus.WAITING_APPROVAL,
                ExecutionIntentStatus.SUCCEEDED,
                ExecutionIntentStatus.PARTIAL,
            }:
                self._clear_failure_state(user_id)
            return intent
        except IntentTranslationSafetyError as exc:
            await self._mark_intent_failure(
                intent=intent,
                status=ExecutionIntentStatus.FAILED,
                error_category="security_policy",
                error_message=str(exc),
                audit_action="blocked",
            )
            return intent
        except OpenClawTimeout as exc:
            await self._mark_intent_failure(
                intent=intent,
                status=ExecutionIntentStatus.TIMED_OUT,
                error_category="timeout",
                error_message=str(exc),
                audit_action="timeout",
            )
            return intent
        except OpenClawError as exc:
            await self._mark_intent_failure(
                intent=intent,
                status=ExecutionIntentStatus.FAILED,
                error_category="adapter_error",
                error_message=str(exc),
                audit_action="failed",
            )
            return intent
        except Exception as exc:
            await self._mark_intent_failure(
                intent=intent,
                status=ExecutionIntentStatus.FAILED,
                error_category="unexpected_error",
                error_message=str(exc),
                audit_action="failed",
            )
            return intent

    async def handoff_to_openclaw(
        self,
        *,
        task_id: UUID,
        user_id: UUID,
        goal: str | None = None,
        instructions: list[str] | None = None,
        policy: dict[str, Any] | None = None,
        success_criteria: dict[str, Any] | None = None,
        result_contract: dict[str, Any] | None = None,
        template_id: str | None = None,
        preferred_node_id: str | None = None,
    ) -> ExecutionIntent:
        intent = await self.create_intent(
            task_id=task_id,
            user_id=user_id,
            goal=goal,
            instructions=instructions,
            policy=policy,
            success_criteria=success_criteria,
            result_contract=result_contract,
            template_id=template_id,
            preferred_node_id=preferred_node_id,
        )
        return await self.dispatch(intent_id=intent.id, user_id=user_id)

    async def handoff_tasks_batch(
        self,
        *,
        task_ids: list[UUID],
        user_id: UUID,
        execution_strategy: str = "auto",
    ) -> dict[str, Any]:
        await self._ensure_runtime(user_id=user_id)
        unique_task_ids: list[UUID] = []
        seen: set[UUID] = set()
        for task_id in task_ids:
            if task_id in seen:
                continue
            seen.add(task_id)
            unique_task_ids.append(task_id)
        if not unique_task_ids:
            raise ValueError("At least one task_id is required")

        intent_ids: list[UUID] = []
        for task_id in unique_task_ids:
            intent = await self.create_intent(
                task_id=task_id,
                user_id=user_id,
            )
            intent_ids.append(intent.id)
        return await self.dispatch_batch(
            intent_ids=intent_ids,
            user_id=user_id,
            execution_strategy=execution_strategy,
        )

    async def handoff_chat_control(
        self,
        *,
        session_id: str,
        user_id: UUID,
        message: str,
        request_id: str | None = None,
        preferred_node_id: str | None = None,
        stream_sink: ExecutionStreamSink | None = None,
    ) -> tuple[ExecutionIntent, ExecutionRecord | None]:
        await self._ensure_runtime(user_id=user_id)
        normalized_message = str(message or "").strip()
        normalized_session_id = str(session_id or "").strip()
        if not normalized_message:
            raise ValueError("Chat control message cannot be empty")
        if not normalized_session_id:
            raise ValueError("Chat control session_id is required")
        if self._is_user_degraded(user_id):
            raise ValueError("AI execution is temporarily degraded after consecutive failures")

        hidden_task = await self._create_hidden_chat_control_task(
            user_id=user_id,
            message=normalized_message,
        )
        intent = await self._create_chat_control_intent(
            task=hidden_task,
            user_id=user_id,
            session_id=normalized_session_id,
            message=normalized_message,
            request_id=request_id,
            preferred_node_id=preferred_node_id,
        )
        dispatched_intent = await self.dispatch(
            intent_id=intent.id,
            user_id=user_id,
            stream_sink=stream_sink,
        )
        record = await self.get_execution_record(intent_id=dispatched_intent.id, user_id=user_id)
        return dispatched_intent, record

    async def retry_intent(
        self,
        *,
        intent_id: UUID,
        user_id: UUID,
    ) -> ExecutionIntent:
        await self._ensure_runtime(user_id=user_id)
        previous_intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
        if previous_intent.status not in self._terminal_statuses():
            raise ValueError("Only terminal executions can be retried")

        preferred_node_id = str((previous_intent.policy or {}).get("target_node_id") or "").strip() or None
        template_metadata = (previous_intent.policy or {}).get("template_metadata") or {}
        template_id = str(template_metadata.get("template_id") or "").strip() or None
        if template_id == "chat_remote_control":
            template_id = None

        if self._is_chat_control_intent(previous_intent):
            session_id = str((previous_intent.policy or {}).get("source_chat_session_id") or "").strip()
            if not session_id:
                raise ValueError("This chat control execution cannot be retried because its session context is missing")
            retried_intent, _ = await self.handoff_chat_control(
                session_id=session_id,
                user_id=user_id,
                message=previous_intent.goal,
                request_id=f"retry:{previous_intent.id}",
                preferred_node_id=preferred_node_id,
            )
        else:
            retried_intent = await self.handoff_to_openclaw(
                task_id=previous_intent.task_id,
                user_id=user_id,
                goal=previous_intent.goal,
                instructions=list(previous_intent.instructions or []),
                policy=self._copy_retry_policy(previous_intent.policy or {}),
                success_criteria=dict(previous_intent.success_criteria or {}),
                result_contract=dict(previous_intent.result_contract or {}),
                template_id=template_id,
                preferred_node_id=preferred_node_id,
            )

        await self._record_execution_audit(
            intent=retried_intent,
            action="retry",
            actor="user",
            details={
                "retried_from_intent_id": str(previous_intent.id),
                "previous_status": previous_intent.status.value if previous_intent.status else None,
            },
        )
        return retried_intent

    async def dispatch_batch(
        self,
        *,
        intent_ids: list[UUID],
        user_id: UUID,
        execution_strategy: str = "auto",
    ) -> dict[str, Any]:
        await self._ensure_runtime(user_id=user_id)
        normalized_strategy = str(execution_strategy or "auto").strip().lower()
        if normalized_strategy not in {"auto", "sequential", "parallel"}:
            normalized_strategy = "auto"

        intents: list[ExecutionIntent] = []
        for intent_id in intent_ids:
            intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
            if intent.status not in {
                ExecutionIntentStatus.DRAFT,
                ExecutionIntentStatus.READY,
                ExecutionIntentStatus.QUEUED,
            }:
                raise ValueError(f"Intent {intent.id} is not dispatchable in batch mode")
            intents.append(intent)

        resolved_strategy = self._resolve_batch_strategy(intents=intents, requested=normalized_strategy)
        batch_id = str(uuid.uuid4())
        await event_bus.publish(
            "EXECUTION_BATCH_STARTED",
            {
                "event_type": "EXECUTION_BATCH_STARTED",
                "batch_id": batch_id,
                "user_id": str(user_id),
                "intent_ids": [str(intent.id) for intent in intents],
                "requested_strategy": normalized_strategy,
                "resolved_strategy": resolved_strategy,
                "timestamp": _utcnow().isoformat(),
            },
        )

        results: list[ExecutionIntent] = []
        if resolved_strategy == "parallel":
            if self._db.in_transaction():
                for intent in intents:
                    results.append(await self.dispatch(intent_id=intent.id, user_id=user_id))
            else:
                from app.db.session import AsyncSessionLocal

                async def _dispatch_isolated(target_intent_id: UUID) -> ExecutionIntent:
                    async with AsyncSessionLocal() as isolated_db:
                        service = ExecutionService(isolated_db, redis=self._redis)
                        return await service.dispatch(intent_id=target_intent_id, user_id=user_id)

                results = list(await asyncio.gather(*[_dispatch_isolated(intent.id) for intent in intents]))
        else:
            for intent in intents:
                results.append(await self.dispatch(intent_id=intent.id, user_id=user_id))

        completed_count = sum(
            1
            for item in results
            if item.status in {ExecutionIntentStatus.SUCCEEDED, ExecutionIntentStatus.PARTIAL}
        )
        failed_count = sum(
            1
            for item in results
            if item.status in {ExecutionIntentStatus.FAILED, ExecutionIntentStatus.TIMED_OUT, ExecutionIntentStatus.CANCELED}
        )
        queued_count = sum(1 for item in results if item.status == ExecutionIntentStatus.QUEUED)
        payload = {
            "batch_id": batch_id,
            "status": "completed" if queued_count == 0 else "partial",
            "requested_strategy": normalized_strategy,
            "resolved_strategy": resolved_strategy,
            "task_ids": [str(intent.task_id) for intent in results],
            "intent_ids": [str(intent.id) for intent in results],
            "completed_count": completed_count,
            "failed_count": failed_count,
            "queued_count": queued_count,
            "items": [
                {
                    "intent_id": str(intent.id),
                    "task_id": str(intent.task_id),
                    "status": intent.status.value if intent.status else None,
                    "target_env": intent.target_env.value if intent.target_env else None,
                    "error_message": intent.error_message,
                }
                for intent in results
            ],
        }
        await event_bus.publish(
            "EXECUTION_BATCH_COMPLETED",
            {
                "event_type": "EXECUTION_BATCH_COMPLETED",
                "batch_id": batch_id,
                "user_id": str(user_id),
                "intent_ids": payload["intent_ids"],
                "task_ids": payload["task_ids"],
                "requested_strategy": normalized_strategy,
                "resolved_strategy": resolved_strategy,
                "completed_count": completed_count,
                "failed_count": failed_count,
                "queued_count": queued_count,
                "status": payload["status"],
                "timestamp": _utcnow().isoformat(),
            },
        )
        return payload

    async def build_manual_fallback(
        self,
        *,
        user_id: UUID | None,
        goal: str,
        error_category: str | None,
        error_message: str,
        target_env: ExecutionTargetEnv | None,
        allow_retry: bool = False,
        retry_intent_id: UUID | None = None,
    ) -> dict[str, Any]:
        target_env_key = target_env.value if target_env else None
        suggestion = (
            await self._learning_service.get_error_suggestion(
                user_id=user_id,
                error_category=error_category,
                target_env=target_env_key,
            )
            if user_id is not None
            else None
        )
        recovery: dict[str, Any] = {
            "suggestion": (
                str((suggestion or {}).get("suggestion") or "").strip()
                or "当前自动执行链路不稳定，我先给你一份手动操作步骤。"
            ),
            "recommended_action": str((suggestion or {}).get("recommended_action") or "manual"),
            "retry_success_rate": (suggestion or {}).get("retry_success_rate"),
            "manual_steps": self._build_manual_steps(
                goal=goal,
                target_env=target_env,
                error_message=error_message,
            ),
            "manual_only": True,
        }
        if allow_retry and retry_intent_id is not None:
            recovery["retry_action"] = {
                "type": "retry_execution",
                "intent_id": str(retry_intent_id),
                "label": "一键重试",
            }
        return recovery

    async def get_intent(self, *, intent_id: UUID, user_id: UUID) -> ExecutionIntent:
        return await self._get_user_intent(intent_id=intent_id, user_id=user_id)

    async def list_task_intents(self, *, task_id: UUID, user_id: UUID) -> list[ExecutionIntent]:
        await self._get_user_task(task_id=task_id, user_id=user_id)
        result = await self._db.execute(
            select(ExecutionIntent)
            .where(
                ExecutionIntent.task_id == task_id,
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
            )
            .order_by(desc(ExecutionIntent.created_at))
        )
        return list(result.scalars().all())

    async def list_templates(self, *, task_id: UUID, user_id: UUID) -> list[dict[str, Any]]:
        task = await self._get_user_task(task_id=task_id, user_id=user_id)
        matches = self._template_service.list_templates(task=task)
        return [match.to_dict() for match in matches]

    async def list_nodes(
        self,
        *,
        user_id: UUID | None = None,
        connected_only: bool = True,
        last_connected: str | None = None,
    ) -> list[dict[str, Any]]:
        await self._ensure_runtime(user_id=user_id)
        nodes = await self._node_service.list_nodes(
            connected_only=connected_only,
            last_connected=last_connected,
        )
        return [node.to_dict() for node in nodes]

    async def invoke_node(
        self,
        *,
        user_id: UUID | None = None,
        node_id: str,
        command: str,
        params: dict[str, Any] | None = None,
        invoke_timeout_ms: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        await self._ensure_runtime(user_id=user_id)
        return await self._node_service.invoke_node(
            node_id=node_id,
            command=command,
            params=params,
            invoke_timeout_ms=invoke_timeout_ms,
            idempotency_key=idempotency_key,
        )

    async def get_quality_summary(self) -> dict[str, Any]:
        return await self._quality_service.get_summary()

    async def get_execution_record(self, *, intent_id: UUID, user_id: UUID) -> ExecutionRecord | None:
        intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
        result = await self._db.execute(
            select(ExecutionRecord).where(
                ExecutionRecord.execution_intent_id == intent.id,
                ExecutionRecord.user_id == user_id,
                ExecutionRecord.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def confirm_result(self, *, record_id: UUID, user_id: UUID) -> ExecutionRecord:
        await self._ensure_runtime(user_id=user_id)
        record = await self._ingestor._get_user_record(record_id=record_id, user_id=user_id)
        intent = await self._get_user_intent(intent_id=record.execution_intent_id, user_id=user_id)
        approval_id = self._extract_approval_id(record.raw_response or {})

        if (
            self._client
            and self._config.transport == "gateway_ws"
            and intent.status == ExecutionIntentStatus.WAITING_APPROVAL
            and approval_id
            and intent.external_run_id
        ):
            raw_response = await self._client.resolve_approval(
                approval_id=approval_id,
                decision="allow-once",
                run_id=intent.external_run_id,
                session_key=self._session_key_for_intent(intent),
                timeout_seconds=intent.timeout_seconds,
                event_callback=lambda frame: self._handle_gateway_stream_event(intent, frame),
            )
            confirmed = await self._ingestor.ingest(
                intent=intent,
                raw_result=raw_response,
                user_confirmed=raw_response.get("status") != "requires_action",
            )
            self._clear_failure_state(user_id)
            refreshed_intent = await self._get_user_intent(intent_id=intent.id, user_id=user_id)
            await self._record_execution_audit(
                intent=refreshed_intent,
                action="confirm",
                actor="user",
                details={
                    "record_id": str(record.id),
                    "approval_id": approval_id,
                    "remote_resolution": True,
                },
            )
            if refreshed_intent.status in self._terminal_statuses():
                await self._promote_next_queued_intent(user_id=user_id)
            return confirmed

        confirmed = await self._ingestor.confirm_result(record_id=record_id, user_id=user_id)
        self._clear_failure_state(user_id)
        refreshed_intent = await self._get_user_intent(intent_id=intent.id, user_id=user_id)
        await self._record_execution_audit(
            intent=refreshed_intent,
            action="confirm",
            actor="user",
            details={
                "record_id": str(record.id),
                "approval_id": approval_id,
                "remote_resolution": False,
            },
        )
        if refreshed_intent.status in self._terminal_statuses():
            await self._promote_next_queued_intent(user_id=user_id)
        return confirmed

    async def reject_result(
        self,
        *,
        record_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> ExecutionRecord:
        await self._ensure_runtime(user_id=user_id)
        record = await self._ingestor._get_user_record(record_id=record_id, user_id=user_id)
        intent = await self._get_user_intent(intent_id=record.execution_intent_id, user_id=user_id)
        approval_id = self._extract_approval_id(record.raw_response or {})

        if (
            self._client
            and self._config.transport == "gateway_ws"
            and intent.status == ExecutionIntentStatus.WAITING_APPROVAL
            and approval_id
            and intent.external_run_id
        ):
            try:
                await self._client.resolve_approval(
                    approval_id=approval_id,
                    decision="deny",
                    run_id=intent.external_run_id,
                    session_key=self._session_key_for_intent(intent),
                    timeout_seconds=max(30, intent.timeout_seconds),
                    event_callback=lambda frame: self._handle_gateway_stream_event(intent, frame),
                )
            except OpenClawError as exc:
                logger.warning("Failed to deny remote OpenClaw approval for intent {}: {}", intent.id, exc)

        rejected = await self._ingestor.reject_result(record_id=record_id, user_id=user_id, reason=reason)
        refreshed_intent = await self._get_user_intent(intent_id=intent.id, user_id=user_id)
        await self._record_execution_audit(
            intent=refreshed_intent,
            action="reject",
            actor="user",
            details={
                "record_id": str(record.id),
                "approval_id": approval_id,
                "reason": reason,
            },
        )
        await self._promote_next_queued_intent(user_id=user_id)
        return rejected

    async def cancel(self, *, intent_id: UUID, user_id: UUID) -> ExecutionIntent:
        await self._ensure_runtime(user_id=user_id)
        intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
        if intent.status in self._terminal_statuses():
            raise ValueError("Execution is already terminal")

        if self._client and self._config.transport == "gateway_ws":
            try:
                await self._client.cancel_run(
                    session_key=self._session_key_for_intent(intent),
                    run_id=intent.external_run_id,
                )
            except OpenClawError as exc:
                logger.warning("Failed to cancel remote OpenClaw run for intent {}: {}", intent.id, exc)

        old_status = intent.status
        intent.status = ExecutionIntentStatus.CANCELED
        intent.completed_at = _utcnow()
        intent.error_category = "canceled"
        intent.error_message = "Canceled by user"
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.CANCELLED,
            progress=1.0,
            progress_message="Execution canceled",
        )
        await self._record_execution_audit(
            intent=intent,
            action="cancel",
            actor="user",
            details={
                "external_run_id": intent.external_run_id,
                "transport": self._config.transport,
            },
        )
        self._clear_failure_state(user_id)
        record = await self.get_execution_record(intent_id=intent.id, user_id=user_id)
        if record is not None:
            await self._quality_service.record_outcome(intent=intent, record=record, outcome="canceled")
            await event_bus.publish(
                EXECUTION_QUALITY_RECORDED,
                {
                    "event_type": EXECUTION_QUALITY_RECORDED,
                    "user_id": str(user_id),
                    "execution_intent_id": str(intent.id),
                    "execution_record_id": str(record.id),
                    "variant_name": ((intent.policy or {}).get("quality_strategy") or {}).get("variant_name"),
                    "outcome": "canceled",
                    "quality_score": record.quality_score,
                    "timestamp": _utcnow().isoformat(),
                },
            )
        await self._promote_next_queued_intent(user_id=user_id)
        return intent

    async def handback(self, *, intent_id: UUID, user_id: UUID, reason: str | None = None) -> ExecutionIntent:
        intent = await self._get_user_intent(intent_id=intent_id, user_id=user_id)
        if intent.status in self._terminal_statuses():
            raise ValueError("Execution is already terminal")
        task = await self._get_user_task(task_id=intent.task_id, user_id=user_id)

        old_status = intent.status
        intent.status = ExecutionIntentStatus.HANDED_BACK
        intent.completed_at = _utcnow()
        intent.error_category = "handed_back"
        intent.error_message = reason or "Returned to user"
        task.execution_mode = ExecutionMode.HUMAN.value
        self._db.add(intent)
        self._db.add(task)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await event_bus.publish(
            EXECUTION_HANDED_BACK,
            {
                "event_type": EXECUTION_HANDED_BACK,
                "user_id": str(user_id),
                "execution_intent_id": str(intent.id),
                "task_id": str(task.id),
                "reason": reason,
                "progress_at_handback": 0.0,
                "timestamp": _utcnow().isoformat(),
            },
        )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.CANCELLED,
            progress=1.0,
            progress_message="Execution returned to user",
        )
        await self._record_execution_audit(
            intent=intent,
            action="handback",
            actor="user",
            details={"reason": reason},
        )
        self._clear_failure_state(user_id)
        record = await self.get_execution_record(intent_id=intent.id, user_id=user_id)
        if record is not None:
            await self._quality_service.record_outcome(intent=intent, record=record, outcome="handed_back")
            await event_bus.publish(
                EXECUTION_QUALITY_RECORDED,
                {
                    "event_type": EXECUTION_QUALITY_RECORDED,
                    "user_id": str(user_id),
                    "execution_intent_id": str(intent.id),
                    "execution_record_id": str(record.id),
                    "variant_name": ((intent.policy or {}).get("quality_strategy") or {}).get("variant_name"),
                    "outcome": "handed_back",
                    "quality_score": record.quality_score,
                    "timestamp": _utcnow().isoformat(),
                },
            )
        await self._learning_service.handle_handed_back(
            intent=intent,
            reason=reason,
        )
        await self._promote_next_queued_intent(user_id=user_id)
        return intent

    def _classify_task_entity(self, task: Task) -> RoutingDecision:
        return self._router.classify(
            task_type=task.type.value if task.type else "",
            goal=task.title or "",
            has_side_effects=self._infer_side_effects(task.title or ""),
            has_clear_criteria=False,
            task_tags=task.tags or [],
        )

    def _build_dispatch_payload(self, intent: ExecutionIntent) -> dict[str, Any]:
        if self._config.transport == "gateway_ws":
            return self._translator.translate_gateway_request(
                intent,
                agent_id=self._config.default_agent_id,
            )
        return self._translator.translate(intent, agent_id=self._config.default_agent_id)

    async def _record_execution_audit(
        self,
        *,
        intent: ExecutionIntent,
        action: str,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        audit = ExecutionAuditLog(
            intent_id=intent.id,
            user_id=intent.user_id,
            action=action,
            actor=actor,
            details=details or {},
        )
        try:
            self._db.add(audit)
            await self._db.commit()
        except Exception as exc:
            logger.warning("Failed to persist execution audit log for intent {} action {}: {}", intent.id, action, exc)
            await self._db.rollback()

    @staticmethod
    def _sensitive_quality_warning(intent: ExecutionIntent) -> dict[str, Any] | None:
        policy = intent.policy or {}
        if policy.get("contains_sensitive_data") is not True:
            return None
        risk = policy.get("_risk_assessment")
        matches = []
        if isinstance(risk, dict):
            matches = [
                item.get("label")
                for item in list(risk.get("sensitive_signals") or [])
                if isinstance(item, dict) and str(item.get("label") or "").strip()
            ]
        label_suffix = f"（{', '.join(matches[:3])}）" if matches else ""
        return {
            "code": "contains_sensitive_data",
            "severity": "warning",
            "message": f"本次执行涉及敏感数据{label_suffix}，请确认执行环境和结果回传链路是安全的。",
        }

    def _session_key_for_intent(self, intent: ExecutionIntent) -> str:
        return self._translator.build_session_key(intent, agent_id=self._config.default_agent_id)

    def _extract_approval_id(self, raw_response: dict[str, Any]) -> str | None:
        approval = raw_response.get("approval")
        if isinstance(approval, dict):
            approval_id = approval.get("id") or approval.get("approvalId")
            if approval_id:
                return str(approval_id)
        required_action = raw_response.get("required_action")
        if isinstance(required_action, dict):
            approval_id = required_action.get("approval_id") or required_action.get("approvalId")
            if approval_id:
                return str(approval_id)
        return None

    async def _handle_gateway_stream_event(
        self,
        intent: ExecutionIntent,
        frame: dict[str, Any],
        *,
        stream_sink: ExecutionStreamSink | None = None,
    ) -> None:
        if self._config.transport != "gateway_ws":
            return

        event_name = frame.get("event")
        payload = frame.get("payload") or {}

        if event_name == "agent":
            stream = payload.get("stream")
            if stream == "lifecycle":
                phase = payload.get("phase")
                if phase == "start":
                    await self._publish_monitor_progress(
                        intent=intent,
                        status=BackgroundTaskStatus.RUNNING,
                        progress=0.35,
                        progress_message="OpenClaw started execution",
                    )
                    await self._emit_stream_sink(
                        stream_sink,
                        "execution_lifecycle",
                        {
                            "intent_id": str(intent.id),
                            "phase": "start",
                            "message": "正在连接你的 OpenClaw 并启动执行",
                            "progress_hint": 0.35,
                        },
                    )
                elif phase == "end":
                    await self._publish_monitor_progress(
                        intent=intent,
                        status=BackgroundTaskStatus.RUNNING,
                        progress=0.95,
                        progress_message="OpenClaw finished execution",
                    )
                    await self._emit_stream_sink(
                        stream_sink,
                        "execution_lifecycle",
                        {
                            "intent_id": str(intent.id),
                            "phase": "end",
                            "message": "执行主体已完成，正在整理结果",
                            "progress_hint": 0.95,
                        },
                    )
                elif phase == "error":
                    await self._publish_monitor_progress(
                        intent=intent,
                        status=BackgroundTaskStatus.RUNNING,
                        progress=0.95,
                        progress_message="OpenClaw reported an execution error",
                        error_message=str(payload.get("error") or "OpenClaw lifecycle error"),
                    )
                    await self._emit_stream_sink(
                        stream_sink,
                        "execution_lifecycle",
                        {
                            "intent_id": str(intent.id),
                            "phase": "error",
                            "message": str(payload.get("error") or "OpenClaw 报告了执行错误"),
                            "progress_hint": 0.95,
                        },
                    )
            elif stream == "assistant":
                await self._publish_monitor_progress(
                    intent=intent,
                    status=BackgroundTaskStatus.RUNNING,
                    progress=0.7,
                    progress_message="OpenClaw is producing output",
                )
                text_chunk = self._extract_gateway_text(payload)
                if text_chunk:
                    await self._emit_stream_sink(
                        stream_sink,
                        "execution_delta",
                        {
                            "intent_id": str(intent.id),
                            "text": text_chunk,
                            "progress_hint": 0.7,
                        },
                    )
            elif stream == "tool":
                await self._publish_monitor_progress(
                    intent=intent,
                    status=BackgroundTaskStatus.RUNNING,
                    progress=0.55,
                    progress_message="OpenClaw is using tools",
                )
                tool_name = self._extract_gateway_tool_name(payload)
                tool_input = (
                    payload.get("input")
                    or payload.get("arguments")
                    or payload.get("params")
                    or payload.get("args")
                )
                input_summary = summarize_tool_input(tool_input)
                await self._emit_stream_sink(
                    stream_sink,
                    "execution_tool_call",
                    {
                        "intent_id": str(intent.id),
                        "tool_name": tool_name,
                        "input_summary": input_summary,
                        "message": describe_tool_call(tool_name, input_summary),
                        "progress_hint": 0.55,
                    },
                )
            return

        if event_name == "exec.approval.requested":
            await self._publish_monitor_progress(
                intent=intent,
                status=BackgroundTaskStatus.RUNNING,
                progress=0.85,
                progress_message="OpenClaw is waiting for approval",
                result_data={
                    "intent_id": str(intent.id),
                    "status": ExecutionIntentStatus.WAITING_APPROVAL.value,
                },
            )
            await self._emit_stream_sink(
                stream_sink,
                "execution_approval",
                {
                    "intent_id": str(intent.id),
                    "message": "OpenClaw 正在等待你确认后继续执行",
                    "progress_hint": 0.85,
                    "approval": payload,
                },
            )

    async def _emit_stream_sink(
        self,
        stream_sink: ExecutionStreamSink | None,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        if stream_sink is None:
            return
        maybe_awaitable = stream_sink(event_type, payload)
        if maybe_awaitable is not None:
            await maybe_awaitable

    @staticmethod
    def _extract_gateway_text(payload: dict[str, Any]) -> str:
        for key in ("delta", "text", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        message = payload.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, list):
                parts: list[str] = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    text = block.get("text") or block.get("delta")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
                if parts:
                    return "\n".join(parts)
        return ""

    @staticmethod
    def _extract_gateway_tool_name(payload: dict[str, Any]) -> str:
        for key in ("name", "toolName", "command", "tool"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        call = payload.get("call")
        if isinstance(call, dict):
            for key in ("name", "toolName", "command"):
                value = call.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return "unknown"

    async def _get_user_task(self, *, task_id: UUID, user_id: UUID) -> Task:
        task = await self._db.get(Task, task_id)
        if not task or task.user_id != user_id or task.deleted_at is not None:
            raise ValueError("Task not found")
        return task

    @staticmethod
    def _should_skip_task_sync(intent: ExecutionIntent) -> bool:
        return bool((intent.policy or {}).get("chat_control"))

    async def _get_user_intent(self, *, intent_id: UUID, user_id: UUID) -> ExecutionIntent:
        intent = await self._db.get(ExecutionIntent, intent_id)
        if not intent or intent.user_id != user_id or intent.deleted_at is not None:
            raise ValueError("Execution intent not found")
        return intent

    async def _ensure_no_active_intent(self, *, task_id: UUID, user_id: UUID) -> None:
        terminal_statuses = [status.value for status in self._terminal_statuses()]
        result = await self._db.execute(
            select(ExecutionIntent)
            .where(
                ExecutionIntent.task_id == task_id,
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
                cast(ExecutionIntent.status, String).notin_(terminal_statuses),
            )
            .order_by(desc(ExecutionIntent.created_at))
        )
        active_intent = result.scalar_one_or_none()
        if active_intent is not None:
            raise ValueError(f"Active execution already exists for task: {active_intent.id}")

    def _build_idempotency_key(self, task: Task) -> str:
        plan_id = str(task.plan_id) if task.plan_id else "noplan"
        return f"{plan_id}:{task.id}:{uuid.uuid4().hex[:8]}"

    async def _create_hidden_chat_control_task(
        self,
        *,
        user_id: UUID,
        message: str,
    ) -> Task:
        task = Task(
            user_id=user_id,
            plan_id=None,
            title=self._build_chat_control_title(message),
            type=TaskType.PLANNING,
            tags=["openclaw", "chat_control", "hidden"],
            estimated_minutes=5,
            difficulty=1,
            energy_cost=1,
            guide_content=message,
            status=TaskStatus.PENDING,
            execution_mode=ExecutionMode.AGENT.value,
            priority=0,
            order_index=0,
        )
        task.deleted_at = _utcnow()
        self._db.add(task)
        await self._db.commit()
        await self._db.refresh(task)
        return task

    async def _create_chat_control_intent(
        self,
        *,
        task: Task,
        user_id: UUID,
        session_id: str,
        message: str,
        request_id: str | None,
        preferred_node_id: str | None,
    ) -> ExecutionIntent:
        target_env = self._infer_chat_control_target_env(message)
        instructions = [
            "Treat this as a direct OpenClaw remote-control request from the user's Sparkle chat.",
            "Prefer taking action on the user's connected device instead of answering abstractly.",
            "If the request is ambiguous, unsafe, or blocked, explain the blocker clearly instead of guessing.",
        ]
        policy = self._default_policy(target_env)
        policy["allow_exec"] = True
        policy["allowed_tools"] = self._chat_control_allowed_tools(target_env)
        policy["approval_policy"] = "require_for_side_effects"
        policy["session_key"] = self._chat_control_session_key(user_id=user_id, session_id=session_id)
        policy["source_chat_session_id"] = session_id
        policy["chat_control"] = True
        policy["template_metadata"] = {
            "template_id": "chat_remote_control",
            "template_name": "Chat Remote Control",
        }
        if target_env == ExecutionTargetEnv.SHELL and self._config.default_workdir:
            policy.setdefault("working_directory", self._config.default_workdir)

        strategy = await self._quality_service.assign_strategy(
            user_id=user_id,
            target_env=target_env.value if target_env else "general",
            execution_mode=ExecutionMode.AGENT,
            template_id="chat_remote_control",
        )
        policy["quality_strategy"] = strategy.to_policy_payload()
        self._apply_strategy_to_payload(
            strategy=strategy,
            instructions=instructions,
            policy=policy,
            result_contract={},
        )
        await self._attach_duration_estimate(
            user_id=user_id,
            target_env=target_env,
            policy=policy,
            fallback_minutes=None,
        )
        await self._apply_user_execution_controls(
            user_id=user_id,
            target_env=target_env,
            goal=message,
            instructions=instructions,
            policy=policy,
        )

        required_node_command = "system.run" if target_env == ExecutionTargetEnv.SHELL else None
        selected_node = None
        node_selection: dict[str, Any] = {}
        if self._config.transport == "gateway_ws":
            try:
                selected_node, node_selection = await self._select_best_node(
                    user_id=user_id,
                    preferred_node_id=preferred_node_id,
                    required_command=required_node_command,
                    target_env=target_env,
                    intent=None,
                )
            except OpenClawError as exc:
                raise ValueError(str(exc)) from exc
            if selected_node is None:
                raise ValueError("No connected OpenClaw nodes are available for chat control")
            policy = self._merge_dicts(
                policy,
                self._node_service.build_policy_patch(
                    node=selected_node,
                    required_command=required_node_command,
                ),
            )
            if node_selection:
                policy["node_selection"] = node_selection

        intent = ExecutionIntent(
            plan_id=None,
            task_id=task.id,
            user_id=user_id,
            execution_mode=ExecutionMode.AGENT,
            executor=ExecutorType.OPENCLAW,
            goal=message,
            instructions=instructions,
            target_env=target_env,
            policy=policy,
            success_criteria={"type": "non_empty"},
            result_contract={},
            timeout_seconds=self._config.default_timeout_seconds,
            status=ExecutionIntentStatus.READY,
            trust_level=TrustLevel.RAW,
            idempotency_key=self._build_chat_control_idempotency_key(
                session_id=session_id,
                message=message,
                request_id=request_id,
            ),
        )
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)

        await self._publish_status_event(intent, old_status=None)
        await event_bus.publish(
            EXECUTION_DELEGATED,
            {
                "event_type": EXECUTION_DELEGATED,
                "user_id": str(user_id),
                "task_id": str(task.id),
                "plan_id": None,
                "execution_intent_id": str(intent.id),
                "execution_mode": intent.execution_mode.value,
                "executor": intent.executor.value,
                "target_env": intent.target_env.value if intent.target_env else None,
                "timestamp": _utcnow().isoformat(),
                "source": "chat_control",
                "chat_session_id": session_id,
            },
        )
        if selected_node is not None:
            await event_bus.publish(
                EXECUTION_NODE_SELECTED,
                {
                    "event_type": EXECUTION_NODE_SELECTED,
                    "user_id": str(user_id),
                    "task_id": str(task.id),
                    "execution_intent_id": str(intent.id),
                    "node_id": selected_node.node_id,
                    "node_name": selected_node.name,
                    "node_platform": selected_node.platform,
                    "node_selection": intent.policy.get("node_selection") or {},
                    "timestamp": _utcnow().isoformat(),
                    "source": "chat_control",
                },
            )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.PENDING,
            progress=0.0,
            progress_message="Chat control intent created",
        )
        return intent

    def _build_instructions(
        self,
        task: Task,
        *,
        template_instructions: list[str] | None,
        extra_instructions: list[str] | None,
    ) -> list[str]:
        instructions = list(template_instructions or [])
        instructions.extend(extra_instructions or [])
        if task.guide_content:
            instructions.append(f"Reference guide: {task.guide_content[:500]}")
        deduped: list[str] = []
        seen: set[str] = set()
        for item in instructions:
            normalized = str(item).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped

    def _default_policy(self, target_env: ExecutionTargetEnv | None) -> dict[str, Any]:
        allowed_tools: list[str] = []
        if target_env == ExecutionTargetEnv.BROWSER:
            allowed_tools = ["browser"]
        elif target_env == ExecutionTargetEnv.DOCUMENT:
            allowed_tools = ["browser", "read"]
        elif target_env == ExecutionTargetEnv.API:
            allowed_tools = ["http"]
        elif target_env == ExecutionTargetEnv.SHELL:
            allowed_tools = ["exec", "read"]

        return {
            "allow_exec": False,
            "allowed_tools": allowed_tools,
            "allowed_domains": [],
            "approval_policy": "deny",
        }

    async def _attach_duration_estimate(
        self,
        *,
        user_id: UUID,
        target_env: ExecutionTargetEnv | None,
        policy: dict[str, Any],
        fallback_minutes: int | None,
    ) -> None:
        estimated_seconds = await self._learning_service.estimate_duration(
            user_id=user_id,
            target_env=target_env.value if target_env else None,
        )
        source = "history"
        if estimated_seconds is None and fallback_minutes and fallback_minutes > 0:
            estimated_seconds = int(fallback_minutes) * 60
            source = "task_estimate"
        if estimated_seconds is None:
            return
        policy["duration_estimate"] = {
            "estimated_seconds": int(estimated_seconds),
            "estimated_minutes": max(1, round(int(estimated_seconds) / 60)),
            "source": source,
        }

    async def _active_execution_count(self, *, user_id: UUID, intent_id: UUID) -> int:
        active_count = await self._db.scalar(
            select(func.count(ExecutionIntent.id)).where(
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
                ExecutionIntent.id != intent_id,
                ExecutionIntent.status.in_(
                    [
                        ExecutionIntentStatus.DISPATCHED,
                        ExecutionIntentStatus.RUNNING,
                        ExecutionIntentStatus.WAITING_APPROVAL,
                    ]
                ),
            )
        )
        return int(active_count or 0)

    async def _queue_intent(
        self,
        *,
        intent: ExecutionIntent,
        active_total: int,
    ) -> ExecutionIntent:
        queued_before = await self._db.scalar(
            select(func.count(ExecutionIntent.id)).where(
                ExecutionIntent.user_id == intent.user_id,
                ExecutionIntent.deleted_at.is_(None),
                ExecutionIntent.id != intent.id,
                ExecutionIntent.status == ExecutionIntentStatus.QUEUED,
            )
        )
        queue_position = int(queued_before or 0) + 1
        message = (
            f"当前有 {active_total} 个任务在执行中，你的任务已进入等待队列，当前排在第 {queue_position} 位。"
        )
        old_status = intent.status
        intent.status = ExecutionIntentStatus.QUEUED
        intent.error_category = "concurrency_limited"
        intent.error_message = message
        policy = dict(intent.policy or {})
        policy["queue_state"] = {
            "position": queue_position,
            "active_count": active_total,
            "max_concurrent_runs": self._config.max_concurrent_runs,
        }
        intent.policy = policy
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.PENDING,
            progress=0.0,
            progress_message=message,
            result_data={
                "intent_id": str(intent.id),
                "status": intent.status.value,
                "queue_position": queue_position,
            },
        )
        return intent

    async def _block_intent_due_to_budget(
        self,
        *,
        intent: ExecutionIntent,
        budget_status: dict[str, Any],
    ) -> ExecutionIntent:
        old_status = intent.status
        intent.status = ExecutionIntentStatus.FAILED
        intent.error_category = str(budget_status.get("code") or "budget_exceeded")
        intent.error_message = str(budget_status.get("message") or "当前执行预算不足")
        policy = dict(intent.policy or {})
        policy["budget_state"] = dict(budget_status.get("budget") or {})
        intent.policy = policy
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await self._record_execution_audit(
            intent=intent,
            action="blocked",
            actor="system",
            details={
                "reason": "execution_budget_exceeded",
                "budget_state": policy["budget_state"],
                "message": intent.error_message,
            },
        )
        return intent

    async def _promote_next_queued_intent(self, *, user_id: UUID) -> None:
        active_total = await self._active_execution_count(
            user_id=user_id,
            intent_id=UUID(int=0),
        )
        if active_total >= self._config.max_concurrent_runs:
            return
        result = await self._db.execute(
            select(ExecutionIntent)
            .where(
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
                ExecutionIntent.status == ExecutionIntentStatus.QUEUED,
            )
            .order_by(ExecutionIntent.created_at.asc())
            .limit(1)
        )
        queued_intent = result.scalar_one_or_none()
        if queued_intent is None:
            return
        logger.info("Promoting queued execution intent {} for user {}", queued_intent.id, user_id)
        await self.dispatch(intent_id=queued_intent.id, user_id=user_id)

    async def _apply_user_execution_controls(
        self,
        *,
        user_id: UUID,
        target_env: ExecutionTargetEnv | None,
        goal: str,
        instructions: list[str],
        policy: dict[str, Any],
    ) -> None:
        preferences = await self._preference_service.get_preferences(
            user_id=user_id,
            include_recommendations=False,
        )
        category_stats = await self._learning_service.get_category_trust_stats(user_id=user_id)
        target_env_key = target_env.value if target_env else "general"
        trust_bucket = category_stats.get(target_env_key, {})
        action_key = self._infer_execution_action_key(
            target_env=target_env,
            goal=goal,
            instructions=instructions,
        )
        preference_rule = self._resolve_preference_rule(
            preferences=preferences,
            action_key=action_key,
        )
        if preference_rule in {"skip", "reject"}:
            raise ValueError(f"你的执行偏好当前不允许这类操作：{action_key}")

        risk = self._risk_assessor.assess(
            intent_goal=goal,
            instructions=instructions,
            policy=policy,
            target_env=target_env_key,
        )
        if risk.blocked:
            raise ValueError(risk.blocked_reason or "该操作因风险过高被拦截")

        approval_policy = self._approval_policy_for_rule(preference_rule)
        if approval_policy:
            policy["approval_policy"] = approval_policy

        if (
            preferences.get("mode") == "autonomous"
            and int(trust_bucket.get("total", 0) or 0) >= 3
            and float(trust_bucket.get("success_rate", 0.0) or 0.0) < 0.6
        ):
            policy["approval_policy"] = "require_for_side_effects"

        if (
            preferences.get("mode") != "cautious"
            and trust_bucket.get("current_trust") == "trusted"
            and float(trust_bucket.get("success_rate", 0.0) or 0.0) >= 0.85
            and risk.level in {"low", "medium"}
        ):
            policy["approval_policy"] = "deny"

        if risk.forced_confirm:
            policy["approval_policy"] = "require_before_completion"

        policy["execution_preferences"] = {
            "mode": preferences.get("mode"),
            "notification_level": preferences.get("notification_level"),
            "rule_key": action_key,
            "resolved_rule": preference_rule,
            "target_env_trust": trust_bucket,
            "node_affinity": preferences.get("node_affinity") or {},
        }
        policy["_risk_assessment"] = risk.to_dict()
        if risk.contains_sensitive_data:
            policy["contains_sensitive_data"] = True

    async def _select_best_node(
        self,
        *,
        user_id: UUID,
        target_env: ExecutionTargetEnv | None,
        preferred_node_id: str | None,
        required_command: str | None,
        intent: ExecutionIntent | None,
    ) -> tuple[ExecutionNode | None, dict[str, Any]]:
        nodes = await self._node_service.list_nodes(connected_only=False)
        if not nodes:
            return None, {}

        preferences = await self._preference_service.get_preferences(
            user_id=user_id,
            include_recommendations=False,
        )
        affinity_key = self._node_affinity_key(target_env)
        affinity_node_id = self._resolve_affinity_node_id(
            preferences=preferences,
            target_env=target_env,
        )
        connected_nodes = [node for node in nodes if node.connected]
        if not connected_nodes:
            return None, {
                "affinity_key": affinity_key,
                "preferred_node_id": preferred_node_id,
                "affinity_node_id": affinity_node_id,
                "waiting_for_node": True,
                "selection_mode": "offline",
            }

        requested_platform = ""
        if intent is not None:
            requested_platform = str((intent.policy or {}).get("target_platform") or "").strip().lower()

        scored: list[tuple[int, ExecutionNode, list[str]]] = []
        for node in connected_nodes:
            score, reasons = self._score_node_candidate(
                node=node,
                target_env=target_env,
                preferred_node_id=preferred_node_id,
                affinity_node_id=affinity_node_id,
                required_command=required_command,
                requested_platform=requested_platform,
            )
            if score <= -1000:
                continue
            scored.append((score, node, reasons))

        if not scored:
            return None, {
                "affinity_key": affinity_key,
                "preferred_node_id": preferred_node_id,
                "affinity_node_id": affinity_node_id,
                "waiting_for_node": False,
                "selection_mode": "unsupported",
            }

        scored.sort(
            key=lambda item: (
                item[0],
                -item[1].active_runs,
                item[1].name.lower(),
            ),
            reverse=True,
        )
        selected_node = scored[0][1]
        fallback_from = None
        if preferred_node_id and selected_node.node_id != preferred_node_id and selected_node.name != preferred_node_id:
            fallback_from = preferred_node_id
        elif affinity_node_id and selected_node.node_id != affinity_node_id and selected_node.name != affinity_node_id:
            fallback_from = affinity_node_id
        metadata = {
            "affinity_key": affinity_key,
            "preferred_node_id": preferred_node_id,
            "affinity_node_id": affinity_node_id,
            "selected_node_id": selected_node.node_id,
            "selected_node_label": selected_node.name,
            "selection_mode": "preferred" if preferred_node_id else ("affinity" if affinity_node_id else "automatic"),
            "fallback_applied": bool(fallback_from),
            "fallback_from_node_id": fallback_from,
            "fallback_reason": "preferred_node_unavailable" if fallback_from else None,
            "selection_reasons": scored[0][2],
        }
        return selected_node, metadata

    def _score_node_candidate(
        self,
        *,
        node: ExecutionNode,
        target_env: ExecutionTargetEnv | None,
        preferred_node_id: str | None,
        affinity_node_id: str | None,
        required_command: str | None,
        requested_platform: str,
    ) -> tuple[int, list[str]]:
        if required_command and not node.supports(required_command):
            return -1000, [f"missing:{required_command}"]

        score = 0
        reasons: list[str] = []
        if preferred_node_id and (node.node_id == preferred_node_id or node.name == preferred_node_id):
            score += 120
            reasons.append("explicit_preference")
        if affinity_node_id and (node.node_id == affinity_node_id or node.name == affinity_node_id):
            score += 90
            reasons.append("user_affinity")
        if requested_platform and node.platform.lower() == requested_platform:
            score += 20
            reasons.append("platform_match")
        if target_env == ExecutionTargetEnv.SHELL and node.supports("system.run"):
            score += 40
            reasons.append("shell_capable")
        if target_env == ExecutionTargetEnv.BROWSER and any(
            token in " ".join([*node.caps, *node.commands]).lower()
            for token in ("browser", "web", "chrome", "playwright")
        ):
            score += 20
            reasons.append("browser_capable")

        status = node.status.strip().lower()
        if status in {"idle", "ready", "online", "available"}:
            score += 15
            reasons.append("available")
        elif status in {"busy", "running"}:
            score -= 12
            reasons.append("busy")
        score -= max(node.active_runs, 0) * 8
        if node.active_runs > 0:
            reasons.append(f"active_runs:{node.active_runs}")

        if not reasons:
            reasons.append("first_available")
        return score, reasons

    @staticmethod
    def _node_affinity_key(target_env: ExecutionTargetEnv | None) -> str:
        if target_env == ExecutionTargetEnv.BROWSER:
            return "browser"
        if target_env == ExecutionTargetEnv.SHELL:
            return "shell"
        if target_env == ExecutionTargetEnv.API:
            return "api"
        if target_env == ExecutionTargetEnv.DOCUMENT:
            return "document"
        return "general"

    def _resolve_affinity_node_id(
        self,
        *,
        preferences: dict[str, Any],
        target_env: ExecutionTargetEnv | None,
    ) -> str | None:
        node_affinity = preferences.get("node_affinity") or {}
        if not isinstance(node_affinity, dict):
            return None
        key = self._node_affinity_key(target_env)
        selected = str(node_affinity.get(key) or node_affinity.get("general") or "").strip()
        return selected or None

    def _infer_execution_action_key(
        self,
        *,
        target_env: ExecutionTargetEnv | None,
        goal: str,
        instructions: list[str],
    ) -> str:
        content = " ".join([str(goal or ""), *[str(item or "") for item in instructions]]).lower()
        if target_env == ExecutionTargetEnv.BROWSER:
            if any(token in content for token in ("submit", "填写", "登录", "purchase", "支付", "upload", "发送")):
                return "browser_write"
            return "browser_read"
        if target_env == ExecutionTargetEnv.DOCUMENT:
            if any(token in content for token in ("delete", "删除", "remove")):
                return "file_delete"
            if any(token in content for token in ("write", "编辑", "修改", "保存", "create")):
                return "file_write"
            return "file_read"
        if target_env == ExecutionTargetEnv.API:
            return "send"
        if target_env == ExecutionTargetEnv.SHELL:
            if any(token in content for token in ("install", "brew ", "pip ", "npm install", "apt ")) :
                return "install"
            if any(token in content for token in ("delete", "删除", "remove", "rm ")) :
                return "file_delete"
            if any(token in content for token in ("cat ", "ls ", "pwd", "read", "查看")):
                return "shell_read"
            return "shell_exec"
        return "send"

    @staticmethod
    def _resolve_preference_rule(
        *,
        preferences: dict[str, Any],
        action_key: str,
    ) -> str:
        mode = str(preferences.get("mode") or "balanced")
        if mode == "cautious":
            return "confirm"
        if mode == "autonomous":
            return "auto"
        if mode == "custom":
            custom_rules = preferences.get("custom_rules") or {}
            return str(custom_rules.get(action_key) or "confirm")
        if action_key in {"browser_read", "file_read", "shell_read"}:
            return "auto"
        return "confirm"

    @staticmethod
    def _approval_policy_for_rule(rule: str) -> str:
        normalized = str(rule or "").strip().lower()
        if normalized == "auto":
            return "deny"
        return "require_for_side_effects"

    @staticmethod
    def _build_chat_control_title(message: str) -> str:
        normalized = " ".join(str(message or "").split()).strip()
        if not normalized:
            return "OpenClaw Chat Control"
        if len(normalized) <= 72:
            return normalized
        return f"{normalized[:69].rstrip()}..."

    def _build_chat_control_idempotency_key(
        self,
        *,
        session_id: str,
        message: str,
        request_id: str | None,
    ) -> str:
        seed = str(request_id or "").strip()
        if seed:
            return f"chatctl:{seed}"
        digest = hashlib.md5(f"{session_id}|{message}|{time.time()}".encode("utf-8")).hexdigest()
        return f"chatctl:{digest}"

    def _chat_control_session_key(self, *, user_id: UUID, session_id: str) -> str:
        agent_suffix = self._config.default_agent_id or "main"
        return f"sparkle:chat:{agent_suffix}:{user_id}:{session_id}"

    def _infer_chat_control_target_env(self, message: str) -> ExecutionTargetEnv | None:
        lowered = str(message or "").lower()
        browser_keywords = (
            "browser",
            "website",
            "web site",
            "网页",
            "网站",
            "浏览器",
            "打开页面",
            "open page",
            "open website",
            "search the web",
            "google",
        )
        shell_keywords = (
            "terminal",
            "shell",
            "command line",
            "命令行",
            "终端",
            "repo",
            "repository",
            "git",
            "pwd",
            "ls ",
            "cd ",
            "npm ",
            "python ",
            "pip ",
            "brew ",
            "文件夹",
            "目录",
        )
        if any(keyword in lowered for keyword in browser_keywords):
            return ExecutionTargetEnv.BROWSER
        if any(keyword in lowered for keyword in shell_keywords):
            return ExecutionTargetEnv.SHELL
        return None

    def _chat_control_allowed_tools(self, target_env: ExecutionTargetEnv | None) -> list[str]:
        if target_env == ExecutionTargetEnv.BROWSER:
            return ["browser", "read"]
        if target_env == ExecutionTargetEnv.SHELL:
            return ["exec", "read"]
        return ["browser", "exec", "read", "http"]

    @staticmethod
    def _is_chat_control_intent(intent: ExecutionIntent) -> bool:
        return bool((intent.policy or {}).get("chat_control"))

    @staticmethod
    def _copy_retry_policy(policy: dict[str, Any]) -> dict[str, Any]:
        copied = dict(policy or {})
        copied.pop("queue_state", None)
        copied.pop("error_recovery", None)
        copied.pop("_risk_assessment", None)
        return copied

    def _resolve_batch_strategy(
        self,
        *,
        intents: list[ExecutionIntent],
        requested: str,
    ) -> str:
        if requested in {"sequential", "parallel"}:
            return requested
        if len(intents) <= 1:
            return "sequential"
        signatures = {self._goal_signature(intent.goal) for intent in intents}
        target_envs = {intent.target_env.value if intent.target_env else "general" for intent in intents}
        if len(signatures) == len(intents) and len(target_envs) > 1:
            return "parallel"
        return "sequential"

    async def _build_error_recovery(
        self,
        *,
        intent: ExecutionIntent,
        error_category: str,
        error_message: str,
    ) -> dict[str, Any] | None:
        suggestion = await self._learning_service.get_error_suggestion(
            user_id=intent.user_id,
            error_category=error_category,
            target_env=intent.target_env.value if intent.target_env else None,
        )
        recent_failures = await self._recent_similar_failure_count(intent=intent)
        recommended_action = str((suggestion or {}).get("recommended_action") or "retry")
        manual_only = recent_failures >= 3 or recommended_action == "manual"
        recovery: dict[str, Any] = {
            "suggestion": str((suggestion or {}).get("suggestion") or error_message or "").strip(),
            "recommended_action": "manual" if manual_only else recommended_action,
            "retry_success_rate": (suggestion or {}).get("retry_success_rate"),
            "recent_similar_failures": recent_failures,
            "manual_only": manual_only,
            "manual_steps": self._build_manual_steps(
                goal=intent.goal,
                target_env=intent.target_env,
                error_message=error_message,
            ),
            "retry_action": {
                "type": "retry_execution",
                "intent_id": str(intent.id),
                "label": "一键重试",
            },
        }
        return recovery

    async def _recent_similar_failure_count(self, *, intent: ExecutionIntent) -> int:
        signature = self._goal_signature(intent.goal)
        result = await self._db.execute(
            select(ExecutionIntent)
            .where(
                ExecutionIntent.user_id == intent.user_id,
                ExecutionIntent.deleted_at.is_(None),
            )
            .order_by(desc(ExecutionIntent.created_at))
            .limit(12)
        )
        count = 0
        for candidate in result.scalars().all():
            if candidate.id == intent.id:
                continue
            if candidate.status not in {
                ExecutionIntentStatus.FAILED,
                ExecutionIntentStatus.TIMED_OUT,
                ExecutionIntentStatus.CANCELED,
            }:
                continue
            if intent.target_env != candidate.target_env:
                continue
            if self._goal_signature(candidate.goal) != signature:
                continue
            count += 1
        return count + 1

    @staticmethod
    def _goal_signature(goal: str) -> str:
        normalized = re.sub(r"\s+", " ", str(goal or "").strip().lower())
        normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff ]+", "", normalized)
        return normalized[:160]

    def _build_manual_steps(
        self,
        *,
        goal: str,
        target_env: ExecutionTargetEnv | None,
        error_message: str,
    ) -> list[dict[str, Any]]:
        env_label = {
            ExecutionTargetEnv.BROWSER: "浏览器",
            ExecutionTargetEnv.SHELL: "终端",
            ExecutionTargetEnv.API: "接口工具",
            ExecutionTargetEnv.DOCUMENT: "文档工具",
        }.get(target_env, "你的设备")
        steps = [
            {
                "title": f"打开{env_label}",
                "description": f"先在你的设备上打开对应环境，准备手动完成这条请求：{goal}",
            },
            {
                "title": "执行核心操作",
                "description": f"按原始目标逐步执行。如果遇到差异，以错误提示“{error_message or '环境异常'}”为排查线索。",
            },
            {
                "title": "核对结果",
                "description": "完成后回到 Sparkle，把观察到的结果贴回来，我可以继续帮你判断下一步。",
            },
        ]
        if target_env == ExecutionTargetEnv.BROWSER:
            steps.insert(
                1,
                {
                    "title": "检查网络与登录状态",
                    "description": "确认网页可访问、账号已登录，避免把环境问题误当成执行失败。",
                },
            )
        elif target_env == ExecutionTargetEnv.SHELL:
            steps.insert(
                1,
                {
                    "title": "确认工作目录",
                    "description": (
                        "进入目标项目目录后再执行命令，避免在错误目录里重复失败："
                        f"{self._config.default_workdir or '请切到正确仓库'}"
                    ),
                },
            )
        return steps

    def _infer_side_effects(self, goal: str) -> bool:
        side_effect_keywords = {"更新", "修改", "提交", "发送", "发布", "删除", "创建", "写入"}
        return any(keyword in goal for keyword in side_effect_keywords)

    def _apply_strategy_to_payload(
        self,
        *,
        strategy,
        instructions: list[str],
        policy: dict[str, Any],
        result_contract: dict[str, Any],
    ) -> None:
        configuration = strategy.configuration or {}
        for instruction in configuration.get("instruction_suffixes", []):
            if instruction not in instructions:
                instructions.append(str(instruction))

        artifact_types = configuration.get("artifact_types")
        if artifact_types:
            existing = list(result_contract.get("artifact_types") or [])
            for artifact_type in artifact_types:
                if artifact_type not in existing:
                    existing.append(artifact_type)
            result_contract["artifact_types"] = existing

        timeout_multiplier = configuration.get("timeout_multiplier")
        if timeout_multiplier:
            policy["timeout_multiplier"] = timeout_multiplier

    def _merge_dicts(self, *values: dict[str, Any] | None) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for value in values:
            if not value:
                continue
            for key, item in value.items():
                if isinstance(item, dict) and isinstance(merged.get(key), dict):
                    merged[key] = self._merge_dicts(merged.get(key), item)
                else:
                    merged[key] = item
        return merged

    def _build_evaluation_input(self, parsed: dict[str, Any]) -> dict[str, Any]:
        evaluation_input = dict(parsed)
        parsed_output = parsed.get("parsed_output")
        if isinstance(parsed_output, dict):
            for key, value in parsed_output.items():
                evaluation_input.setdefault(key, value)
        return evaluation_input

    async def _upsert_execution_record(
        self,
        *,
        intent: ExecutionIntent,
        raw_response: dict[str, Any],
        parsed: dict[str, Any],
        evaluation: TrustEvaluation,
    ) -> ExecutionRecord:
        result = await self._db.execute(select(ExecutionRecord).where(ExecutionRecord.execution_intent_id == intent.id))
        record = result.scalar_one_or_none()
        if record is None:
            record = ExecutionRecord(
                execution_intent_id=intent.id,
                user_id=intent.user_id,
                task_id=intent.task_id,
            )

        record.executor_type = intent.executor.value
        record.external_run_id = raw_response.get("id")
        enriched_raw_response = dict(raw_response)
        quality_warnings = self._result_validator.validate(
            parsed=parsed,
            result_contract=intent.result_contract or {},
        )
        sensitive_warning = self._sensitive_quality_warning(intent)
        if sensitive_warning is not None and all(
            str(item.get("code") or "") != str(sensitive_warning["code"])
            for item in quality_warnings
            if isinstance(item, dict)
        ):
            quality_warnings.append(sensitive_warning)
        enriched_raw_response["_sparkle_quality_warnings"] = quality_warnings
        record.raw_response = enriched_raw_response
        record.parsed_output = parsed.get("parsed_output")
        record.artifacts = parsed.get("artifacts", [])
        record.trust_level = evaluation.trust_level.value
        record.validation_passed = evaluation.validation_passed
        record.validation_total = evaluation.validation_total
        record.quality_score = evaluation.quality_score
        record.token_usage = parsed.get("token_usage")
        record.tool_calls_count = parsed.get("tool_calls_count", 0)
        record.error_category = None if parsed.get("success") else "execution_failed"
        record.error_message = parsed.get("error_message")
        record.execution_started_at = intent.dispatched_at
        record.execution_completed_at = _utcnow()
        self._db.add(record)
        await self._db.commit()
        await self._db.refresh(record)
        if record.token_usage:
            await self._preference_service.record_token_usage(
                user_id=intent.user_id,
                token_usage=record.token_usage,
            )
        return record

    async def _apply_execution_result(
        self,
        *,
        intent: ExecutionIntent,
        parsed: dict[str, Any],
        evaluation: TrustEvaluation,
        record: ExecutionRecord,
    ) -> None:
        old_status = intent.status
        now = _utcnow()

        intent.external_run_id = record.external_run_id
        intent.trust_level = evaluation.trust_level
        intent.completed_at = now

        if parsed.get("success"):
            intent.status = ExecutionIntentStatus.SUCCEEDED
        elif parsed.get("output"):
            intent.status = ExecutionIntentStatus.PARTIAL
        else:
            intent.status = ExecutionIntentStatus.FAILED
            intent.error_category = "execution_failed"
            intent.error_message = parsed.get("error_message")

        task = await self._get_user_task(task_id=intent.task_id, user_id=intent.user_id)
        task.execution_mode = intent.execution_mode.value

        if evaluation.can_update_task and parsed.get("success"):
            await self._complete_task_safely(task=task, intent=intent, parsed=parsed)
            if intent.plan_id:
                await self._create_plan_execution_record(intent=intent, parsed=parsed, evaluation=evaluation)
        else:
            self._db.add(task)

        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await event_bus.publish(
            EXECUTION_RESULT_INGESTED,
            {
                "event_type": EXECUTION_RESULT_INGESTED,
                "user_id": str(intent.user_id),
                "execution_intent_id": str(intent.id),
                "execution_record_id": str(record.id),
                "task_id": str(intent.task_id),
                "trust_level": evaluation.trust_level.value,
                "quality_score": evaluation.quality_score,
                "success": bool(parsed.get("success")),
                "error_category": intent.error_category,
                "timestamp": _utcnow().isoformat(),
            },
        )
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.COMPLETED if parsed.get("success") else BackgroundTaskStatus.FAILED,
            progress=1.0,
            progress_message="Execution completed" if parsed.get("success") else "Execution failed",
            result_data={
                "intent_id": str(intent.id),
                "trust_level": evaluation.trust_level.value,
                "status": intent.status.value,
            },
            error_message=intent.error_message,
        )
        await self._promote_next_queued_intent(user_id=intent.user_id)

    async def _complete_task_safely(self, *, task: Task, intent: ExecutionIntent, parsed: dict[str, Any]) -> None:
        task.status = TaskStatus.COMPLETED
        task.completed_at = _utcnow()
        task.actual_minutes = 0
        if not task.user_note:
            task.user_note = "Completed by delegated OpenClaw execution"
        self._db.add(task)

        if task.plan_id:
            from app.services.plan_service import PlanService
            from app.services.task_state_sync import TaskStateSyncService

            await self._db.commit()
            await self._db.refresh(task)
            await PlanService.update_progress(self._db, task.plan_id, task.user_id)
            sync_service = TaskStateSyncService(self._db, self._redis)
            await sync_service.on_task_completed(task, actual_minutes=task.actual_minutes)
        else:
            await self._db.commit()
            await self._db.refresh(task)

    async def _create_plan_execution_record(
        self,
        *,
        intent: ExecutionIntent,
        parsed: dict[str, Any],
        evaluation: TrustEvaluation,
    ) -> None:
        if not intent.plan_id:
            return

        validation_status = "passed" if parsed.get("success") else "partial" if parsed.get("output") else "failed"
        issues = list(evaluation.reasons) + list(evaluation.blocked_fields)
        await self._plan_record_service.create_record(
            plan_id=intent.plan_id,
            user_id=intent.user_id,
            validation_status=validation_status,
            quality_score=evaluation.quality_score,
            criteria_results={
                "trust_level": evaluation.trust_level.value,
                "validation_passed": evaluation.validation_passed,
                "validation_total": evaluation.validation_total,
            },
            tool_summary={
                "total": parsed.get("tool_calls_count", 0),
                "successful": parsed.get("tool_calls_count", 0) if parsed.get("success") else 0,
                "failed": 0 if parsed.get("success") else parsed.get("tool_calls_count", 0),
            },
            issues=issues,
        )

    async def _mark_intent_failure(
        self,
        *,
        intent: ExecutionIntent,
        status: ExecutionIntentStatus,
        error_category: str,
        error_message: str,
        audit_action: str = "failed",
    ) -> None:
        old_status = intent.status
        recovery = await self._build_error_recovery(
            intent=intent,
            error_category=error_category,
            error_message=error_message,
        )
        intent.status = status
        intent.error_category = error_category
        intent.error_message = error_message
        intent.completed_at = _utcnow()
        if recovery:
            policy = dict(intent.policy or {})
            policy["error_recovery"] = recovery
            intent.policy = policy
        self._db.add(intent)
        await self._db.commit()
        await self._db.refresh(intent)
        await self._publish_status_event(intent, old_status=old_status)
        await self._publish_monitor_progress(
            intent=intent,
            status=BackgroundTaskStatus.FAILED,
            progress=1.0,
            progress_message=error_message,
            error_message=error_message,
        )
        await self._record_execution_audit(
            intent=intent,
            action=audit_action,
            actor="system",
            details={
                "status": intent.status.value if intent.status else None,
                "error_category": error_category,
                "error_message": error_message,
                "error_recovery": recovery,
            },
        )
        degraded = self._record_failure(intent.user_id)
        if degraded or bool((recovery or {}).get("manual_only")):
            if not self._should_skip_task_sync(intent):
                task = await self._get_user_task(task_id=intent.task_id, user_id=intent.user_id)
                task.execution_mode = ExecutionMode.HUMAN.value
                self._db.add(task)
                await self._db.commit()
        await self._promote_next_queued_intent(user_id=intent.user_id)

    async def _publish_status_event(
        self,
        intent: ExecutionIntent,
        *,
        old_status: ExecutionIntentStatus | None,
    ) -> None:
        await event_bus.publish(
            EXECUTION_STATUS_CHANGED,
            {
                "event_type": EXECUTION_STATUS_CHANGED,
                "user_id": str(intent.user_id),
                "execution_intent_id": str(intent.id),
                "task_id": str(intent.task_id),
                "old_status": old_status.value if old_status else None,
                "new_status": intent.status.value,
                "trust_level": intent.trust_level.value if intent.trust_level else None,
                "timestamp": _utcnow().isoformat(),
            },
        )

    async def _publish_monitor_progress(
        self,
        *,
        intent: ExecutionIntent,
        status: BackgroundTaskStatus,
        progress: float,
        progress_message: str,
        result_data: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        try:
            await task_monitor_service.publish_progress(
                user_id=intent.user_id,
                task_type=BackgroundTaskType.AI_GENERATION,
                name=f"OpenClaw execution for task {intent.task_id}",
                status=status,
                progress=progress,
                progress_message=progress_message,
                external_task_id=str(intent.id),
                related_entity_id=intent.task_id,
                related_entity_type="task",
                result_data=result_data,
                error_message=error_message,
            )
        except Exception as exc:
            logger.warning("Failed to publish execution task monitor progress: {}", exc)

    @staticmethod
    def _terminal_statuses() -> set[ExecutionIntentStatus]:
        return {
            ExecutionIntentStatus.SUCCEEDED,
            ExecutionIntentStatus.PARTIAL,
            ExecutionIntentStatus.FAILED,
            ExecutionIntentStatus.CANCELED,
            ExecutionIntentStatus.TIMED_OUT,
            ExecutionIntentStatus.HANDED_BACK,
        }

    def get_degradation_snapshot(self) -> dict[str, Any]:
        self._cleanup_degradation_state()
        return {
            "degraded_user_count": len(self.__class__._degraded_users),
            "failure_counts": dict(self.__class__._failure_counts),
            "degraded_users": dict(self.__class__._degraded_users),
            "degradation_threshold": self.__class__._degradation_threshold,
            "degradation_window_seconds": self.__class__._degradation_window_seconds,
        }

    def _is_user_degraded(self, user_id: UUID) -> bool:
        self._cleanup_degradation_state()
        return str(user_id) in self.__class__._degraded_users

    def _record_failure(self, user_id: UUID) -> bool:
        self._cleanup_degradation_state()
        key = str(user_id)
        next_count = self.__class__._failure_counts.get(key, 0) + 1
        self.__class__._failure_counts[key] = next_count
        if next_count >= self.__class__._degradation_threshold:
            self.__class__._degraded_users[key] = time.time() + self.__class__._degradation_window_seconds
            return True
        return False

    def _clear_failure_state(self, user_id: UUID) -> None:
        key = str(user_id)
        self.__class__._failure_counts.pop(key, None)
        self.__class__._degraded_users.pop(key, None)

    def _cleanup_degradation_state(self) -> None:
        now = time.time()
        expired = [
            key
            for key, expires_at in self.__class__._degraded_users.items()
            if expires_at <= now
        ]
        for key in expired:
            self.__class__._degraded_users.pop(key, None)
            self.__class__._failure_counts.pop(key, None)
