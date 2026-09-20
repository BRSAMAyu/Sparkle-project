"""E-07: 三维自适应路由反馈环（quality / latency / cost）。

定位（红线）：这是 E-02 既有路由的**反馈维度扩展**，不是新决策真源——
- 冷启动（某候选样本 < MIN_SAMPLES）零介入，候选顺序 = E-02 既有策略输出；
- 只在**已组装好的候选链内部**做稳定重排（健康过滤之后），永不跨 tier 提升、
  永不把被策略/免费层钳制剔除的模型带回来；
- 有界内存：每模型一个 maxlen 滑窗，只记录 llm_router 已注册的 model_key。

打分（0..1，越高越好）：
- quality：显式质量信号（0..1，eval/judge 回流）EMA；无显式信号时取窗口成功率；
- latency_score = 1 - clamp(latency_ema / LATENCY_REF_MS, 0, 1)；
- cost_score   = 1 - clamp(cost_ema / COST_REF_PER_1K, 0, 1)（免费=1.0）；
- desirability = wq*quality + wl*latency_score + wc*cost_score（权重 settings 可调）。

滞回：重排后首位只有在与原首位分差 ≥ MARGIN 时才真正交换，防评分抖动引发
候选顺序抖动（与健康滞回同一防风暴原则）。
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

from loguru import logger

from app.config import settings
from app.core import routing_audit
from app.core.metrics import (
    LLM_ADAPTIVE_REORDER_TOTAL,
    LLM_ROUTER_QUALITY_SIGNAL,
)

_REGISTERED_MODELS_MAX = 1024  # 防御上限（注册表本身远小于此）


def _clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


@dataclass
class _Outcome:
    ts: float
    latency_ms: float
    success: bool
    quality: float | None  # 显式质量信号（None=无）
    cost_per_1k: float | None


@dataclass
class _ModelStats:
    outcomes: deque = field(default_factory=deque)


class AdaptiveRoutingEngine:
    """三维反馈状态与候选重排（线程安全、有界、冷启动不介入）。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stats: dict[str, _ModelStats] = {}

    # --------------------------------------------
    # 结果回流（由真实调用链 llm_service / fallback 调用）
    # --------------------------------------------

    def record_outcome(
        self,
        model_key: str,
        *,
        latency_ms: float,
        success: bool,
        quality: float | None = None,
        cost_per_1k: float | None = None,
    ) -> None:
        """记录一次真实调用结果。未注册的 model_key 拒收（内存有界）。"""
        from app.core.llm_router import llm_router

        if not model_key or model_key not in llm_router._available_models:
            return
        if quality is not None:
            quality = _clamp01(float(quality))
        with self._lock:
            if len(self._stats) >= _REGISTERED_MODELS_MAX:
                return
            stats = self._stats.get(model_key)
            if stats is None:
                stats = _ModelStats()
                self._stats[model_key] = stats
            stats.outcomes.append(
                _Outcome(
                    ts=time.monotonic(),
                    latency_ms=max(0.0, float(latency_ms)),
                    success=bool(success),
                    quality=quality,
                    cost_per_1k=cost_per_1k,
                )
            )
            window = self._window_size()
            while len(stats.outcomes) > window:
                stats.outcomes.popleft()

    def _window_size(self) -> int:
        try:
            return max(1, int(settings.ADAPTIVE_ROUTING_WINDOW))
        except Exception:
            return 64

    # --------------------------------------------
    # 打分
    # --------------------------------------------

    def sample_count(self, model_key: str) -> int:
        with self._lock:
            stats = self._stats.get(model_key)
            return len(stats.outcomes) if stats else 0

    def desirability(self, model_key: str) -> float | None:
        """三维合成分；样本不足返回 None（冷启动语义）。"""
        with self._lock:
            stats = self._stats.get(model_key)
            outcomes = list(stats.outcomes) if stats else []
        min_samples = max(1, int(getattr(settings, "ADAPTIVE_ROUTING_MIN_SAMPLES", 8)))
        if len(outcomes) < min_samples:
            return None

        try:
            wq = float(settings.ADAPTIVE_ROUTING_WEIGHT_QUALITY)
            wl = float(settings.ADAPTIVE_ROUTING_WEIGHT_LATENCY)
            wc = float(settings.ADAPTIVE_ROUTING_WEIGHT_COST)
        except Exception:
            wq, wl, wc = 0.5, 0.3, 0.2
        total_w = wq + wl + wc
        if total_w <= 0:
            wq, wl, wc, total_w = 0.5, 0.3, 0.2, 1.0
        wq, wl, wc = wq / total_w, wl / total_w, wc / total_w

        explicit = [o.quality for o in outcomes if o.quality is not None]
        if explicit:
            quality = sum(explicit) / len(explicit)
        else:
            quality = sum(1.0 for o in outcomes if o.success) / len(outcomes)

        latency_ema = 0.0
        for o in outcomes:
            latency_ema = o.latency_ms if latency_ema == 0.0 else 0.7 * latency_ema + 0.3 * o.latency_ms
        try:
            latency_ref = max(1.0, float(settings.ADAPTIVE_ROUTING_LATENCY_REF_MS))
        except Exception:
            latency_ref = 5000.0
        latency_score = 1.0 - _clamp01(latency_ema / latency_ref)

        cost_samples = [o.cost_per_1k for o in outcomes if o.cost_per_1k is not None]
        if cost_samples:
            cost_avg = sum(cost_samples) / len(cost_samples)
        else:
            cost_avg = 0.0
        try:
            cost_ref = max(1e-9, float(settings.ADAPTIVE_ROUTING_COST_REF_PER_1K))
        except Exception:
            cost_ref = 0.01
        cost_score = 1.0 - _clamp01(cost_avg / cost_ref)

        return _clamp01(wq * quality + wl * latency_score + wc * cost_score)

    # --------------------------------------------
    # 候选重排（唯一对外决策面；稳定、滞回、不跨层）
    # --------------------------------------------

    def reorder_candidates(self, candidates: list[str]) -> list[str]:
        """对已过滤候选链做可选稳定重排。返回新列表（可能原序）。"""
        if not candidates or not getattr(settings, "ADAPTIVE_ROUTING_ENABLED", True):
            return candidates
        if len(candidates) < 2:
            return candidates

        scored: list[tuple[str, float]] = []
        for key in candidates:
            score = self.desirability(key)
            if score is not None:
                scored.append((key, score))
        # 冷启动：可用分 < 2 → 无可比性，零介入
        if len(scored) < 2:
            return candidates

        original_head = candidates[0]
        best_key, best_score = max(scored, key=lambda pair: pair[1])
        try:
            margin = float(settings.ADAPTIVE_ROUTING_MARGIN)
        except Exception:
            margin = 0.05

        head_score = next((s for k, s in scored if k == original_head), None)
        if best_key != original_head and head_score is not None and best_score - head_score < margin:
            # 滞回：分差不足，保持原序（防抖）
            return candidates

        if best_key == original_head:
            return candidates

        score_map = dict(scored)
        # 稳定排序：有分的按分数降序，无分的保持原相对序在其后（冷启动模型仍可用）
        ranked = sorted(
            candidates,
            key=lambda k: (-(score_map[k]) if k in score_map else 0.0, candidates.index(k)),
        )
        # 无分模型永远排在有分模型之后
        ranked = [k for k in ranked if k in score_map] + [k for k in ranked if k not in score_map]
        if ranked != candidates:
            LLM_ADAPTIVE_REORDER_TOTAL.labels(trigger="desirability").inc()
            routing_audit.record(
                "adaptive",
                {
                    "subtype": "reorder",
                    "from_model_key": original_head,
                    "to_model_key": ranked[0],
                    "reason": (
                        f"adaptive quality/latency/cost reorder " f"(head {head_score:.3f} -> {best_score:.3f})"
                        if head_score is not None
                        else "adaptive quality/latency/cost reorder"
                    ),
                },
            )
            logger.info(
                f"[AdaptiveRouting] reorder head {original_head} -> {ranked[0]} "
                f"(samples>={getattr(settings, 'ADAPTIVE_ROUTING_MIN_SAMPLES', 8)})"
            )
        return ranked


def observe_quality_signal(model_key: str, provider: str, quality: float) -> None:
    """显式质量信号（0..1）进 Prometheus 时序（供 eval/judge 回流复用）。"""
    LLM_ROUTER_QUALITY_SIGNAL.labels(model_key=model_key, provider=provider).observe(_clamp01(float(quality)))


adaptive_routing_engine = AdaptiveRoutingEngine()
