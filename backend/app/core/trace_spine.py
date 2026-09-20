"""O-02 End-to-End Trace Spine — 统一 trace_id/span tags（metadata-only）。

把一次聊天请求（UI→Gateway→Context→Aurora→LLM→Run→Outcome）在引擎侧的
关键阶段以**单行 JSON span**写入日志（``TRACE_SPINE {...}``），全部 span
共享同一个 trace_id（优先网关 x-trace-id，缺失时回退引擎 OTel span id），
使任一黄金旅程（GJ）可以用一个 trace_id 还原：关键阶段时间线、actual
model、receipt 关联、latency/cost/context 关联。

设计约束（不重建观测体系）：
- 复用 loguru 结构化输出（生产 serialize=True 即 JSON）；查询脚本
  ``scripts/devtools/trace_timeline.py`` 直接消费。
- 复用 C-08 的 metadata-only 红线：tag 值只允许标量 id/数量/时长/短哈希；
  任何非标量（dict/list/长文本）一律降级为 ``<len=N,hash=h12>`` 指纹，
  正文不可还原。
- 观测永不阻断主链：所有发射路径吞异常，元数据缺省降级为空。
"""

from __future__ import annotations

import hashlib
import json
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from loguru import logger

TRACE_SPINE_MARKER = "TRACE_SPINE"

#: tag 值字符串上限：id/短标签（≤48 字符）原样放行；更长的字符串一律
#: 降级为 长度+短哈希 指纹——正文不可借道 tag 字段进日志（PII/Memory 红线）。
_MAX_TAG_VALUE_LEN = 48
_MAX_TAG_KEY_LEN = 48
_MAX_TAGS_PER_SPAN = 32

_spine_var: ContextVar["SpineRecorder | None"] = ContextVar("trace_spine_recorder", default=None)


def fingerprint(text: str) -> tuple[int, str]:
    """正文 → (长度, 12 位短哈希)。与 C-08 ``content_fingerprint`` 同算法。

    身份可比对、正文不可还原（隐私红线）。本地实现以保持 core 层不反向
    依赖 orchestration 层。
    """
    payload = str(text or "")
    return len(payload), hashlib.sha256(payload.encode("utf-8", "ignore")).hexdigest()[:12]


def _clamp_str(value: str, limit: int) -> str:
    text = str(value)
    return text if len(text) <= limit else text[:limit] + "…"


def sanitize_tags(tags: dict[str, Any] | None) -> dict[str, Any]:
    """tag 收敛：只放行标量（id/数量/布尔/短字符串），其余降级为指纹。

    - 标量（bool/int/float）原样保留；None 丢弃。
    - str ≤ ``_MAX_TAG_VALUE_LEN`` 钳制放行；更长一律指纹化（正文不可还原）。
    - list/tuple/dict 等结构 → ``<len=N,hash=h12>`` 指纹。
    - key 钳制 + span 级 tag 数量封顶（防基数/体积膨胀）。
    """
    if not isinstance(tags, dict):
        return {}
    clean: dict[str, Any] = {}
    for raw_key, raw_value in list(tags.items())[:_MAX_TAGS_PER_SPAN]:
        key = _clamp_str(str(raw_key or ""), _MAX_TAG_KEY_LEN)
        if not key or raw_value is None:
            continue
        if isinstance(raw_value, bool):
            clean[key] = raw_value
        elif isinstance(raw_value, (int, float)):
            clean[key] = raw_value
        elif isinstance(raw_value, str):
            if len(raw_value) <= _MAX_TAG_VALUE_LEN:
                clean[key] = raw_value
            else:
                length, digest = fingerprint(raw_value)
                clean[key] = f"<len={length},hash={digest}>"
        else:
            try:
                blob = json.dumps(raw_value, ensure_ascii=False, default=str)
            except Exception:
                blob = str(raw_value)
            length, digest = fingerprint(blob)
            clean[key] = f"<len={length},hash={digest}>"
    return clean


def emit_span(
    stage: str,
    *,
    trace_id: str,
    status: str = "ok",
    duration_ms: float | None = None,
    tags: dict[str, Any] | None = None,
) -> None:
    """发射单行 TRACE_SPINE JSON（日志面；失败绝不抛错）。"""
    try:
        payload: dict[str, Any] = {
            "marker": TRACE_SPINE_MARKER,
            "ts": time.time(),
            "trace_id": _clamp_str(str(trace_id or ""), 128),
            "stage": _clamp_str(str(stage or "unknown"), 64),
            "status": _clamp_str(str(status or "ok"), 24),
        }
        if duration_ms is not None:
            payload["duration_ms"] = round(max(float(duration_ms), 0.0), 2)
        clean_tags = sanitize_tags(tags)
        if clean_tags:
            payload["tags"] = clean_tags
        # 消息体 = "TRACE_SPINE {json}"：前缀是解析锚点（JSON 内的 marker
        # 字段是冗余校验位，find() 必须先命中前缀）。
        logger.info("{} {}", TRACE_SPINE_MARKER, json.dumps(payload, ensure_ascii=False, default=str))
    except Exception:  # pragma: no cover - observability must never break the chain
        pass


def current_trace_id() -> str:
    """当前任务绑定的 spine trace_id（无绑定返回空串）。"""
    recorder = _spine_var.get()
    return recorder.trace_id if recorder is not None else ""


class SpineRecorder:
    """一次请求的 stage 串行发射器：``step()`` 自动计算与上一阶段的间隔。

    用于 ``process_stream`` 这类顺序大流程——无需包裹缩进，在既有
    ``latency_probe.mark`` 落点旁补一行 ``recorder.step(...)`` 即可。
    """

    def __init__(
        self,
        *,
        trace_id: str,
        request_id: str = "",
        session_id: str = "",
        user_id: str = "",
    ) -> None:
        self.trace_id = str(trace_id or "")
        self.request_id = _clamp_str(str(request_id or ""), 128)
        self.session_id = _clamp_str(str(session_id or ""), 128)
        # PII 红线：user_id 只留 8 位前缀（引擎日志既有惯例 user_id[:8]）。
        self.user_hint = _clamp_str(str(user_id or "")[:8], 16)
        self._t0 = time.perf_counter()
        self._last = self._t0
        self._stage_count = 0
        self._error = False

    @property
    def elapsed_ms(self) -> float:
        return max((time.perf_counter() - self._t0) * 1000.0, 0.0)

    def _base_tags(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "user_hint": self.user_hint,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }

    def step(self, stage: str, *, status: str = "ok", **tags: Any) -> None:
        """发射一个阶段 span（duration = 距上一 step 的间隔）。"""
        if self._error:
            status = "after_error"
        now = time.perf_counter()
        duration_ms = max((now - self._last) * 1000.0, 0.0)
        self._last = now
        self._stage_count += 1
        emit_span(
            stage,
            trace_id=self.trace_id,
            status=status,
            duration_ms=duration_ms,
            tags={**self._base_tags(), **tags},
        )

    def span(self, stage: str, *, status: str = "ok", duration_ms: float, **tags: Any) -> None:
        """发射一个自带时长的 span（用于嵌套层如 LLM 调用内部计时）。"""
        self._stage_count += 1
        emit_span(
            stage,
            trace_id=self.trace_id,
            status=status,
            duration_ms=duration_ms,
            tags={**self._base_tags(), **tags},
        )

    def finish(self, *, status: str = "ok", **tags: Any) -> None:
        """收尾 span：携带总时长与阶段数。"""
        if status != "ok":
            self._error = True
        emit_span(
            "finish",
            trace_id=self.trace_id,
            status=status,
            duration_ms=self.elapsed_ms,
            tags={
                **self._base_tags(),
                "stage_count": self._stage_count,
                **tags,
            },
        )

    # -- contextvar 绑定 ----------------------------------------------------

    def bind(self) -> None:
        """把 recorder 绑定到当前任务 context（不 reset——async generator
        跨上下文 yield 时 token reset 可能跨 Context 抛错；绑定幂等且任务
        隔离，泄漏面为一个引用）。"""
        _spine_var.set(self)


@contextmanager
def bind_spine(recorder: SpineRecorder) -> Iterator[SpineRecorder]:
    """普通（非 async generator）上下文的绑定：进入绑定、退出还原。"""
    token = _spine_var.set(recorder)
    try:
        yield recorder
    finally:
        _spine_var.reset(token)


def current_recorder() -> SpineRecorder | None:
    return _spine_var.get()
