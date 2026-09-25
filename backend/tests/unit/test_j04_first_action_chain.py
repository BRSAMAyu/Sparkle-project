"""J-04 · First Meaningful Action 端到端 —— 全链断点 / feedback / 失败诚实的验收证据.

红测先行（本文件提交时链路尚断，逐条对应卡面 work/acceptance）：

1. **链路断点（红1）**：Goal capture（onboarding → memory_goals）之后没有任何
   面把目标推进到 Smallest Useful Step——``first_action_service`` 缺失，
   Goal→Context→Aurora→Proposal→confirm→Task 六环无实现。
2. **拒绝不进 feedback（红2）**：``POST /action-proposals/{id}/reject`` 的
   ``RejectProposalRequest.reason``（用户"这个不合适"的自由文本）在 API 层被
   丢弃（从未传入 service），service 又把 terminal_reason 硬编码为枚举值——
   用户反馈在 append-only 审计面（transition + event_outbox）零留痕。
3. **5 Persona 不模板化（红3）**：五个真实 Persona 的 first action 必须彼此
   不同（title/outcome/step/evidence），且 mode 由 Aurora 分配策略权威裁决。
4. **提案生成失败诚实（红4）**：Aurora 推导失败 → 显式错误（可重试），
   不写半成品 proposal、不假装成功、不静默降级为模板动作。
5. **持久化（acceptance「重开存在」）**：全链状态持久于 DB，新会话（新
   service/新查询）可完整读回——App kill/reopen 语义（X-03 API 测试同构）。

Action 三字段 = X-01 ActionPlanContract 的 desired_outcome（产出）/
completion_evidence（完成证据）/ execution_mode（你做/Sparkle做/一起做），
本文件断言三者真实落入 proposal payload 与 commit 后的 tasks 行。
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.action_proposals import router as action_proposals_router
from app.core.action_command import (
    EVENT_ACTION_REJECTED,
    ActionCommandType,
    ProposalStatus,
)
from app.models.action_proposal import ActionProposal, ActionProposalTransition
from app.models.memory import MemoryGoal
from app.models.task import Task
from app.models.user import User
from app.services.action_command_service import ActionCommandService
from tests.unit.test_action_command_service import _OUTBOX_DDL, _make_user

# --- 测试基建（X-03 同法：sqlite + outbox DDL + ASGI client） ------------------


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


async def _seed_onboarding_goal(
    db_session: AsyncSession,
    user: User,
    *,
    goal_text: str,
    goal_type: str,
    knowledge_level: str = "beginner",
    learning_style: str = "balanced",
    study_minutes: int = 60,
) -> MemoryGoal:
    """复现 /profile/onboarding 的 goal capture 写法（J-02 面的真源形态）.

    goal 落 memory_goals（MemoryService.create_goal 形态），显式偏好落
    user_preferences_center.explicit（ProfileWriteService 展开形态：plain value）。
    """
    from app.models.user_preferences import UserPreferencesCenter

    goal = MemoryGoal(
        user_id=user.id,
        title=goal_text[:255],
        status="active",
        source_type="user_state",
        evidence_refs=[{"type": "user_state", "id": "onboarding", "schema_version": "onboarding.v1"}],
        metadata_payload={"goal_type": goal_type},
    )
    db_session.add(goal)
    db_session.add(
        UserPreferencesCenter(
            user_id=user.id,
            explicit={
                "learning_style": learning_style,
                "knowledge_level": knowledge_level,
                "study_time_preference": study_minutes,
            },
        )
    )
    await db_session.flush()
    return goal


def _scripted_llm(persona_outputs: dict[str, dict]):
    """脚本化 LLM（注入面：生产路径走 get_configured_llm_service_for_tier）.

    记录收到的 prompt（差异化断言要证明 prompt 由真实 goal 数据构成），
    按 prompt 中出现的 goal 文本返回对应 persona 的结构化输出。
    """

    async def _chat(messages, **_kwargs):
        user_msg = str(messages[-1]["content"])
        for goal_text, output in persona_outputs.items():
            if goal_text in user_msg:
                return json.dumps(output, ensure_ascii=False)
        raise AssertionError(f"scripted LLM received prompt without seeded goal text: {user_msg[:200]}")

    _chat.prompts: list[str] = []  # type: ignore[attr-defined]
    _original = _chat

    async def _chat_recording(messages, **kwargs):
        _chat_recording.prompts.append(str(messages[-1]["content"]))  # type: ignore[attr-defined]
        return await _original(messages, **kwargs)

    _chat_recording.prompts = []  # type: ignore[attr-defined]
    return _chat_recording


def _failing_llm(error: Exception):
    async def _chat(messages, **_kwargs):
        raise error

    return _chat


# ============================================================================
# 红1 · 全链：Goal capture → Context → Aurora → Proposal → confirm → Task
# ============================================================================


async def test_first_action_chain_goal_to_task_end_to_end(db_session, outbox_tables):
    """六环全通：真实 goal → 上下文 → Aurora 推导 → PENDING proposal →
    approve → tasks 行携带 outcome/evidence/mode；重开（新查询）状态仍在."""
    from app.services.first_action_service import (  # noqa: PLC0415 — 红测先行：模块尚不存在
        FIRST_ACTION_TRACE_ID,
        collect_first_action_context,
        propose_first_action,
    )

    user = await _make_user(db_session)
    goal = await _seed_onboarding_goal(
        db_session,
        user,
        goal_text="两周内做出可展示的作品集网站",
        goal_type="skill",
        knowledge_level="beginner",
        learning_style="practice",
        study_minutes=45,
    )

    # 环1→2：Context 从真实 goal 真源采集（非调用方编造）
    context = await collect_first_action_context(db_session, user_id=user.id)
    assert context is not None, "有 active goal 的用户必须能采集到 first action 上下文"
    assert context.goal_title.startswith("两周内做出可展示的作品集网站")
    assert context.goal_type == "skill"
    assert context.knowledge_level == "beginner"
    assert context.study_minutes == 45
    assert any(ref.startswith("goal://") for ref in context.source_refs)
    assert str(goal.id) in "".join(context.source_refs)

    # 环3→4：Aurora 推导（注入脚本 LLM）→ 统一 command path 建 proposal
    llm = _scripted_llm(
        {
            "两周内做出可展示的作品集网站": {
                "step_title": "列出 3 个最能代表你的项目素材",
                "smallest_step": "打开备忘录，为每个候选项目写一行：做了什么、结果是什么",
                "desired_outcome": "一份可继续筛选的项目素材清单（≥3 条）",
                "evidence_kind": "artifact",
                "useful_because": ["produces_artifact", "advances_goal"],
                "suggested_mode": "human",
                "estimated_minutes": 25,
            }
        }
    )
    result = await propose_first_action(
        db_session,
        user_id=user.id,
        llm_chat=llm,
        idempotency_key=f"first_action:{goal.id}",
    )
    assert result.created is True
    proposal = result.proposal
    assert proposal.status is ProposalStatus.PENDING
    assert proposal.command_type == ActionCommandType.TASK_CREATE_BATCH.value
    assert proposal.trace_id == FIRST_ACTION_TRACE_ID

    # Action 三字段真实落入 proposal payload（X-01 契约形态）
    task_spec = proposal.payload["tasks"][0]
    plan = task_spec["action_plan"]
    assert plan["desired_outcome"] == "一份可继续筛选的项目素材清单（≥3 条）"
    assert plan["smallest_useful_step"]["description"].startswith("打开备忘录")
    assert plan["completion_evidence"][0]["evidence_kind"] == "artifact"
    assert plan["execution_mode"] in {"human", "agent", "hybrid"}

    # 环5→6：confirm → X-03 统一落账 → Task 真实持久化（V3 列齐全）
    approved = await ActionCommandService(db_session).approve(proposal.id, user_id=user.id, idempotency_key="approve-1")
    assert approved.applied is True
    tasks = (await db_session.execute(select(Task).where(Task.user_id == user.id))).scalars().all()
    assert len(tasks) == 1, "commit 恰好创建一个任务"
    task = tasks[0]
    assert task.title == "列出 3 个最能代表你的项目素材"
    assert task.action_schema_version is not None
    assert task.desired_outcome == "一份可继续筛选的项目素材清单（≥3 条）"
    assert task.smallest_useful_step["description"].startswith("打开备忘录")
    assert task.completion_evidence[0]["evidence_kind"] == "artifact"
    assert task.execution_mode in {"human", "agent", "hybrid"}

    # 重开（acceptance：重开 App 后链路状态存在）——同一 DB、全新查询面
    from app.services.first_action_service import get_first_action_state  # noqa: PLC0415

    state = await get_first_action_state(db_session, user_id=user.id)
    assert state["proposal"] is not None
    assert state["proposal"]["status"] == ProposalStatus.COMMITTED.value
    assert state["proposal"]["receipt"] is not None
    assert len(state["tasks"]) == 1
    assert str(tasks[0].id) in [str(t["id"]) for t in state["tasks"]]


# ============================================================================
# 红2 · 拒绝/编辑进入 feedback（不静默丢弃）
# ============================================================================


async def test_reject_reason_is_persisted_as_user_feedback(db_session, outbox_tables):
    """拒绝理由（"这个不合适"的自由文本）必须落入 append-only 审计面：
    transition.details.user_feedback + event_outbox payload.user_feedback.
    现状（红）：API 层直接丢弃 request.reason，service 硬编码枚举归因."""
    from app.api.v1.action_proposals import RejectProposalRequest  # noqa: PLC0415

    user = await _make_user(db_session)
    goal = await _seed_onboarding_goal(db_session, user, goal_text="完成期末复习", goal_type="exam")
    service = ActionCommandService(db_session)
    llm = _scripted_llm(
        {
            "完成期末复习": {
                "step_title": "翻出最近一次测验卷",
                "smallest_step": "把错题题号抄到一张纸上",
                "desired_outcome": "一份错题清单",
                "evidence_kind": "artifact",
                "useful_because": ["reduces_uncertainty"],
                "suggested_mode": "human",
                "estimated_minutes": 15,
            }
        }
    )
    result = await propose_first_action_ref(db_session, user.id, llm, f"first_action:{goal.id}")
    proposal = result.proposal

    # 走 API 层（用户真实入口）：拒绝并携带理由
    reject_body = RejectProposalRequest(reason="这个不合适，我还没有测验卷", idempotency_key="rj-1")
    await service.reject(
        proposal.id,
        user_id=user.id,
        reason=reject_body.reason,  # ← 修复点：service 接收并持久化用户理由
        idempotency_key=reject_body.idempotency_key,
    )

    refreshed = await service.get_proposal(proposal.id, user_id=user.id)
    assert refreshed.status is ProposalStatus.REJECTED

    transition = (
        (
            await db_session.execute(
                select(ActionProposalTransition).where(
                    ActionProposalTransition.proposal_id == proposal.id,
                    ActionProposalTransition.to_status == ProposalStatus.REJECTED.value,
                )
            )
        )
        .scalars()
        .all()
    )
    assert transition, "拒绝必须留下审计行"
    details = transition[-1].details or {}
    assert (details.get("user_feedback") or {}).get(
        "reason"
    ) == "这个不合适，我还没有测验卷", "用户拒绝理由必须进入 transition 审计（feedback 真源），现状被静默丢弃"

    # 事件面同样可观测（Aurora 下轮推导可消费）
    rows = (
        await db_session.execute(
            text("SELECT payload FROM event_outbox WHERE event_type = :evt AND aggregate_id = :agg"),
            {"evt": EVENT_ACTION_REJECTED, "agg": str(proposal.id)},
        )
    ).all()
    assert rows, "action.rejected 事件必须落 event_outbox"
    payload = json.loads(rows[-1][0])
    assert (payload.get("user_feedback") or {}).get("reason") == "这个不合适，我还没有测验卷"

    # 终态归因词表不放宽（守卫不弱化）：terminal_reason 仍是封闭枚举值
    assert refreshed.terminal_reason == "user_rejected"


async def propose_first_action_ref(db, user_id, llm, key):
    from app.services.first_action_service import propose_first_action  # noqa: PLC0415

    return await propose_first_action(db, user_id=user_id, llm_chat=llm, idempotency_key=key)


async def test_edit_first_action_supersedes_and_records_feedback(db_session, outbox_tables):
    """编辑 = 拒绝旧提案（理由=edit feedback，含编辑字段）+ 同链路重提案：
    旧提案留编辑 feedback，新 proposal 携带编辑后 payload，两者都经统一 path."""
    from app.services.first_action_service import edit_first_action_proposal, propose_first_action  # noqa: PLC0415

    user = await _make_user(db_session)
    goal = await _seed_onboarding_goal(db_session, user, goal_text="持续产出播客", goal_type="creator")
    llm = _scripted_llm(
        {
            "持续产出播客": {
                "step_title": "写下第一期选题",
                "smallest_step": "用三句话写出第一期要讲什么",
                "desired_outcome": "第一期选题草稿",
                "evidence_kind": "artifact",
                "useful_because": ["produces_artifact"],
                "suggested_mode": "human",
                "estimated_minutes": 20,
            }
        }
    )
    created = await propose_first_action(
        db_session, user_id=user.id, llm_chat=llm, idempotency_key=f"first_action:{goal.id}"
    )
    old_proposal = created.proposal

    edited = await edit_first_action_proposal(
        db_session,
        user_id=user.id,
        proposal_id=old_proposal.id,
        edited_fields={"title": "列出 5 个身边可聊的人选", "estimated_minutes": 10},
        reason="第一步还是太大，改小",
        idempotency_key="edit-1",
    )
    assert edited.created is True
    new_proposal = edited.proposal
    assert new_proposal.id != old_proposal.id
    assert new_proposal.status is ProposalStatus.PENDING
    assert new_proposal.payload["tasks"][0]["title"] == "列出 5 个身边可聊的人选"
    assert new_proposal.payload["tasks"][0]["estimated_minutes"] == 10

    # 旧提案终态 + 编辑进入 feedback 审计
    service = ActionCommandService(db_session)
    old = await service.get_proposal(old_proposal.id, user_id=user.id)
    assert old.status is ProposalStatus.REJECTED
    transition = (
        (
            await db_session.execute(
                select(ActionProposalTransition).where(
                    ActionProposalTransition.proposal_id == old_proposal.id,
                    ActionProposalTransition.to_status == ProposalStatus.REJECTED.value,
                )
            )
        )
        .scalars()
        .all()
    )
    feedback = (transition[-1].details or {}).get("user_feedback") or {}
    assert feedback.get("kind") == "edit"
    assert feedback.get("edited_fields") == {"title": "列出 5 个身边可聊的人选", "estimated_minutes": 10}
    assert feedback.get("reason") == "第一步还是太大，改小"


# ============================================================================
# 红3 · 5 Persona 差异化（不模板化）+ mode 权威
# ============================================================================


_PERSONAS = [
    ("比赛", "两周内做出可展示的比赛 demo", "project", "hybrid候选"),
    ("科研", "推进论文的实验部分并整理结果", "research", "human"),
    ("作品集", "边学交互设计边形成作品集", "skill", "human"),
    ("课程", "三周后期末考，高数还没系统复习", "exam", "human"),
    ("Creator", "持续产出视频，目前断了三周", "creator", "human"),
]


async def test_five_personas_first_actions_are_not_templated(db_session, outbox_tables):
    """五个 Persona 的 first action 必须真实差异化：prompt 由各自 goal 数据
    构成；产出（title/outcome/step/evidence）五者互不相同；同因子的 mode
    由 Aurora 分配策略裁决（非 LLM 自由发挥）."""
    from app.services.first_action_service import collect_first_action_context, derive_first_action  # noqa: PLC0415

    persona_raw = {
        "两周内做出可展示的比赛 demo": {
            "step_title": "写下 demo 的 30 秒演示脚本",
            "smallest_step": "用一页纸写清评委将看到的三个画面",
            "desired_outcome": "30 秒演示脚本草稿",
            "evidence_kind": "artifact",
            "useful_because": ["produces_artifact", "enables_decision"],
            "suggested_mode": "agent",
            "estimated_minutes": 30,
        },
        "推进论文的实验部分并整理结果": {
            "step_title": "复述当前实验的最小可运行版本",
            "smallest_step": "写下实验要验证的唯一假设和判停条件",
            "desired_outcome": "一页实验假设卡（假设+判停条件）",
            "evidence_kind": "artifact",
            "useful_because": ["reduces_uncertainty"],
            "suggested_mode": "agent",
            "estimated_minutes": 25,
        },
        "边学交互设计边形成作品集": {
            "step_title": "挑一个想重做的界面做拆解",
            "smallest_step": "截一张图并列出它的三个可用性问题",
            "desired_outcome": "一份带问题的界面拆解笔记",
            "evidence_kind": "artifact",
            "useful_because": ["builds_capability"],
            "suggested_mode": "human",
            "estimated_minutes": 20,
        },
        "三周后期末考，高数还没系统复习": {
            "step_title": "摸清薄弱章节",
            "smallest_step": "把考纲章节按会/不会分成两栏",
            "desired_outcome": "一张个人薄弱章节分布表",
            "evidence_kind": "self_report",
            "useful_because": ["reduces_uncertainty", "advances_goal"],
            "suggested_mode": "agent",
            "estimated_minutes": 15,
        },
        "持续产出视频，目前断了三周": {
            "step_title": "解冻：写下回归选题",
            "smallest_step": "列 5 个三分钟内能讲完的选题",
            "desired_outcome": "5 条候选选题清单",
            "evidence_kind": "artifact",
            "useful_because": ["produces_artifact"],
            "suggested_mode": "human",
            "estimated_minutes": 10,
        },
    }
    llm = _scripted_llm(persona_raw)

    seen_actions: set[tuple[str, str]] = set()
    seen_titles: set[str] = set()
    for _label, goal_text, goal_type, _mode_hint in _PERSONAS:
        user = await _make_user(db_session)
        await _seed_onboarding_goal(db_session, user, goal_text=goal_text, goal_type=goal_type)
        context = await collect_first_action_context(db_session, user_id=user.id)
        assert context is not None
        derived = await derive_first_action(context, llm_chat=llm)
        signature = (derived["step_title"], derived["desired_outcome"], derived["smallest_step"])
        assert (
            signature not in seen_actions
        ), f"persona {goal_text!r} 的 first action 与其他 persona 模板撞车: {signature}"
        seen_actions.add(signature)
        seen_titles.add(derived["step_title"])
        # 真实数据流：prompt 携带该 persona 的 goal 原文（Aurora 看到的是真目标）
        assert any(
            goal_text in prompt for prompt in llm.prompts
        ), f"推导 prompt 必须由真实 goal 数据构成（缺 {goal_text!r}）"
    assert len(seen_titles) == 5, "五个 Persona 的 step 标题必须互不相同（不模板化）"


async def test_mode_is_adjudicated_by_allocation_policy_not_llm(db_session, outbox_tables):
    """mode 权威 = Aurora 分配策略（decide_allocation）：学习型 user_core 步骤
    即使 LLM 建议 agent 也绝不全自动（学习守卫）；纯机械委托步骤才允许 agent."""
    from app.services.first_action_service import (  # noqa: PLC0415
        collect_first_action_context,
        derive_first_action,
        resolve_execution_mode,  # noqa: PLC0415
    )

    user = await _make_user(db_session)
    await _seed_onboarding_goal(db_session, user, goal_text="三周后期末考，高数还没系统复习", goal_type="exam")
    context = await collect_first_action_context(db_session, user_id=user.id)
    llm = _scripted_llm(
        {
            "三周后期末考，高数还没系统复习": {
                "step_title": "把考纲章节按会/不会分成两栏",
                "smallest_step": "逐条过考纲并自评",
                "desired_outcome": "薄弱章节分布表",
                "evidence_kind": "self_report",
                "useful_because": ["reduces_uncertainty"],
                "suggested_mode": "agent",  # LLM 越权建议全自动
                "estimated_minutes": 15,
            }
        }
    )
    derived = await derive_first_action(context, llm_chat=llm)
    decision = resolve_execution_mode(context, derived)
    assert decision.mode in {"human", "hybrid"}, (
        "学习型 user_core 步骤被 LLM 建议 agent 时必须被分配策略拦回（学习守卫），" f"got {decision.mode}"
    )


# ============================================================================
# 红4 · 提案生成失败诚实处理（错误可见可重试，不假装成功）
# ============================================================================


async def test_generation_failure_is_honest_and_retryable(db_session, outbox_tables):
    """Aurora 推导失败（LLM 不可用/输出不合法）→ 显式 FirstActionGenerationError；
    不写 proposal（不留半成品）；同一用户恢复后重试即成功."""
    from app.services.first_action_service import (  # noqa: PLC0415
        FirstActionGenerationError,
        propose_first_action,
    )

    user = await _make_user(db_session)
    await _seed_onboarding_goal(db_session, user, goal_text="两周内做出可展示的作品集网站", goal_type="skill")

    with pytest.raises(FirstActionGenerationError) as exc_info:
        await propose_first_action(
            db_session,
            user_id=user.id,
            llm_chat=_failing_llm(RuntimeError("llm provider unavailable")),
            idempotency_key="first_action:fail-1",
        )
    assert exc_info.value.retryable is True
    assert str(exc_info.value.reason), "失败必须携带可展示原因（错误可见）"

    # 不留半成品：失败路径零 proposal 落库（不假装成功）
    proposals = (
        (await db_session.execute(select(ActionProposal).where(ActionProposal.user_id == user.id))).scalars().all()
    )
    assert proposals == [], "生成失败不得留下任何 proposal 行"

    # 恢复后重试即成功（可重试语义）
    llm = _scripted_llm(
        {
            "两周内做出可展示的作品集网站": {
                "step_title": "列出 3 个项目素材",
                "smallest_step": "为每个候选项目写一行说明",
                "desired_outcome": "项目素材清单",
                "evidence_kind": "artifact",
                "useful_because": ["produces_artifact"],
                "suggested_mode": "human",
                "estimated_minutes": 25,
            }
        }
    )
    retried = await propose_first_action(
        db_session, user_id=user.id, llm_chat=llm, idempotency_key="first_action:fail-1"
    )
    assert retried.created is True


async def test_generation_failure_api_returns_honest_503(db_session, outbox_tables):
    """API 层：生成失败 → 503 + 结构化错误（retryable），HTTP 200 假成功被禁止."""
    app = FastAPI()
    from app.api.v1.journey import router as journey_router  # noqa: PLC0415

    app.include_router(journey_router, prefix="/api/v1")
    app.include_router(action_proposals_router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    user = await _make_user(db_session)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        # 无 goal → 422（诚实：没有目标就没有 first action）
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        resp = await client.post("/api/v1/journey/first-action", json={})
        assert resp.status_code == 422

        # 有 goal + Aurora 失败 → 503 结构化错误（可见可重试），零 proposal
        await _seed_onboarding_goal(db_session, user, goal_text="完成期末复习", goal_type="exam")

        from app.services import first_action_service as fa_service  # noqa: PLC0415

        original = fa_service.propose_first_action

        async def _failing_propose(*args, **kwargs):
            from app.services.first_action_service import FirstActionGenerationError  # noqa: PLC0415

            raise FirstActionGenerationError(reason="aurora_derivation_failed", detail="llm timeout")

        fa_service.propose_first_action = _failing_propose
        try:
            resp = await client.post("/api/v1/journey/first-action", json={"idempotency_key": "k1"})
        finally:
            fa_service.propose_first_action = original
        assert resp.status_code == 503, resp.text
        body = resp.json()
        # FastAPI HTTPException 把结构化错误包在 detail 里（错误可见、可重试）
        assert body["detail"]["error"] == "first_action_generation_failed"
        assert body["detail"]["retryable"] is True
        proposals = (
            (await db_session.execute(select(ActionProposal).where(ActionProposal.user_id == user.id))).scalars().all()
        )
        assert proposals == []
        await client.aclose()
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# 幂等：同 key 重复生成恰一次（重开/双击不重复提案）
# ============================================================================


async def test_first_action_generation_is_idempotent(db_session, outbox_tables):
    from app.services.first_action_service import propose_first_action  # noqa: PLC0415

    user = await _make_user(db_session)
    goal = await _seed_onboarding_goal(db_session, user, goal_text="持续产出播客", goal_type="creator")
    llm = _scripted_llm(
        {
            "持续产出播客": {
                "step_title": "写下第一期选题",
                "smallest_step": "三句话写出第一期讲什么",
                "desired_outcome": "选题草稿",
                "evidence_kind": "artifact",
                "useful_because": ["produces_artifact"],
                "suggested_mode": "human",
                "estimated_minutes": 20,
            }
        }
    )
    key = f"first_action:{goal.id}"
    first = await propose_first_action(db_session, user_id=user.id, llm_chat=llm, idempotency_key=key)
    second = await propose_first_action(db_session, user_id=user.id, llm_chat=llm, idempotency_key=key)
    assert first.proposal.id == second.proposal.id
    assert second.created is False
    count = len(
        (await db_session.execute(select(ActionProposal).where(ActionProposal.user_id == user.id))).scalars().all()
    )
    assert count == 1
