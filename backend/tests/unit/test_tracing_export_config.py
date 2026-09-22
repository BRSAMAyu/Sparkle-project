"""HYGIENE-2：otel trace export 默认关闭 + instrumentation detach 噪音过滤的单元测试。

- 无 collector（未配置 OTEL_EXPORTER_OTLP_ENDPOINT）→ 不挂 OTLP exporter，
  也不再有 ``Failed to export traces to localhost:4317`` 刷屏；
- 显式配置 endpoint 的环境（docker-compose/k8s/prod）行为不变；
- span 采集语义保持：TracerProvider 真实生效，span 有真实 trace_id；
- detach 噪音（库层已知问题）按日志过滤器精确抑制。
"""

import logging
import sys

import pytest

from app.core import tracing
from app.core.tracing import (
    OtelCrossContextDetachNoiseFilter,
    resolve_export_settings,
    suppress_otel_detach_noise,
)

# ---------------------------------------------------------------------------
# resolve_export_settings（纯函数决策）
# ---------------------------------------------------------------------------


class TestResolveExportSettings:
    def test_no_env_defaults_to_disabled(self):
        # 本机无 collector：默认 localhost:4317 的无效导出必须关闭（旧债噪音源）
        settings = resolve_export_settings(env={})
        assert settings["export_enabled"] is False

    def test_empty_endpoint_disabled(self):
        settings = resolve_export_settings(env={"OTEL_EXPORTER_OTLP_ENDPOINT": "   "})
        assert settings["export_enabled"] is False

    def test_explicit_endpoint_enabled(self):
        # 有 collector 的环境不受影响：显式 endpoint → 照常导出
        settings = resolve_export_settings(env={"OTEL_EXPORTER_OTLP_ENDPOINT": "http://sparkle_tempo:4317"})
        assert settings["export_enabled"] is True
        assert settings["endpoint"] == "http://sparkle_tempo:4317"
        assert settings["insecure"] is False

    def test_sdk_disabled_overrides_endpoint(self):
        # OTel 规范标准开关 OTEL_SDK_DISABLED=true 优先
        settings = resolve_export_settings(
            env={
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://tempo:4317",
                "OTEL_SDK_DISABLED": "true",
            }
        )
        assert settings["export_enabled"] is False

    def test_traces_exporter_none_overrides_endpoint(self):
        # OTel 规范信号级开关 OTEL_TRACES_EXPORTER=none 优先
        settings = resolve_export_settings(
            env={
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://tempo:4317",
                "OTEL_TRACES_EXPORTER": "none",
            }
        )
        assert settings["export_enabled"] is False

    def test_otlp_insecure_parsing(self):
        settings = resolve_export_settings(
            env={
                "OTEL_EXPORTER_OTLP_ENDPOINT": "http://tempo:4317",
                "OTLP_INSECURE": "TRUE",
            }
        )
        assert settings["insecure"] is True


# ---------------------------------------------------------------------------
# 活动模块状态（import 期副作用）：span 语义保留 + 无 collector 不挂 exporter
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.modules.get("app.core.tracing") is None, reason="tracing module not importable")
class TestLiveTracingModule:
    def test_span_semantics_preserved_without_export(self):
        """红线：默认关 export 不卸业务 trace 语义——span 真实、trace_id 可用。"""
        span = tracing.tracer.start_span("hygiene2.semantic_check")
        try:
            span.set_attribute("hygiene2", True)
            span_context = span.get_span_context()
            # orchestrator O-02 trace spine 依赖真实 span context 的 trace_id
            assert span_context.trace_id != 0
            assert span.is_recording() is True
        finally:
            span.end()

    def test_no_export_error_log_without_collector(self, caplog):
        """红线（日志断言）：无 collector 时结束 span 不产生 export 失败日志。"""
        exporter_loggers = [
            "opentelemetry.exporter.otlp.proto.grpc.exporter",
            "opentelemetry.exporter.otlp.proto.grpc._log_exporter",
            "opentelemetry.sdk.trace.export",
        ]
        with caplog.at_level(logging.WARNING, logger="opentelemetry"):
            span = tracing.tracer.start_span("hygiene2.no_export_noise")
            span.end()
        noise = [
            r
            for r in caplog.records
            if r.name in exporter_loggers
            and ("Failed to export" in r.getMessage() or "Transient error" in r.getMessage())
        ]
        assert noise == []

    def test_detach_noise_filter_installed_once(self):
        suppress_otel_detach_noise()
        suppress_otel_detach_noise()  # 幂等：重复调用不叠加
        filters = [
            f
            for f in logging.getLogger("opentelemetry.context").filters
            if isinstance(f, OtelCrossContextDetachNoiseFilter)
        ]
        assert len(filters) == 1


# ---------------------------------------------------------------------------
# detach 噪音过滤器：只吞已知良性 ValueError，其余日志照常
# ---------------------------------------------------------------------------


def _make_detach_record(exc: BaseException | None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="opentelemetry.context",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Failed to detach context",
        args=(),
        exc_info=(type(exc), exc, None) if exc else None,
    )
    return record


class TestDetachNoiseFilter:
    FILTER = OtelCrossContextDetachNoiseFilter()

    def test_suppresses_known_cross_context_valueerror(self):
        # 与 /tmp/sparkle_grpc.log 中观测到的库层噪音完全同形
        exc = ValueError(
            "<Token var=<ContextVar name='current_context' default={} "
            "at 0x10b11c0e0> at 0x127f35c80> was created in a different Context"
        )
        assert self.FILTER.filter(_make_detach_record(exc)) is False

    def test_passes_other_detach_exceptions(self):
        assert self.FILTER.filter(_make_detach_record(RuntimeError("boom"))) is True

    def test_passes_valueerror_without_marker(self):
        assert self.FILTER.filter(_make_detach_record(ValueError("other reason"))) is True

    def test_passes_non_detach_messages(self):
        record = logging.LogRecord(
            name="opentelemetry.context",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg="some other otel log",
            args=(),
            exc_info=None,
        )
        assert self.FILTER.filter(record) is True
