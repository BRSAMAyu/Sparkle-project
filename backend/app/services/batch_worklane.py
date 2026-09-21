"""
Service: batch-ai
Phase: execute
Stage: E-06 Async Batch Cognitive Worklane

异步批处理认知车道（E-06）：把不需实时的 reflection / profile aggregation /
analytics 三类认知负载标记为 batch-eligible，并统一路由到 MiniMax/glm_batch
执行面，降低前台成本。

设计约束（卡面 + AI_ROUTING_LATENCY.md）：
- **不重建 E-02 路由真源**：模型解析直接走 ``llm_router.select_model(force_tier=
  GLM_BATCH)``，MiniMax M3 优先（glm_batch tier 链首，key 未配置时自然落回
  glm_* 原链，无 key 环境零行为变化）。batch 车道是既有路由的 batch 扩展车道。
- **前台零挤占**：车道内并发受两层隔离钳制——(1) 提供商池沿用
  ``llm_concurrency`` 的 minimax / zhipu_coding 池（与前台 deepseek/dashscope/
  xiaomi/zhipu 普通池互不相交）；(2) 车道级 ``BATCH_LANE_MAX_CONCURRENCY``
  信号量跨三类工作负载总闸，防止 batch 风暴回灌。预算核算走独立的
  ``CostCategory.GLM_BATCH`` 预算桶，不占前台 LLM 预算，也不被前台预算熔断
  误伤（各自独立 check）。
- **失败语义**：有界重试（指数退避，BATCH_LANE_MAX_ATTEMPTS），重试耗尽进入
  终态 ``dead_letter``（指标 + 死信登记 + 结构化日志），不无限循环、不静默丢。
- **幂等（重放恰一次）**：每个车道执行必须携带 idempotency_key；claim 键
  （SET NX + TTL）防并发双执行，结果键（TTL > freshness SLA）保证同一 key
  的 LLM 调用恰好执行一次，后续重放返回已存结果（replayed=True）。
- **新鲜度**：结果带 completed_at/model/model_version/source；``is_result_stale``
  按 kind 的 SLA 拒绝过期结果；``should_apply`` 保证 batch 老结果绝不覆盖
  更新的 explicit correction（目标记录更新时间晚于 batch 开始即拒绝）。

全部执行路径零真实 LLM 依赖即可测试（chat executor 可注入 mock）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Awaitable, Callable

from loguru import logger

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.business_metrics import (
    BATCH_LANE_BUDGET_REJECTED_TOTAL,
    BATCH_LANE_COST_USD_TOTAL,
    BATCH_LANE_DEADLETTER_TOTAL,
    BATCH_LANE_DISABLED_TOTAL,
    BATCH_LANE_DISPATCH_TOTAL,
    BATCH_LANE_DUPLICATE_SKIPPED_TOTAL,
    BATCH_LANE_INFLIGHT,
    BATCH_LANE_LATENCY,
    BATCH_LANE_RETRIES_TOTAL,
    BATCH_LANE_STALE_REJECTED_TOTAL,
)
from app.core.cost_controller import CostCategory, get_budget_breaker
from app.core.llm_router import LLMSelection, llm_router


class BatchWorkloadKind(StrEnum):
    """batch-eligible 认知工作负载类别（E-06 三类）。"""

    REFLECTION = "reflection"
    PROFILE_AGGREGATION = "profile_aggregation"
    ANALYTICS = "analytics"


class BatchLaneOutcome(StrEnum):
    """车道执行终态。"""

    COMPLETED = "completed"                # 本进程内成功执行
    REPLAYED = "replayed"                  # 幂等命中，返回已存结果（不重执行）
    DUPLICATE_SKIPPED = "duplicate_in_flight"  # 并发同 key 去重（另一执行在途）
    DISABLED = "disabled"                  # 车道未启用（调用方自行走前台兜底）
    BUDGET_EXHAUSTED = "budget_exhausted"  # batch 独立预算耗尽（不影响前台）
    DEAD_LETTER = "dead_letter"            # 有界重试耗尽，终态登记


# 每类的路由画像（role/task 选取影响 GLM_BATCH 链内的 fallback 顺序画像，
# tier 恒为 GLM_BATCH——真源仍在 llm_router，不在此重建）。
_KIND_ROUTE_PROFILE: dict[BatchWorkloadKind, dict[str, Any]] = {
    BatchWorkloadKind.REFLECTION: {
        "agent_role": AgentRole.DEEP_ANALYST,
        "task_type": TaskType.STANDARD_RESPONSE,
        "reasoning_mode": "balanced",
    },
    BatchWorkloadKind.PROFILE_AGGREGATION: {
        "agent_role": AgentRole.DEEP_ANALYST,
        "task_type": TaskType.STANDARD_RESPONSE,
        "reasoning_mode": "balanced",
    },
    BatchWorkloadKind.ANALYTICS: {
        "agent_role": AgentRole.ERROR_ANALYST,
        "task_type": TaskType.STANDARD_RESPONSE,
        "reasoning_mode": "fast",
    },
}

_KIND_ENABLED_SETTINGS = {
    BatchWorkloadKind.REFLECTION: "BATCH_LANE_ENABLED_REFLECTION",
    BatchWorkloadKind.PROFILE_AGGREGATION: "BATCH_LANE_ENABLED_PROFILE_AGGREGATION",
    BatchWorkloadKind.ANALYTICS: "BATCH_LANE_ENABLED_ANALYTICS",
}

_KIND_SLA_SETTINGS = {
    BatchWorkloadKind.REFLECTION: "BATCH_LANE_FRESHNESS_SLA_REFLECTION_SECONDS",
    BatchWorkloadKind.PROFILE_AGGREGATION: "BATCH_LANE_FRESHNESS_SLA_PROFILE_AGGREGATION_SECONDS",
    BatchWorkloadKind.ANALYTICS: "BATCH_LANE_FRESHNESS_SLA_ANALYTICS_SECONDS",
}

_RESULT_KEY_PREFIX = "batch_worklane:result:"
_CLAIM_KEY_PREFIX = "batch_worklane:claim:"
_DEADLETTER_LIST_KEY = "batch_worklane:dead_letters"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def default_idempotency_key(kind: BatchWorkloadKind, payload: Any) -> str:
    """由 kind + 稳定序列化 payload 派生幂等键（无业务键时的兜底）。"""
    try:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:  # noqa: BLE001 — 序列化失败退化为 repr
        raw = repr(payload)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{kind.value}:{digest}"


@dataclass
class BatchLaneResult:
    """车道执行结果（自带 model/version/source 溯源，卡面 Work#2）。"""

    kind: BatchWorkloadKind
    outcome: BatchLaneOutcome
    idempotency_key: str
    content: str | None = None
    model_key: str = ""
    model: str = ""            # 具体模型名（version 语义），如 MiniMax-M3
    provider: str = ""         # provider 值（minimax/zhipu）
    source: str = "batch_worklane"
    attempts: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    replayed: bool = False
    completed_at: str = field(default_factory=lambda: _utcnow().isoformat())
    error: str | None = None
    reason: str | None = None

    def provenance(self) -> dict[str, Any]:
        """溯源字段（随结果落库/落缓存时携带）。"""
        return {
            "model_key": self.model_key,
            "model": self.model,
            "provider": self.provider,
            "source": self.source,
            "completed_at": self.completed_at,
            "attempts": self.attempts,
        }


class BatchLaneChatClient:
    """车道内 LLM 客户端适配器。

    暴露与 ``LLMService.chat`` 兼容的 ``chat(messages, temperature=...)`` 签名，
    可注入 ReflectionAgent 等 generator_llm 插槽，把该次调用锁进 batch 车道
    （GLM_BATCH tier + 隔离并发 + 独立预算 + 幂等）。
    """

    def __init__(self, kind: BatchWorkloadKind, lane: "BatchWorklaneService"):
        self._kind = kind
        self._lane = lane

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        *,
        idempotency_key: str | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        key = idempotency_key or default_idempotency_key(self._kind, messages)
        result = await self._lane.run_chat(
            self._kind,
            messages,
            idempotency_key=key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if result.outcome in (BatchLaneOutcome.COMPLETED, BatchLaneOutcome.REPLAYED):
            return result.content or ""
        raise RuntimeError(
            f"batch_worklane[{self._kind.value}] outcome={result.outcome.value} "
            f"reason={result.reason} error={result.error}"
        )


class BatchWorklaneService:
    """E-06 异步批处理认知车道服务。"""

    def __init__(self, store: Any | None = None) -> None:
        # store 可注入（测试用 FakeRedis）；None 时惰性取 cache_service.redis
        self._store_override = store
        self._lane_semaphore: asyncio.Semaphore | None = None
        self._semaphore_loop: asyncio.AbstractEventLoop | None = None
        self._providers: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 启用与路由解析
    # ------------------------------------------------------------------

    def enabled(self, kind: BatchWorkloadKind) -> bool:
        if not bool(getattr(settings, "BATCH_LANE_ENABLED", True)):
            return False
        return bool(getattr(settings, _KIND_ENABLED_SETTINGS[kind], True))

    def lane_available(self, kind: BatchWorkloadKind) -> tuple[bool, str | None]:
        """车道可用性：GLM_BATCH 链解析出的模型必须带非空 api_key。

        无 key 环境（本地 dev/测试）解析出的 glm_* 条目同样无凭据，此时车道
        视为不可用并让调用方走前台兜底——与 E-06 之前行为一致（LLMService
        demo/降级模式），保证零 key 环境零行为变化。
        """
        selection = self.resolve_selection(kind)
        if not (selection.config.api_key or "").strip():
            return False, "no_provider_credentials"
        return True, None

    def resolve_selection(self, kind: BatchWorkloadKind) -> LLMSelection:
        """经 E-02 路由真源解析 GLM_BATCH 车道模型（MiniMax 优先）。"""
        profile = _KIND_ROUTE_PROFILE[kind]
        return llm_router.select_model(
            profile["agent_role"],
            task_type=profile["task_type"],
            force_tier=ModelTier.GLM_BATCH,
            reasoning_mode=profile["reasoning_mode"],
        )

    def resolve_batch_model_key(self, kind: BatchWorkloadKind) -> str:
        return self.resolve_selection(kind).model_key

    def sla_seconds(self, kind: BatchWorkloadKind) -> int:
        return max(1, int(getattr(settings, _KIND_SLA_SETTINGS[kind], 86400)))

    def chat_client(self, kind: BatchWorkloadKind) -> BatchLaneChatClient:
        return BatchLaneChatClient(kind, self)

    def mark_enqueued(self, kind: BatchWorkloadKind) -> None:
        """任务投递进 glm_batch 车道队列时的计数点（队列可观测）。"""
        BATCH_LANE_DISPATCH_TOTAL.labels(kind=kind.value, outcome="enqueued").inc()

    # ------------------------------------------------------------------
    # 新鲜度 / explicit-correction 守卫
    # ------------------------------------------------------------------

    def is_result_stale(
        self,
        kind: BatchWorkloadKind,
        completed_at: datetime | str | None,
        *,
        now: datetime | None = None,
    ) -> bool:
        """batch 结果超过 kind 的 freshness SLA 即视为 stale（消费方应拒绝）。"""
        if completed_at is None:
            return True
        if isinstance(completed_at, str):
            try:
                completed_at = datetime.fromisoformat(completed_at)
            except ValueError:
                return True
        now = now or _utcnow()
        age = (now - completed_at).total_seconds()
        return age > self.sla_seconds(kind)

    def should_apply(
        self,
        kind: BatchWorkloadKind,
        *,
        batch_started_at: datetime,
        target_updated_at: datetime | str | None,
    ) -> tuple[bool, str | None]:
        """batch 结果应用守卫：目标记录在 batch 开始后被显式更新（explicit
        correction）时拒绝应用，绝不让 batch 老结果覆盖新修正。"""
        if target_updated_at is None:
            return True, None
        if isinstance(target_updated_at, str):
            try:
                target_updated_at = datetime.fromisoformat(target_updated_at)
            except ValueError:
                return True, None
        if target_updated_at > batch_started_at:
            BATCH_LANE_STALE_REJECTED_TOTAL.labels(kind=kind.value).inc()
            return False, "newer_explicit_correction"
        return True, None

    # ------------------------------------------------------------------
    # 执行面
    # ------------------------------------------------------------------

    def _get_lane_semaphore(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        limit = max(1, int(getattr(settings, "BATCH_LANE_MAX_CONCURRENCY", 4)))
        if self._lane_semaphore is None or self._semaphore_loop is not loop:
            self._lane_semaphore = asyncio.Semaphore(limit)
            self._semaphore_loop = loop
        return self._lane_semaphore

    def _get_provider(self, model_key: str, config: Any) -> Any:
        """按模型配置缓存 OpenAI 兼容 provider（池由 base_url 映射，与前台分池）。"""
        provider = self._providers.get(model_key)
        if provider is not None:
            return provider
        from app.services.llm.providers import OpenAICompatibleProvider

        provider = OpenAICompatibleProvider(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout_seconds=float(getattr(settings, "BATCH_LANE_CALL_TIMEOUT_SECONDS", 90)),
        )
        self._providers[model_key] = provider
        return provider

    def _get_store(self) -> Any:
        """幂等存储（redis）。导入放内层，测试可用注入替身。"""
        if self._store_override is not None:
            return self._store_override
        from app.core.cache import cache_service

        return cache_service.redis

    async def _load_cached_result(self, key: str) -> dict[str, Any] | None:
        store = self._get_store()
        if store is None:
            return None
        try:
            raw = await store.get(key)
        except Exception as exc:  # noqa: BLE001 — 存储故障不致命，退化为直执行
            logger.warning("[BatchWorklane] result store read failed: {}", exc)
            return None
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    async def _store_result(self, key: str, payload: dict[str, Any]) -> None:
        store = self._get_store()
        if store is None:
            return
        try:
            ttl = int(getattr(settings, "BATCH_LANE_RESULT_TTL_SECONDS", 172800))
            await store.setex(key, ttl, json.dumps(payload, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[BatchWorklane] result store write failed: {}", exc)

    async def _try_claim(self, key: str) -> bool:
        """SET NX claim，防同 key 并发双执行（重放恰一次的执行面保障）。"""
        store = self._get_store()
        if store is None:
            return True
        try:
            ttl = max(30, int(getattr(settings, "BATCH_LANE_CLAIM_TTL_SECONDS", 600)))
            acquired = await store.set(key, "1", nx=True, ex=ttl)
            # set(nx=True) 返回 True = 抢到；None/False = 已被占
            return bool(acquired)
        except TypeError:
            # 某些 fake/客户端不支持 nx/ex —— 降级为 get-then-set（测试环境）
            try:
                if await store.get(key):
                    return False
                await store.set(key, "1")
                return True
            except Exception:  # noqa: BLE001
                return True
        except Exception as exc:  # noqa: BLE001 — 存储故障不阻塞执行
            logger.warning("[BatchWorklane] claim failed (executing anyway): {}", exc)
            return True

    async def _release_claim(self, key: str) -> None:
        store = self._get_store()
        if store is None:
            return
        try:
            await store.delete(key)
        except Exception:  # noqa: BLE001
            pass

    async def _register_dead_letter(
        self,
        kind: BatchWorkloadKind,
        idempotency_key: str,
        error: str,
        attempts: int,
    ) -> None:
        entry = {
            "kind": kind.value,
            "idempotency_key": idempotency_key,
            "error": error[:500],
            "attempts": attempts,
            "at": _utcnow().isoformat(),
        }
        logger.error("[BatchWorklane] DEAD_LETTER kind={} key={} attempts={} error={}", kind.value, idempotency_key, attempts, error)
        store = self._get_store()
        if store is None:
            return
        try:
            cap = max(1, int(getattr(settings, "BATCH_LANE_DEADLETTER_MAX_ENTRIES", 200)))
            await store.lpush(_DEADLETTER_LIST_KEY, json.dumps(entry, ensure_ascii=False))
            await store.ltrim(_DEADLETTER_LIST_KEY, 0, cap - 1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[BatchWorklane] dead-letter registry write failed: {}", exc)

    async def _record_cost(
        self,
        kind: BatchWorkloadKind,
        selection: LLMSelection,
        content: str,
        messages: list[dict[str, str]],
    ) -> float:
        """batch 车道独立成本核算：计 GLM_BATCH 预算桶，不占前台 LLM 预算。"""
        input_tokens = sum(len(str(m.get("content") or "")) for m in messages) / 4.0
        output_tokens = len(content or "") / 4.0
        cost = (input_tokens + output_tokens) / 1000.0 * float(selection.estimated_cost_per_1k or 0.0)
        try:
            breaker = get_budget_breaker()
            await breaker.record_spend(
                CostCategory.GLM_BATCH,
                cost,
                operation=f"batch_worklane/{selection.model_key}",
            )
        except Exception as exc:  # noqa: BLE001 — 核算失败不影响执行
            logger.warning("[BatchWorklane] cost accounting failed: {}", exc)
        BATCH_LANE_COST_USD_TOTAL.labels(kind=kind.value, model=selection.model_key).inc(cost)
        return cost

    async def _execute_once(
        self,
        selection: LLMSelection,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        provider = self._get_provider(selection.model_key, selection.config)
        kwargs: dict[str, Any] = {}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        content = await provider.chat(
            messages,
            model=selection.config.model_name,
            temperature=temperature,
            **kwargs,
        )
        return content or ""

    async def run_chat(
        self,
        kind: BatchWorkloadKind,
        messages: list[dict[str, str]],
        *,
        idempotency_key: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        chat_executor: Callable[..., Awaitable[str]] | None = None,
    ) -> BatchLaneResult:
        """把一次 LLM 调用锁进 batch 车道（幂等 → 预算 → 隔离并发 → 有界重试）。

        chat_executor 可注入（测试零真实 LLM）；默认用路由解析的 OpenAI 兼容
        provider 直连（llm_concurrency 按 base_url 映射 minimax/zhipu_coding 池）。
        """
        start = time.perf_counter()

        def _finish(result: BatchLaneResult) -> BatchLaneResult:
            result.latency_ms = int((time.perf_counter() - start) * 1000)
            return result

        if not self.enabled(kind):
            BATCH_LANE_DISABLED_TOTAL.labels(kind=kind.value).inc()
            BATCH_LANE_DISPATCH_TOTAL.labels(kind=kind.value, outcome=BatchLaneOutcome.DISABLED.value).inc()
            return _finish(BatchLaneResult(
                kind=kind, outcome=BatchLaneOutcome.DISABLED,
                idempotency_key=idempotency_key,
                reason="batch_lane_disabled",
            ))

        # 0) 可用性门：无凭据（无 key 环境）→ 车道不可用，调用方走前台兜底
        available, unavailable_reason = self.lane_available(kind)
        if not available:
            BATCH_LANE_DISABLED_TOTAL.labels(kind=kind.value).inc()
            BATCH_LANE_DISPATCH_TOTAL.labels(kind=kind.value, outcome=BatchLaneOutcome.DISABLED.value).inc()
            return _finish(BatchLaneResult(
                kind=kind, outcome=BatchLaneOutcome.DISABLED,
                idempotency_key=idempotency_key,
                reason=unavailable_reason,
            ))

        # 1) 幂等重放：同 key 已有结果 → 恰好重放，不再执行 LLM
        result_key = _RESULT_KEY_PREFIX + idempotency_key
        cached = await self._load_cached_result(result_key)
        if cached is not None:
            BATCH_LANE_DISPATCH_TOTAL.labels(kind=kind.value, outcome=BatchLaneOutcome.REPLAYED.value).inc()
            return _finish(BatchLaneResult(
                kind=kind, outcome=BatchLaneOutcome.REPLAYED,
                idempotency_key=idempotency_key,
                content=cached.get("content"),
                model_key=str(cached.get("model_key") or ""),
                model=str(cached.get("model") or ""),
                provider=str(cached.get("provider") or ""),
                completed_at=str(cached.get("completed_at") or _utcnow().isoformat()),
                replayed=True,
            ))

        # 2) 并发去重：同 key 另一执行在途 → 跳过（重放恰一次）
        claim_key = _CLAIM_KEY_PREFIX + idempotency_key
        if not await self._try_claim(claim_key):
            BATCH_LANE_DUPLICATE_SKIPPED_TOTAL.labels(kind=kind.value).inc()
            BATCH_LANE_DISPATCH_TOTAL.labels(kind=kind.value, outcome=BatchLaneOutcome.DUPLICATE_SKIPPED.value).inc()
            return _finish(BatchLaneResult(
                kind=kind, outcome=BatchLaneOutcome.DUPLICATE_SKIPPED,
                idempotency_key=idempotency_key,
                reason="duplicate_in_flight",
            ))

        # 3) batch 独立预算门（与前台 LLM 预算桶隔离，互不挤占）
        try:
            within_budget = await get_budget_breaker().check_budget(CostCategory.GLM_BATCH)
        except Exception:  # noqa: BLE001 — 预算面故障放行（不比前台更严格地误伤 batch）
            within_budget = True
        if not within_budget:
            await self._release_claim(claim_key)
            BATCH_LANE_BUDGET_REJECTED_TOTAL.labels(kind=kind.value).inc()
            BATCH_LANE_DISPATCH_TOTAL.labels(kind=kind.value, outcome=BatchLaneOutcome.BUDGET_EXHAUSTED.value).inc()
            return _finish(BatchLaneResult(
                kind=kind, outcome=BatchLaneOutcome.BUDGET_EXHAUSTED,
                idempotency_key=idempotency_key,
                reason="batch_lane_budget_exhausted",
            ))

        selection = self.resolve_selection(kind)
        max_attempts = max(1, int(getattr(settings, "BATCH_LANE_MAX_ATTEMPTS", 3)))
        backoff_base = float(getattr(settings, "BATCH_LANE_RETRY_BACKOFF_SECONDS", 2.0))

        semaphore = self._get_lane_semaphore()
        BATCH_LANE_INFLIGHT.labels(kind=kind.value).inc()
        last_error: str | None = None
        try:
            for attempt in range(1, max_attempts + 1):
                try:
                    if chat_executor is not None:
                        content = await chat_executor(
                            messages,
                            model=selection.config.model_name,
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                    else:
                        async with semaphore:
                            content = await self._execute_once(
                                selection, messages, temperature, max_tokens,
                            )
                except Exception as exc:  # noqa: BLE001 — 有界重试
                    last_error = f"{type(exc).__name__}: {exc}"
                    logger.warning(
                        "[BatchWorklane] attempt {}/{} failed kind={} model={} error={}",
                        attempt, max_attempts, kind.value, selection.model_key, last_error,
                    )
                    if attempt < max_attempts:
                        BATCH_LANE_RETRIES_TOTAL.labels(kind=kind.value).inc()
                        await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))
                    continue

                cost = await self._record_cost(kind, selection, content, messages)
                result = BatchLaneResult(
                    kind=kind, outcome=BatchLaneOutcome.COMPLETED,
                    idempotency_key=idempotency_key,
                    content=content,
                    model_key=selection.model_key,
                    model=selection.config.model_name,
                    provider=selection.config.provider.value,
                    attempts=attempt,
                    cost_usd=cost,
                )
                await self._store_result(
                    result_key,
                    {
                        "content": content,
                        **result.provenance(),
                        "cost_usd": cost,
                    },
                )
                BATCH_LANE_DISPATCH_TOTAL.labels(kind=kind.value, outcome=BatchLaneOutcome.COMPLETED.value).inc()
                BATCH_LANE_LATENCY.labels(kind=kind.value).observe((time.perf_counter() - start))
                return _finish(result)

            # 有界重试耗尽 → 死信终态（不无限循环、不静默丢）
            await self._register_dead_letter(kind, idempotency_key, last_error or "unknown", max_attempts)
            BATCH_LANE_DEADLETTER_TOTAL.labels(kind=kind.value).inc()
            BATCH_LANE_DISPATCH_TOTAL.labels(kind=kind.value, outcome=BatchLaneOutcome.DEAD_LETTER.value).inc()
            return _finish(BatchLaneResult(
                kind=kind, outcome=BatchLaneOutcome.DEAD_LETTER,
                idempotency_key=idempotency_key,
                model_key=selection.model_key,
                model=selection.config.model_name,
                provider=selection.config.provider.value,
                attempts=max_attempts,
                error=last_error,
            ))
        finally:
            BATCH_LANE_INFLIGHT.labels(kind=kind.value).dec()
            # 成功路径保留 claim 至 TTL 过期亦安全（结果键优先命中）；
            # 失败/预算路径需释放，让下一次调度可重试。
            if last_error is not None:
                await self._release_claim(claim_key)


batch_worklane = BatchWorklaneService()
