"""
UnderstandingDepthMetricService — "越用越懂用户"每日量化基线（数据飞轮 MVP）。

与运行时 `UnderstandingDepthService`（self_evolution_service.py，L0-L5 等级、纯
Redis 态、每次请求现算）互补：本服务做 **每日离线聚合**，产出可回归、可画趋势的
0-1 合成分并落表 understanding_depth_daily。

## 指标设计（v0.1，全部数据源为既有生产表）

| 分量 | 含义 | 数据源 | 方向 |
|---|---|---|---|
| memory_injection | 记忆命中/注入量：日均注入记忆条数（preferences+goals+episodic），饱和点 HIT_SATURATION=3 | context_pack_runs.memory_counts | 越多越高 |
| personalization | 个性化回复率：注入了 ≥1 条记忆的 context pack 占比 | context_pack_runs.memory_counts | 越高越高 |
| non_correction | 1 - 纠正强度：memory_corrections 次数 / max(chat_turns,1)，容忍度 CORRECTION_TOLERANCE=0.5 次/轮 | memory_corrections + chat_messages(role=user) | 纠正越少越高 |
| non_repeat | 1 - 重复提问率：当日 user 消息归一化后重复占比 | chat_messages(role=user) | 重复越少越高 |

合成分 `score = 0.40*memory_injection + 0.25*personalization + 0.20*non_correction
+ 0.15*non_repeat`，权重和为 1，各分量 ∈ [0,1]，故 score ∈ [0,1]；每个分量对
"更懂用户"单调，线性合成保持各维单调性（单测钉死）。

冷启动规则：当日既无 context_pack_runs 也无 user 消息 → 不落行。
重复判定对 ≤4 字符的短消息（"嗯"、"谢谢"）豁免，避免误伤寒暄。
"""

from __future__ import annotations

import re
from datetime import date as date_type
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, MessageRole
from app.models.context_pack import ContextPackRun
from app.models.memory import MemoryCorrection
from app.models.understanding_depth import UnderstandingDepthDaily

# ---- 归一化常数（改这里要同步更新报告与单测注释）----
WEIGHT_MEMORY = 0.40
WEIGHT_PERSONALIZATION = 0.25
WEIGHT_NON_CORRECTION = 0.20
WEIGHT_NON_REPEAT = 0.15

HIT_SATURATION = 3.0  # 日均注入 ≥3 条记忆 → memory_injection 满分
CORRECTION_TOLERANCE = 0.5  # 0.5 次纠正/轮 → non_correction 归零
SHORT_MESSAGE_MIN_LEN = 4  # 归一化后长度 ≤4 的消息不参与重复判定

_PUNCT_RE = re.compile(r"[\s，。？！、；：\"'“”‘’（）《》\[\]{}…·,.\?;:!?()\[\]<>]+")


def _normalize_message(text: str) -> str:
    """消息归一化：去空白/标点、小写。用于重复提问判定。"""
    return _PUNCT_RE.sub("", str(text or "")).lower()


def normalize_memory_counts(memory_counts: Any) -> int:
    """context_pack_runs.memory_counts JSONB → 该 run 注入记忆总条数。"""
    if not isinstance(memory_counts, dict):
        return 0
    total = 0
    for key in ("preferences", "goals", "episodic"):
        value = memory_counts.get(key)
        if isinstance(value, (int, float)) and value > 0:
            total += int(value)
    return total


def compute_components(
    *,
    memory_counts_list: list[int],
    chat_messages: list[str],
    correction_count: int,
) -> dict[str, Any]:
    """由当日原始样本计算各维度分量（纯函数，单测主入口）。

    Args:
        memory_counts_list: 当日每个 context pack run 注入的记忆条数。
        chat_messages: 当日 user 角色消息原文列表。
        correction_count: 当日 memory_corrections 行数。
    Returns:
        components dict：4 个归一化分量 + 原始样本量。
    """
    runs = len(memory_counts_list)
    chat_turns = len(chat_messages)
    total_injected = sum(memory_counts_list)
    personalized_runs = sum(1 for count in memory_counts_list if count > 0)
    avg_injected = (total_injected / runs) if runs else 0.0
    personalization_ratio = (personalized_runs / runs) if runs else 0.0

    # 重复提问：归一化后出现 >1 次的消息，超出第一条的份数 / 参与判定消息数。
    normalized = [_normalize_message(msg) for msg in chat_messages]
    eligible = [text for text in normalized if len(text) > SHORT_MESSAGE_MIN_LEN]
    if eligible:
        seen: dict[str, int] = {}
        for text in eligible:
            seen[text] = seen.get(text, 0) + 1
        duplicates = sum(count - 1 for count in seen.values() if count > 1)
        repeat_ratio = duplicates / len(eligible)
    else:
        repeat_ratio = 0.0

    # 纠正强度：纠正次数 / 聊天轮数，CORRECTION_TOLERANCE 次/轮归零。
    correction_intensity = correction_count / chat_turns if chat_turns else 0.0

    components = {
        "memory_injection": round(min(1.0, avg_injected / HIT_SATURATION), 4),
        "personalization": round(min(1.0, personalization_ratio), 4),
        "non_correction": round(max(0.0, 1.0 - correction_intensity / CORRECTION_TOLERANCE), 4),
        "non_repeat": round(max(0.0, 1.0 - repeat_ratio), 4),
        # 原始样本量（可解释性/重放）
        "context_pack_runs": runs,
        "avg_memory_injected": round(avg_injected, 4),
        "chat_turns": chat_turns,
        "memory_corrections": int(correction_count),
        "repeat_questions": int(round(repeat_ratio * len(eligible))) if eligible else 0,
    }
    return components


def compute_score(components: dict[str, Any]) -> float:
    """合成分（纯函数）：各分量加权和，∈[0,1]，对每维单调。"""
    score = (
        WEIGHT_MEMORY * float(components.get("memory_injection") or 0.0)
        + WEIGHT_PERSONALIZATION * float(components.get("personalization") or 0.0)
        + WEIGHT_NON_CORRECTION * float(components.get("non_correction") or 0.0)
        + WEIGHT_NON_REPEAT * float(components.get("non_repeat") or 0.0)
    )
    return round(min(1.0, max(0.0, score)), 4)


def _day_bounds(day: date_type) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day)
    return start, start + timedelta(days=1)


class UnderstandingDepthMetricService:
    """每日离线聚合 + 趋势查询。Celery beat 每日调用 compute_daily_all。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_daily_for_user(self, *, user_id: UUID, day: date_type) -> float | None:
        """计算并 upsert 单用户单日基线；无活动返回 None（不落行）。"""
        start, end = _day_bounds(day)

        runs_result = await self.db.execute(
            select(ContextPackRun.memory_counts).where(
                ContextPackRun.user_id == user_id,
                ContextPackRun.created_at >= start,
                ContextPackRun.created_at < end,
            )
        )
        memory_counts_list = [normalize_memory_counts(row) for row in runs_result.scalars().all()]

        messages_result = await self.db.execute(
            select(ChatMessage.content).where(
                ChatMessage.user_id == user_id,
                ChatMessage.role == MessageRole.USER,
                ChatMessage.created_at >= start,
                ChatMessage.created_at < end,
                ChatMessage.deleted_at.is_(None),
            )
        )
        chat_messages = [str(text or "") for text in messages_result.scalars().all()]

        corrections_result = await self.db.execute(
            select(MemoryCorrection).where(
                MemoryCorrection.user_id == user_id,
                MemoryCorrection.created_at >= start,
                MemoryCorrection.created_at < end,
            )
        )
        correction_count = len(corrections_result.scalars().all())

        if not memory_counts_list and not chat_messages:
            return None

        components = compute_components(
            memory_counts_list=memory_counts_list,
            chat_messages=chat_messages,
            correction_count=correction_count,
        )
        score = compute_score(components)

        existing = (
            await self.db.execute(
                select(UnderstandingDepthDaily).where(
                    UnderstandingDepthDaily.user_id == user_id,
                    UnderstandingDepthDaily.metric_date == day,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            self.db.add(
                UnderstandingDepthDaily(
                    user_id=user_id,
                    metric_date=day,
                    score=score,
                    components=components,
                    context_pack_runs=int(components["context_pack_runs"]),
                    chat_turns=int(components["chat_turns"]),
                )
            )
        else:
            existing.score = score
            existing.components = components
            existing.context_pack_runs = int(components["context_pack_runs"])
            existing.chat_turns = int(components["chat_turns"])
        await self.db.commit()
        return score

    async def compute_daily_all(self, *, day: date_type, limit: int = 2000) -> dict[str, int]:
        """对当日有活动的用户全量计算。由 celery beat 每日触发。"""
        start, end = _day_bounds(day)
        user_ids: set[UUID] = set()

        pack_users = await self.db.execute(
            select(ContextPackRun.user_id).where(
                ContextPackRun.created_at >= start,
                ContextPackRun.created_at < end,
            )
        )
        user_ids.update(row for row in pack_users.scalars().all() if row)

        chat_users = await self.db.execute(
            select(ChatMessage.user_id).where(
                ChatMessage.role == MessageRole.USER,
                ChatMessage.created_at >= start,
                ChatMessage.created_at < end,
                ChatMessage.deleted_at.is_(None),
            )
        )
        user_ids.update(row for row in chat_users.scalars().all() if row)

        computed = 0
        skipped = 0
        for user_id in sorted(user_ids)[:limit]:
            try:
                if await self.compute_daily_for_user(user_id=user_id, day=day) is None:
                    skipped += 1
                else:
                    computed += 1
            except Exception as exc:  # 单用户失败不阻断整批
                logger.warning(f"understanding-depth daily compute failed for {user_id}: {exc}")
                skipped += 1
        return {"active_users": len(user_ids), "computed": computed, "skipped": skipped}

    async def get_trend(self, *, user_id: UUID, days: int = 7) -> list[UnderstandingDepthDaily]:
        """近 N 天基线趋势（升序）。days 仅支持 7/30，其余按 7。"""
        window = days if days in (7, 30) else 7
        since = (datetime.utcnow() - timedelta(days=window - 1)).date()
        result = await self.db.execute(
            select(UnderstandingDepthDaily)
            .where(
                UnderstandingDepthDaily.user_id == user_id,
                UnderstandingDepthDaily.metric_date >= since,
            )
            .order_by(UnderstandingDepthDaily.metric_date.asc())
        )
        return list(result.scalars().all())
