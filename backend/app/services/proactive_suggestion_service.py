"""
Proactive Suggestion feedback (P-03) — 可忽略、可解释、可 mute 的建议面。

P-03 在既有 nudge 真源（``comeback_nudge_task`` / ``NudgeService`` /
A-07 stimulation policy）之上补齐**用户反馈回路**，不重建任何真源：

- **拒绝后 cooldown**：用户点「今天不再看」→ 记 ``ignored_until = now + 24h``，
  抑制窗口内同类型建议在生成源头被抑制（真源不产新通知，不是渲染层遮蔽）。
- **mute this type**：持久静音该 suggestion 类型，直到用户在设置里恢复。
- **持久层**：``UserPreferencesCenter.explicit`` JSONB（AuroraUserPreferencesService
  同款载体与读写模式），独立命名空间键，不与 Aurora 偏好键冲突，零迁移。
- **四要素 payload**（``build_suggestion_elements``）：``why_now`` /
  ``suggested_action`` 由引擎侧事实字段构建——只陈述计划状态与下一步，
  绝不做心理判断，不用 guilt/羞耻/压力话术（PRODUCT_LANGUAGE 红线；
  「还来得及」一类表述按 A-07 口径不得进入建议要素）。
- **deep link**（``resolve_comeback_destination``）：goal_state.goal_id 存在时
  指向 Goal 页（读侧真源投影，不误用 plan_id——F-7 判例）；无 goal 时回退
  Plan 页；两者皆无时回退 chat。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Mapping, cast
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preferences import UserPreferencesCenter

__all__ = [
    "ProactiveSuggestionFeedbackService",
    "ProactiveSuggestionFeedbackError",
    "IGNORE_TODAY_COOLDOWN_HOURS",
    "build_suggestion_elements",
    "resolve_comeback_destination",
]

#: 「今天不再看」冷却窗口（小时）。语义：拒绝后 24h 内同类型建议不再生成。
IGNORE_TODAY_COOLDOWN_HOURS = 24

_MUTE_KEY = "proactive_suggestion_muted"
_IGNORE_KEY = "proactive_suggestion_ignored_until"

#: 版本守卫合并的bounded重试上限（冲突连续超限 → 诚实报错，不静默丢写）
_MAX_MERGE_ATTEMPTS = 3


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


class ProactiveSuggestionFeedbackError(Exception):
    """抑制态落库失败（诚实错误；API 层映射 503，不谎报成功）.

    WT378-02：``_update_explicit`` 曾吞掉一切写异常并照常返回成功 payload——
    DB 瞬断时用户看到「不再提醒」已生效而抑制态零落库。写失败必须显式抛错。
    """


class ProactiveSuggestionFeedbackService:
    """记录/查询用户对主动建议的反馈（mute 与 today-ignore cooldown）。

    状态落在 ``UserPreferencesCenter.explicit`` JSONB 的独立命名空间键里；
    与 AuroraUserPreferencesService 共用一行存储但键集不相交，互不覆写。
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- write ------------------------------------------------------------

    async def record_ignore_today(
        self,
        user_id: str | UUID,
        suggestion_type: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, str]:
        """「今天不再看」：返回 ``{"reason": "cooldown", "until": iso}``。

        落库失败抛 ``ProactiveSuggestionFeedbackError``（诚实错误，不假成功）。
        """
        moment = now or _utcnow()
        until = moment + timedelta(hours=IGNORE_TODAY_COOLDOWN_HOURS)
        await self._update_explicit(
            user_id,
            _IGNORE_KEY,
            lambda current: {**current, suggestion_type: _iso(until)},
        )
        return {"reason": "cooldown", "until": _iso(until)}

    async def record_mute(
        self,
        user_id: str | UUID,
        suggestion_type: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, str]:
        """「不再提醒此类」：持久静音。返回 ``{"reason": "muted"}``。

        落库失败抛 ``ProactiveSuggestionFeedbackError``（诚实错误，不假成功）。
        """
        moment = now or _utcnow()
        await self._update_explicit(
            user_id,
            _MUTE_KEY,
            lambda current: {**current, suggestion_type: _iso(moment)},
        )
        return {"reason": "muted"}

    # -- read -------------------------------------------------------------

    async def get_suppression(
        self,
        user_id: str | UUID,
        suggestion_type: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, str] | None:
        """返回抑制态 ``{"reason": "muted"|"cooldown", "until": iso?}``，未抑制为 ``None``。"""
        moment = now or _utcnow()
        explicit = await self._read_explicit(user_id)

        if suggestion_type in (explicit.get(_MUTE_KEY) or {}):
            return {"reason": "muted"}

        ignored_until_raw = (explicit.get(_IGNORE_KEY) or {}).get(suggestion_type)
        if isinstance(ignored_until_raw, str) and ignored_until_raw:
            try:
                ignored_until = datetime.fromisoformat(ignored_until_raw)
            except ValueError:
                logger.warning(
                    "proactive suggestion ignored_until corrupt for user={} type={}",
                    user_id,
                    suggestion_type,
                )
                return None
            if ignored_until > moment:
                return {"reason": "cooldown", "until": ignored_until_raw}
        return None

    async def is_suppressed(
        self,
        user_id: str | UUID,
        suggestion_type: str,
        *,
        now: datetime | None = None,
    ) -> bool:
        return await self.get_suppression(user_id, suggestion_type, now=now) is not None

    # -- storage ----------------------------------------------------------

    async def _read_explicit(self, user_id: str | UUID) -> dict[str, Any]:
        """读 explicit（WT378-03 fail-closed：读失败抛错，绝不当作「未抑制」）.

        mute/cooldown 语义是「直到用户恢复/24h」——把读失败当成空 dict 会让
        抑制态在瞬时错误窗口内静默失效（静音被击穿）。读不到 ≠ 未抑制：
        异常向上传播，由调用方按失败处理（celery 重试 / 事件处理留痕）。
        """
        result = await self.db.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id))
        row = result.scalar_one_or_none()
        if row is None:
            return {}
        explicit = row.explicit
        return dict(explicit) if isinstance(explicit, Mapping) else {}

    async def _update_explicit(
        self,
        user_id: str | UUID,
        key: str,
        mutate,
    ) -> None:
        """版本守卫 CAS 合并写（WT378-02 诚实 + WT378-04 防丢更新）.

        - 写失败（瞬断/约束冲突/重试超限）→ 抛 ``ProactiveSuggestionFeedbackError``，
          绝不吞错后返回成功；
        - 与 AuroraUserPreferencesService 同行双写：读行带 ``FOR UPDATE``
          （PG 行锁；sqlite 忽略无害）+ ``UPDATE ... WHERE version = 读时版本``
          原子合并 + 冲突重读重试——读改写从「旧快照整列覆写」改为「CAS 合并」，
          杜绝先行写方的键整组蒸发。
        """
        try:
            for _attempt in range(_MAX_MERGE_ATTEMPTS):
                result = await self.db.execute(
                    select(UserPreferencesCenter)
                    .where(UserPreferencesCenter.user_id == user_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                row = result.scalar_one_or_none()
                if row is None:
                    row = UserPreferencesCenter(
                        user_id=user_id,
                        explicit={key: mutate({})},
                        last_explicit_update=_utcnow(),
                    )
                    self.db.add(row)
                    try:
                        await self.db.commit()
                        return
                    except IntegrityError:
                        # 并发首写撞 user_id unique → 重读合并
                        await self.db.rollback()
                        continue

                explicit = dict(row.explicit) if isinstance(row.explicit, Mapping) else {}
                explicit[key] = mutate(dict(explicit.get(key) or {}))
                version_before = row.version
                merge_result = await self.db.execute(
                    update(UserPreferencesCenter)
                    .where(
                        UserPreferencesCenter.user_id == user_id,
                        UserPreferencesCenter.version == version_before,
                    )
                    .values(explicit=explicit, last_explicit_update=_utcnow(), version=version_before + 1)
                )
                if cast(CursorResult[Any], merge_result).rowcount == 1:
                    await self.db.commit()
                    return
                # 版本冲突：他人已提交 → 回滚后重读合并（保对方键）
                await self.db.rollback()
        except ProactiveSuggestionFeedbackError:
            raise
        except Exception as exc:
            await self.db.rollback()
            logger.opt(exception=True).warning(
                "proactive suggestion feedback write failed for user={} key={}",
                user_id,
                key,
            )
            raise ProactiveSuggestionFeedbackError(
                f"suggestion feedback not persisted (user={user_id}, key={key})"
            ) from exc
        raise ProactiveSuggestionFeedbackError(
            f"suggestion feedback not persisted after {_MAX_MERGE_ATTEMPTS} merge attempts "
            f"(user={user_id}, key={key})"
        )


# ── 四要素 payload 构建（纯函数；事实性、零 guilt） ───────────────────────────


def build_suggestion_elements(payload: Mapping[str, Any]) -> dict[str, str]:
    """从 comeback/nudge payload 构建建议要素：``why_now`` 与 ``suggested_action``。

    why-now 只陈述**计划状态事实**（截止窗口 / 任务账本 / 下一个任务），不指向
    人、不做心理推断、不用压力话术；suggested-action 优先用引擎已生成的轻量
    启动建议，缺省时落到具体下一步。
    """
    subject = str(payload.get("subject") or "").strip() or "学习计划"
    days_remaining = payload.get("days_remaining")
    plan_expired = bool(payload.get("plan_expired"))
    next_task = str(payload.get("next_task_title") or "").strip()
    if not next_task:
        next_task = str(payload.get("recent_task_summary") or "").strip()

    facts: list[str] = []
    if plan_expired or (isinstance(days_remaining, (int, float)) and days_remaining <= 0):
        facts.append(f"「{subject}」的原定窗口已经结束")
    elif isinstance(days_remaining, (int, float)) and days_remaining > 0:
        facts.append(f"距离「{subject}」目标截止还有 {int(days_remaining)} 天")
    else:
        facts.append(f"「{subject}」计划还在进行中")

    goal_state = payload.get("goal_state")
    ledger: Mapping[str, Any] = {}
    if isinstance(goal_state, Mapping):
        raw_ledger = goal_state.get("ledger")
        if isinstance(raw_ledger, Mapping):
            ledger = raw_ledger
    total = ledger.get("total")
    completed = ledger.get("completed")
    if isinstance(total, (int, float)) and total > 0 and isinstance(completed, (int, float)):
        facts.append(f"任务账本 {int(completed)}/{int(total)}")

    if next_task:
        facts.append(f"下一个任务是「{next_task}」")

    why_now = "；".join(facts) + "。"

    light_restart = str(payload.get("light_restart_suggestion") or "").strip()
    if light_restart:
        suggested_action = light_restart
    elif next_task:
        suggested_action = f"从「{next_task}」的一小步开始"
    else:
        suggested_action = "从今天最小的一步开始"

    return {"why_now": why_now, "suggested_action": suggested_action}


def resolve_comeback_destination(payload: Mapping[str, Any]) -> str:
    """建议 deep link：Goal 页优先（读侧 goal_state.goal_id），Plan 兜底，chat 保底。

    goal_id 来自 A-07 的 goal_state 读侧投影（真实 ``Goal.id``）——绝不把
    plan_id 误用作 goal id（F-7 判例）。
    """
    goal_state = payload.get("goal_state")
    if isinstance(goal_state, Mapping):
        goal_id = str(goal_state.get("goal_id") or "").strip()
        if goal_id:
            return f"/goals/{goal_id}?source=comeback_nudge"

    plan_id = str(payload.get("plan_id") or "").strip()
    if plan_id:
        return f"/plans/{plan_id}?source=comeback_nudge"

    return "/chat?entry=comeback_nudge"
