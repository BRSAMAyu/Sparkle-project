"""M-06 · Experience Memory Projector 服务层（只读投影 + Context retrieval）。

形态（契约 = ``app/core/experience_memory.py``）：

- **投影（read-side 衍生视图）**：``project()`` 消费 D-05
  ``InterventionLifecycleService.association_summary`` 的保守摘要，纯函数
  投影成 ``ExperienceProjection``（每切片一条 ``ExperienceMemoryRecord``）。
  零写路径：不 ``db.add``、不产事件、不落新表——outcome 真源是 D-02，
  生命周期/聚合真源是 D-05，本层不复制任何写路径。
- **截断语义（FIX-31 P2-1 消费面动作）**：D-05 摘要按 ``occurred_at ASC``
  加载 ``_SUMMARY_EVENT_CAP``（5000）行，超界时静默丢弃最新历史且载体无
  truncated 标记。消费侧探测：对同谓词（user + not_deleted + [since, until)
  窗口，无 cohort 排除——截断发生在排除前的加载面）做 count，行数 > cap
  即判定截断 → 投影 ``truncated=True`` + 档位降一级
  （``completeness_adjusted_strength``，D-05 原档位保留）。cap 常量从
  D-05 服务模块 import——上游调 cap 本层自动跟随。
- **缓存（D-05 预留钩）**：进程内 LRU，键 = D-05 ``summary_cache_key``，
  失效 = 公开 ``watermark()`` 印记变化 + 有界 TTL（默认 300s）。TTL 兜底
  FIX-31 P3-1（>1000 事件时公开 watermark 与事件集非全指纹——中位事件
  删除可能不动印记；单用户 ≤1000 事件的常态场景印记含行数，删除可测）。
  另：摘要的删失分类是 ``now`` 的函数（not_yet_due→window_closed 随时间
  迁移而事件集不变），TTL 同时是这类时间迁移的可见性上界（观察窗以小时
  计，300s 滞后对 context 装配无实质影响）。
- **Context retrieval（卡面 Work 3）**：``retrieve_context()`` 供
  chat/orchestration 装配 context——「该用户相似 situation 下何曾与正/负
  结果共同出现」。双向召回 + 无证据桶，输出经**真实 M-03 预筛**
  （``build_retrieval_context`` 加载真实 ``user_memory_settings`` →
  ``prefilter_candidates`` 守卫投影记录的鸭子类型面）后才返回；purpose 词表
  复用 M-03 ``RETRIEVAL_PURPOSES``。M-05 输出面：``to_selfcheck_candidates``
  把记录映射为 ``MemoryUseCandidate``（section="episodic"），调用方过真实
  ``run_memory_use_selfcheck`` 决定 surface/internal-only（接线测试钉死链路
  不弱化）。

边界（与 M-02/M-05/M-07 的关系）：
- M-02 storage gate 是 episodic **写路径**守门员——本层零写路径，故不在
  M-02 门后；若未来卡片物化经验记录为 episodic 行（M-01 注释预留的
  EXPERIENCE writer 面），须走 B3 结构化系统写者通道 + memory_epoch 失效，
  属独立卡片；
- M-05 usage selfcheck：本层输出可完整过真实 selfcheck（见上）；
- M-07 删除：无物化行 → 无复活面；事件删除经 watermark/TTL 反映（见上）。
"""

from __future__ import annotations

import time
from collections import OrderedDict
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from uuid import UUID

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.experience_memory import (
    BUCKET_NO_OUTCOME_EVIDENCE,
    DIRECTION_NEGATIVE,
    DIRECTION_POSITIVE,
    EXPERIENCE_CONTEXT_RESULT_PAYLOAD_KEYS,
    EXPERIENCE_MEMORY_SCHEMA_VERSION,
    EXPERIENCE_RECALL_BUCKETS,
    SUMMARY_TRUNCATION_REASON,
    ExperienceContextQuery,
    ExperienceContextResult,
    ExperienceMemoryRecord,
    ExperienceProjection,
    project_summary,
    rank_experience_records,
    signature_matches_query,
    split_by_evidence_direction,
)
from app.core.time_utils import ensure_naive_utc, utcnow
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.services import intervention_lifecycle_service as _d05
from app.services.intervention_lifecycle_service import InterventionLifecycleService
from app.services.memory_retrieval_prefilter import (
    build_retrieval_context,
    prefilter_candidates,
)
from app.services.memory_use_selfcheck import (
    MemoryUseCandidate,
    SelfCheckContext,
    run_memory_use_selfcheck,
)

EXPERIENCE_MEMORY_PROJECTOR_VERSION = "experience-memory.m06.v1"

#: 缓存 TTL（秒）：watermark 兜底（FIX-31 P3-1）+ 删失分类的时间迁移上界。
CACHE_TTL_SECONDS = 300.0
#: 进程内缓存条目上限（per-user 键，LRU 淘汰）。
CACHE_MAX_ENTRIES = 256


def _naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return ensure_naive_utc(value)


class ExperienceMemoryProjector:
    """经验记忆投影器（只读；一个 AsyncSession 一个实例）。"""

    # 进程级缓存（跨实例共享；watermark + TTL 失效）。
    _cache: OrderedDict[str, tuple[str, ExperienceProjection, float]] = OrderedDict()

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 1. 投影（D-05 摘要 → 经验记忆记录；只读）
    # ------------------------------------------------------------------

    async def project(
        self,
        *,
        user_id: UUID | str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        now: datetime | None = None,
        user_last_active_at: datetime | None = None,
        include_demo_cohort: bool = False,
        use_cache: bool = True,
    ) -> ExperienceProjection:
        """per-user（或 global，``user_id=None``）经验记忆投影。

        - 缓存命中条件：(D-05 cache_key, 公开 watermark) 匹配且条目年龄 ≤ TTL；
        - 截断探测与摘要同谓词（user + not_deleted + [since, until)）；
        - ``user_last_active_at`` 透传 D-05（churned 判定活跃面）。
        """
        now_naive = _naive(now) or utcnow()
        svc = InterventionLifecycleService(self.db)
        # cohort 旗标必须进 M-06 自有缓存键：D-05 summary_cache_key 只含
        # (user, window)，同窗不同旗标共享条目会让 demo cohort 行在暖缓存下
        # 泄入显式排除调用（R2 P2-1），双向均错。
        cache_key = f"{InterventionLifecycleService.summary_cache_key(user_id=user_id, since=since, until=until)}|demo={int(include_demo_cohort)}"
        watermark = await svc.watermark(user_id=user_id)
        if use_cache:
            cached = self._cache_get(cache_key, watermark)
            if cached is not None:
                return cached

        summary = await svc.association_summary(
            user_id=user_id,
            since=since,
            until=until,
            now=now_naive,
            user_last_active_at=user_last_active_at,
            include_demo_cohort=include_demo_cohort,
        )
        n_rows = await self._count_events(user_id=user_id, since=since, until=until)
        # cap 惰性引用（模块属性读取）：上游 D-05 调整 cap 时探测面自动跟随，
        # 不出现「摘要按新 cap 截断、探测按旧 cap 判否」的分裂。
        summary_cap = int(getattr(_d05, "_SUMMARY_EVENT_CAP", 5000))
        truncated = n_rows > summary_cap
        if truncated:
            logger.warning(
                "M-06 experience projection truncated: rows={} cap={} (FIX-31 P2-1; "
                "newest history dropped by D-05 ASC load; strength downgraded one tier)",
                n_rows,
                summary_cap,
            )
        projection = project_summary(summary, truncated=truncated)
        self._cache_put(cache_key, watermark, projection)
        return projection

    # ------------------------------------------------------------------
    # 2. Context retrieval（相似情境双向召回；M-03 预筛在输出边界真实执行）
    # ------------------------------------------------------------------

    async def retrieve_context(self, query: ExperienceContextQuery) -> ExperienceContextResult:
        """「该用户相似 situation 下何曾与正/负结果共同出现」。

        身份不可判定即拒绝（``user_id`` 必填——M-03 identity 维度同律，
        派生视图没有无主体放行的合法形态）。purpose 词表校验由 M-03
        ``RetrievalContext`` 构造器执行（fail-loud）。
        """
        if not query.user_id or not str(query.user_id).strip():
            raise ValueError("ExperienceContextQuery.user_id is required (identity is unconditional)")

        projection = await self.project(
            user_id=query.user_id,
            since=query.since,
            until=query.until,
            now=query.now,
            user_last_active_at=query.user_last_active_at,
        )

        constraints = query.constraints()
        matched = [record for record in projection.records if signature_matches_query(constraints, record.signature)]
        ranked = rank_experience_records(matched)
        buckets = split_by_evidence_direction(ranked)

        # 上下文预算：每桶截到 max_records_per_direction（排序确定性 → 截断确定性）
        cap = max(0, int(query.max_records_per_direction))
        capped: dict[str, tuple[ExperienceMemoryRecord, ...]] = {
            name: tuple(records[:cap]) for name, records in buckets.items()
        }

        # 真实 M-03 预筛（加载真实 user_memory_settings；鸭子类型候选面）
        ctx = await build_retrieval_context(
            self.db,
            user_id=query.user_id,
            purpose=query.purpose,
            now=_naive(query.now),
        )
        prefilter_payloads: dict[str, Mapping[str, Any]] = {}
        filtered: dict[str, tuple[ExperienceMemoryRecord, ...]] = {}
        for name in EXPERIENCE_RECALL_BUCKETS:
            records = capped.get(name, ())
            if not records:
                filtered[name] = ()
                continue
            result = prefilter_candidates(records, ctx)
            filtered[name] = tuple(result.allowed)
            prefilter_payloads[name] = result.to_metric_payload()

        return ExperienceContextResult(
            schema_version=EXPERIENCE_MEMORY_SCHEMA_VERSION,
            query=query,
            observed_with_positive=filtered.get(DIRECTION_POSITIVE, ()),
            observed_with_negative=filtered.get(DIRECTION_NEGATIVE, ()),
            no_outcome_evidence=filtered.get(BUCKET_NO_OUTCOME_EVIDENCE, ()),
            watermark=projection.watermark,
            truncated=projection.truncated,
            truncation_reason=SUMMARY_TRUNCATION_REASON if projection.truncated else "",
            prefilter_payloads=prefilter_payloads,
        )

    # ------------------------------------------------------------------
    # 内部：截断探测（与 D-05 摘要加载同谓词的 count）
    # ------------------------------------------------------------------

    async def _count_events(
        self,
        *,
        user_id: UUID | str | None,
        since: datetime | None,
        until: datetime | None,
    ) -> int:
        """行数探测：user + not_deleted + [since, until)（与摘要加载谓词一致）。

        不做 cohort 排除：D-05 的 cap 截断发生在 ASC 加载面（demo 排除在
        加载之后），探测的正是「进入加载的行数」。global scope（user_id=None）
        计全表未删行——global 最先触界（FIX-31 登记语）。
        """
        predicates = [InterventionLifecycleEvent.not_deleted_filter()]
        if user_id is not None:
            predicates.append(InterventionLifecycleEvent.user_id == UUID(str(user_id)))
        since_naive = _naive(since)
        until_naive = _naive(until)
        if since_naive is not None:
            predicates.append(InterventionLifecycleEvent.occurred_at >= since_naive)
        if until_naive is not None:
            predicates.append(InterventionLifecycleEvent.occurred_at < until_naive)
        count = (
            await self.db.execute(select(func.count()).select_from(InterventionLifecycleEvent).where(*predicates))
        ).scalar_one()
        return int(count)

    # ------------------------------------------------------------------
    # 内部：进程级缓存（(cache_key, watermark) + TTL）
    # ------------------------------------------------------------------

    @classmethod
    def _cache_get(cls, cache_key: str, watermark: str) -> ExperienceProjection | None:
        entry = cls._cache.get(cache_key)
        if entry is None:
            return None
        cached_watermark, projection, computed_at = entry
        if cached_watermark != watermark:
            return None  # 事件集印记变化 → 失效（D-05 预留钩）
        if time.monotonic() - computed_at > CACHE_TTL_SECONDS:
            cls._cache.pop(cache_key, None)
            return None  # TTL 兜底（FIX-31 P3-1 印记盲区 + 删失时间迁移）
        cls._cache.move_to_end(cache_key)
        return projection

    @classmethod
    def _cache_put(cls, cache_key: str, watermark: str, projection: ExperienceProjection) -> None:
        cls._cache[cache_key] = (watermark, projection, time.monotonic())
        cls._cache.move_to_end(cache_key)
        while len(cls._cache) > CACHE_MAX_ENTRIES:
            cls._cache.popitem(last=False)

    @classmethod
    def reset_cache(cls) -> None:
        """测试钩：清空进程级投影缓存。"""
        cls._cache.clear()


# ---------------------------------------------------------------------------
# M-05 usage selfcheck 接线面（输出面链路不弱化）
# ---------------------------------------------------------------------------


def to_selfcheck_candidates(
    records: Iterable[ExperienceMemoryRecord],
    *,
    section: str = "episodic",
) -> tuple[MemoryUseCandidate, ...]:
    """经验记录 → M-05 selfcheck 候选（内容面 = D-05 非因果 claim 文案）。

    调用方在装配最终输出时过真实 ``run_memory_use_selfcheck``：经验证据
    主要服务内部决策（干预选择），surfaced 与否由 M-05 的 relevance/
    necessity/repetition/sycophancy 四检决定——本层不复制那些判定。
    """
    return tuple(
        MemoryUseCandidate(
            item_id=record.record_id,
            section=section,
            content=record.claim,
        )
        for record in records
    )


async def run_experience_use_selfcheck(
    records: Sequence[ExperienceMemoryRecord],
    *,
    ctx: SelfCheckContext | None = None,
):
    """便捷面：对一组经验记录跑真实 M-05 输出门（决策面归 M-05 单一权威）。"""
    return await run_memory_use_selfcheck(episodic=to_selfcheck_candidates(records), ctx=ctx)


def projection_is_clean_of_causal_assertions(projection: ExperienceProjection) -> list[str]:
    """便捷面：对投影 payload 跑无因果断言扫描（空清单 = 干净；验收 ③）。"""
    from app.core.experience_memory import scan_output_for_causal_assertions

    return scan_output_for_causal_assertions(projection.to_dict())


__all__ = [
    "EXPERIENCE_MEMORY_PROJECTOR_VERSION",
    "CACHE_TTL_SECONDS",
    "CACHE_MAX_ENTRIES",
    "EXPERIENCE_CONTEXT_RESULT_PAYLOAD_KEYS",
    "EXPERIENCE_MEMORY_SCHEMA_VERSION",
    "ExperienceMemoryProjector",
    "to_selfcheck_candidates",
    "run_experience_use_selfcheck",
    "projection_is_clean_of_causal_assertions",
]
