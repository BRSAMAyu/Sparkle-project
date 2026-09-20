"""E-07: 路由决策审计 — 每次路由/回退/调用结果留痕，切换原因可查。

设计约束：
- 纯内存有界 ring（deque maxlen），进程生命周期，不落库不无界增长；
- 只追加、线程安全；查询返回快照 dict（不可变视图）；
- kind 封闭集：selection（路由决策）/ fallback（回退切换）/ adaptive（三维反馈重排）/
  outcome（调用结果回流）。
  这是 AI_ROUTING_LATENCY.md「Observability: requested/actual provider+model/tier、
  reason、fallback、TTFT、total latency、cost、error、quality eval」的落地。
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

_RING_SIZE = 512

_KINDS = ("selection", "fallback", "adaptive", "outcome")

_records: deque[dict[str, Any]] = deque(maxlen=_RING_SIZE)
_seq: list[int] = [0]
_lock = threading.Lock()


def record(kind: str, payload: dict[str, Any]) -> None:
    """追加一条审计记录（kind 之外的值拒绝，防滥用撑爆标签面）。"""
    if kind not in _KINDS:
        raise ValueError(f"unknown routing audit kind: {kind!r}")
    with _lock:
        _seq[0] += 1
        _records.append(
            {
                "seq": _seq[0],
                "ts": time.time(),
                "kind": kind,
                **payload,
            }
        )


def recent(*, kind: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """按序返回最近记录（新在后）；kind 过滤可选。"""
    if limit <= 0:
        return []
    with _lock:
        snapshot = list(_records)
    if kind is not None:
        snapshot = [r for r in snapshot if r.get("kind") == kind]
    return snapshot[-limit:]


def clear() -> None:
    """清空审计（仅测试使用）。"""
    with _lock:
        _records.clear()


def size() -> int:
    with _lock:
        return len(_records)
