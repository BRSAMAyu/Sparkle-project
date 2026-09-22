"""OTEL tracing bootstrap (HYGIENE-2).

设计要点（2026-09 债务清理）：

1. **trace export 默认关闭，除非显式配置 collector**。
   旧实现把 endpoint 硬编码默认到 ``http://localhost:4317``，本机没有 OTEL
   collector 时 BatchSpanProcessor 会持续刷
   ``Failed to export traces to localhost:4317 ... UNAVAILABLE`` + retry 噪音。
   现在只有显式设置 ``OTEL_EXPORTER_OTLP_ENDPOINT`` 的环境（docker-compose /
   k8s / prod 全部都设置了）才挂 OTLP exporter；未设置 = 无处可导出 = 不挂。
   **span 采集语义保持不变**：TracerProvider 照常创建并 set 为全局 provider，
   业务代码的 start_span / span attributes / trace spine（orchestrator 的
   O-02 trace_id 取自真实 span context）不受影响，只是不再向不存在的
   collector 做无效导出。

2. **标准开关语义保留**：
   - ``OTEL_SDK_DISABLED=true``（OTel 官方规范开关，SDK 1.40 原生支持，
     生效时 get_tracer 返回 NoOpTracer）→ 同时不挂 exporter；
   - ``OTEL_TRACES_EXPORTER=none``（OTel 规范信号级开关）→ 不挂 exporter。

3. **instrumentation 跨 task detach 噪音抑制**。
   opentelemetry-instrumentation-grpc(aio) 在不同 task 里 detach 上下文时，
   ``opentelemetry.context.detach`` 会打
   ``Failed to detach context`` + ``ValueError: Token ... was created in a
   different Context``（opentelemetry-contextvars 的已知库层问题，对业务
   无影响）。按"不改库、只在应用侧滤噪"原则，模块导入时给
   ``opentelemetry.context`` logger 挂一个精确匹配该 ValueError 的日志
   过滤器；其它 detach 失败仍正常记录。
"""

import logging
import os
from typing import Mapping

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Detach 噪音指纹：opentelemetry.context.__init__.detach 的
# `logger.exception("Failed to detach context")` + contextvars reset 的
# ValueError("... was created in a different Context")。
_DETACH_NOISE_LOGGER = "opentelemetry.context"
_DETACH_NOISE_MSG = "Failed to detach context"
_DETACH_NOISE_EXC_MARKER = "was created in a different Context"


class OtelCrossContextDetachNoiseFilter(logging.Filter):
    """只吞 instrumentation 跨 task detach 的已知良性 ValueError 噪音。

    匹配条件（三条全中才过滤，其余日志一律放行）：
    - logger 名 == ``opentelemetry.context``（由 addFilter 的挂载点保证）；
    - message == ``Failed to detach context``；
    - exc_info 是带 "was created in a different Context" 的 ValueError。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.getMessage() != _DETACH_NOISE_MSG:
            return True
        exc = record.exc_info[1] if record.exc_info else None
        if isinstance(exc, ValueError) and _DETACH_NOISE_EXC_MARKER in str(exc):
            return False
        return True


def suppress_otel_detach_noise() -> None:
    """给 otel context logger 挂 detach 噪音过滤器（幂等）。"""
    logger = logging.getLogger(_DETACH_NOISE_LOGGER)
    for existing in logger.filters:
        if isinstance(existing, OtelCrossContextDetachNoiseFilter):
            return
    logger.addFilter(OtelCrossContextDetachNoiseFilter())


def resolve_export_settings(
    env: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """纯函数：解析 OTEL 环境变量，决定是否挂 OTLP trace exporter。

    - ``OTEL_EXPORTER_OTLP_ENDPOINT`` 未设置/为空 → export 关闭（默认关，
      本机无 collector，避免 localhost:4317 UNAVAILABLE 刷屏）；
    - ``OTEL_SDK_DISABLED=true`` → export 关闭（SDK 层同时整体禁用）；
    - ``OTEL_TRACES_EXPORTER=none`` → export 关闭；
    - 以上都不满足（显式配了 endpoint）→ export 开启，endpoint/insecure
      行为与旧实现完全一致。
    """
    env = os.environ if env is None else env
    endpoint = (env.get("OTEL_EXPORTER_OTLP_ENDPOINT") or "").strip()
    traces_exporter = (env.get("OTEL_TRACES_EXPORTER") or "").strip().lower()
    sdk_disabled = (env.get("OTEL_SDK_DISABLED") or "").strip().lower() == "true"
    insecure = (env.get("OTLP_INSECURE") or "false").strip().lower() == "true"
    export_enabled = bool(endpoint) and not sdk_disabled and traces_exporter != "none"
    return {
        "export_enabled": export_enabled,
        "endpoint": endpoint,
        "insecure": insecure,
    }


suppress_otel_detach_noise()

# Configure Trace Provider
resource = Resource.create({
    "service.name": "sparkle-backend",
    "service.namespace": "sparkle",
    "deployment.environment": os.getenv("ENVIRONMENT", "development")
})

tracer_provider = TracerProvider(resource=resource)

# Configure OTLP Exporter (connects to Jaeger/Tempo via OTEL Collector).
# Only attach when a collector endpoint is explicitly configured — see
# resolve_export_settings() for the default-off rationale (HYGIENE-2).
_export_settings = resolve_export_settings()
TRACE_EXPORT_ENABLED = _export_settings["export_enabled"]

if TRACE_EXPORT_ENABLED:
    otlp_exporter = OTLPSpanExporter(
        endpoint=str(_export_settings["endpoint"]),
        insecure=bool(_export_settings["insecure"]),
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Set global Trace Provider
trace.set_tracer_provider(tracer_provider)

# Get a tracer for usage in application code
tracer = trace.get_tracer("sparkle.backend")

def get_tracer(name: str):
    """Helper to get a named tracer"""
    return trace.get_tracer(name)
