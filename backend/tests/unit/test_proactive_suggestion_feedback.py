"""P-03: Proactive Suggestion feedback — cooldown / mute 真逻辑 + 四要素 + deep link。

红测先行（wt370 卡 P-03）：

- 拒绝（今天不再看）后 cooldown 生效：窗口内同类型建议被抑制，窗口外恢复——
  抑制判定是服务端真逻辑（读 UserPreferencesCenter 持久态），不是渲染层遮蔽。
- mute this type：持久静音、跨类型隔离。
- 四要素 payload：why_now / suggested_action 事实性构建，guilt 词零命中。
- deep link：goal_state.goal_id 优先 → Goal 页；plan 兜底 → Plan 页；无目标 → chat。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

# guilt/羞耻/诊断式文案红线词表（PRODUCT_LANGUAGE）。命中即红。
GUILT_LEXICON: tuple[str, ...] = (
    "懒",
    "落后",
    "拖后腿",
    "堕落",
    "荒废",
    "浪费",
    "太差",
    "失败",
    "你怎么",
    "辜负",
    "失望",
    "别人都",
    "羞耻",
    "丢人",
)

# A-07 判定的压力话术：对已过期计划不得宣称“还来得及”。
PRESSURE_LEXICON: tuple[str, ...] = ("还来得及",)


def _assert_guilt_free(text: str) -> None:
    for term in GUILT_LEXICON + PRESSURE_LEXICON:
        assert term not in text, f"guilt/pressure term {term!r} hit in: {text!r}"


# ── cooldown / mute 真逻辑（DB 持久态，非渲染遮蔽） ──────────────────────────


@pytest.mark.asyncio
async def test_ignore_today_sets_cooldown_that_expires(db, test_user):
    """拒绝后 cooldown 生效：窗口内抑制、窗口过期恢复。"""
    from app.services.proactive_suggestion_service import (
        IGNORE_TODAY_COOLDOWN_HOURS,
        ProactiveSuggestionFeedbackService,
    )

    service = ProactiveSuggestionFeedbackService(db)
    now = datetime.now(UTC).replace(tzinfo=None)

    result = await service.record_ignore_today(test_user.id, "comeback_nudge", now=now)
    assert result["reason"] == "cooldown"
    assert result["until"] is not None

    # 窗口内：抑制，且带可解释原因。
    within = await service.get_suppression(test_user.id, "comeback_nudge", now=now + timedelta(hours=1))
    assert within is not None
    assert within["reason"] == "cooldown"
    assert await service.is_suppressed(test_user.id, "comeback_nudge", now=now + timedelta(hours=1))

    # 窗口边界语义：>= IGNORE_TODAY_COOLDOWN_HOURS 后恢复。
    after = now + timedelta(hours=IGNORE_TODAY_COOLDOWN_HOURS, seconds=1)
    assert await service.get_suppression(test_user.id, "comeback_nudge", now=after) is None
    assert await service.is_suppressed(test_user.id, "comeback_nudge", now=after) is False


@pytest.mark.asyncio
async def test_mute_type_suppresses_indefinitely_and_is_type_isolated(db, test_user):
    """mute this type：持久静音；只静音点中的类型，不外溢。"""
    from app.services.proactive_suggestion_service import (
        ProactiveSuggestionFeedbackService,
    )

    service = ProactiveSuggestionFeedbackService(db)
    now = datetime.now(UTC).replace(tzinfo=None)

    await service.record_mute(test_user.id, "comeback_nudge", now=now)

    far_future = now + timedelta(days=365)
    muted = await service.get_suppression(test_user.id, "comeback_nudge", now=far_future)
    assert muted is not None
    assert muted["reason"] == "muted"

    # 其他类型不受影响。
    other = await service.get_suppression(test_user.id, "sprint_reminder", now=far_future)
    assert other is None


@pytest.mark.asyncio
async def test_suppression_state_survives_new_service_instance(db, test_user):
    """抑制态持久在 DB（UserPreferencesCenter），不是内存态：新实例仍可读。"""
    from app.services.proactive_suggestion_service import (
        ProactiveSuggestionFeedbackService,
    )

    now = datetime.now(UTC).replace(tzinfo=None)
    await ProactiveSuggestionFeedbackService(db).record_mute(test_user.id, "comeback_nudge", now=now)

    fresh = ProactiveSuggestionFeedbackService(db)
    assert await fresh.is_suppressed(test_user.id, "comeback_nudge", now=now)


@pytest.mark.asyncio
async def test_no_feedback_means_not_suppressed(db, test_user):
    from app.services.proactive_suggestion_service import (
        ProactiveSuggestionFeedbackService,
    )

    service = ProactiveSuggestionFeedbackService(db)
    assert await service.is_suppressed(test_user.id, "comeback_nudge") is False


# ── 四要素 payload：why_now / suggested_action 事实性、零 guilt ───────────────


def test_build_suggestion_elements_uses_plan_facts_not_guilt():
    from app.services.proactive_suggestion_service import build_suggestion_elements

    payload = {
        "subject": "计算机网络",
        "days_remaining": 3,
        "next_task_title": "TCP 流量控制",
        "recent_task_summary": "TCP 拥塞控制",
        "light_restart_suggestion": "先开一个「30分钟保底版」，把「TCP 流量控制」推进到一个最小闭环。",
        "goal_state": {"goal_id": "g1", "ledger": {"completed": 1, "total": 4}},
    }
    elements = build_suggestion_elements(payload)

    assert elements["why_now"].strip()
    # why-now 是事实性解释：包含目标名与剩余窗口，不指向人。
    assert "计算机网络" in elements["why_now"]
    assert "3" in elements["why_now"]
    assert elements["suggested_action"] == payload["light_restart_suggestion"]

    for text in elements.values():
        _assert_guilt_free(text)


def test_build_suggestion_elements_expired_plan_is_honest_without_pressure():
    """窗口已结束：如实呈报，不用“还来得及”一类压力话术（A-07 口径延续）。"""
    from app.services.proactive_suggestion_service import build_suggestion_elements

    elements = build_suggestion_elements(
        {
            "subject": "考研数学",
            "days_remaining": 0,
            "plan_expired": True,
            "next_task_title": "线性代数第二轮",
            "goal_state": {},
        }
    )
    _assert_guilt_free(elements["why_now"])
    # 兜底 suggested_action 指向具体下一步，不是空话。
    assert elements["suggested_action"].strip()


def test_build_suggestion_elements_minimal_payload_stays_factual():
    from app.services.proactive_suggestion_service import build_suggestion_elements

    elements = build_suggestion_elements({"subject": "", "days_remaining": None})
    _assert_guilt_free(elements["why_now"])
    assert elements["why_now"].strip()
    assert elements["suggested_action"].strip()


# ── deep link：Goal 页优先（读侧 goal_state.goal_id，不误用 plan_id） ─────────


def test_resolve_comeback_destination_prefers_goal_page():
    from app.services.proactive_suggestion_service import resolve_comeback_destination

    route = resolve_comeback_destination(
        {
            "plan_id": "plan-1",
            "goal_state": {"goal_id": "goal-9"},
        }
    )
    assert route == "/goals/goal-9?source=comeback_nudge"


def test_resolve_comeback_destination_falls_back_to_plan_page():
    from app.services.proactive_suggestion_service import resolve_comeback_destination

    route = resolve_comeback_destination({"plan_id": "plan-1", "goal_state": {}})
    assert route == "/plans/plan-1?source=comeback_nudge"


def test_resolve_comeback_destination_final_fallback_is_chat():
    from app.services.proactive_suggestion_service import resolve_comeback_destination

    assert resolve_comeback_destination({"plan_id": "", "goal_state": {}}) == "/chat?entry=comeback_nudge"


# ── NudgeService 通用 nudge 通道同样遵守 mute/cooldown（真实 DB 投递路径） ─────


@pytest.mark.asyncio
async def test_nudge_service_respects_mute_before_delivery(db, test_user):
    """mute this type 后，事件驱动的 nudge 通道不再为该类型投递任何通知。"""
    from sqlalchemy import select

    from app.models.notification import Notification
    from app.services.nudge_service import NudgeService
    from app.services.proactive_suggestion_service import (
        ProactiveSuggestionFeedbackService,
    )

    await ProactiveSuggestionFeedbackService(db).record_mute(test_user.id, "micro_restart")

    await NudgeService(db).handle_nudge_triggered(
        {
            "user_id": str(test_user.id),
            "type": "micro_restart",
            "message": "有一个 5 分钟的小重启建议。",
            "context": {},
        }
    )

    rows = (await db.execute(select(Notification).where(Notification.user_id == test_user.id))).scalars().all()
    assert rows == [], "muted nudge type must not create any notification"


@pytest.mark.asyncio
async def test_nudge_service_delivers_unmuted_type(db, test_user):
    """对照组：未静音类型照常入应用内通知中心（抑制不误伤）。"""
    from sqlalchemy import select

    from app.models.notification import Notification
    from app.services.nudge_service import NudgeService

    await NudgeService(db).handle_nudge_triggered(
        {
            "user_id": str(test_user.id),
            "type": "concept_gap_focus",
            "message": "有一个值得看的概念缺口。",
            "context": {},
        }
    )

    rows = (
        (
            await db.execute(
                select(Notification).where(
                    Notification.user_id == test_user.id,
                    Notification.type == "system",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].data.get("nudge_type") == "concept_gap_focus"
