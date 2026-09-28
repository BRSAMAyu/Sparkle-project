"""V4-I07 · 学习/交付目标的人机权限与脚手架 —— 验收可失败面测试。

对应卡验收三条（每条一正一反；RED 证据：本卡之前 ``human_mastery_settlement``
/``redact_independent_check``/``next_scaffold_step`` 全仓不存在——
``grep -rn "human_mastery_settlement" backend/app`` → 0 命中，mastery 结算面
（``TaskService._update_sprint_pack_mastery_for_completed_task``）对完成来源
零判定：agent 代执行与用户亲手完成同额 +25 节点掌握）。

- 验收①（学会目标中 Agent 代答不能结算人类掌握）：结算门 BLOCK 面 +
  TaskService.complete 集成（sprint 掌握写面 spy 不触发，任务完成/outcome 照常）；
- 验收②（交付目标允许合法代办，不强迫用户手工重复）：deliverable 目标
  （声明块或 delegated 推导）agent 完成照常结算 + X-02 分配面 agent 可行；
  human_required 声明仍守（G5/G1 反例）；
- 验收③（独立检验答案不出现在可见/可检索上下文）：红化门 + 泄漏探针 +
  chat 上下文投影入口（``task_guide_context_projection``）；
- 脚手架链（示例→尝试→独立检验 + 提示渐隐）：冻结转移表逐规则正反例。

词表纪律：derive_goal_purpose 与 X-02 ``LEARNING_TASK_TYPES`` 同集防漂移测试；
SETTLEMENT_REASONS / SCAFFOLD_TRANSITION_REASONS / INDEPENDENT_CHECK_ANSWER_KEYS
精确集冻结。
"""

from __future__ import annotations

from typing import Any

import pytest

from app.core.hybrid_policy import (
    GOAL_PURPOSE_BLOCK_KEY,
    GOAL_PURPOSE_DELIVERABLE,
    GOAL_PURPOSE_MASTERY,
    GOAL_PURPOSE_MIXED,
    GOAL_PURPOSES,
    HINT_LEVELS,
    INDEPENDENT_CHECK_ANSWER_KEYS,
    SCAFFOLD_STAGES,
    SCAFFOLD_TRANSITION_REASONS,
    SETTLEMENT_REASONS,
    apply_scaffold_decision,
    contains_independent_check_answer,
    derive_goal_purpose,
    human_mastery_settlement,
    next_scaffold_step,
    parse_policy_block,
    redact_independent_check,
    resolve_step_purpose,
    settlement_for_task_row,
    task_guide_context_projection,
)
from app.models.task import CognitiveOwnership, Task, TaskStatus, TaskType
from app.services.action_allocation_policy import (
    ALLOCATION_POLICY_VERSION,
    LEARNING_TASK_TYPES,
    AllocationFactors,
    decide_allocation,
    vet_agent_offer,
)
from app.services.task_service import TaskService


def _policy_block(**overrides: Any) -> dict[str, Any]:
    block = {
        "schema_version": "hybrid_policy.v1",
        "goal_purpose": GOAL_PURPOSE_MASTERY,
        "human_required": True,
    }
    block.update(overrides)
    return {GOAL_PURPOSE_BLOCK_KEY: block}


class _FakeTask:
    """settlement_for_task_row 的最小行投影（无需 DB）。"""

    def __init__(self, task_type: Any = TaskType.TRAINING, cognitive_ownership: Any = None, guide_json: Any = None):
        self.type = task_type
        self.cognitive_ownership = cognitive_ownership
        self.guide_json = guide_json


# ---------------------------------------------------------------------------
# 验收①：学会目标中 Agent 代答不能结算人类掌握
# ---------------------------------------------------------------------------


def test_agent_on_human_required_mastery_step_cannot_settle():
    """反例（验收①核心）：human_required 步骤被 agent 完成 → 结算被拒。"""
    verdict = human_mastery_settlement(goal_purpose=GOAL_PURPOSE_MASTERY, human_required=True, completed_by="agent")
    assert verdict.allowed is False
    assert verdict.reason == "BLOCK.agent_completed_human_required_mastery"


def test_agent_on_mastery_goal_step_cannot_settle_even_unmarked():
    """mastery 目标中未标 human_required 的步骤被 agent 完成 → 仍不结算
    （mastery 目标里 Agent 只准备，不产出人类掌握）。"""
    verdict = human_mastery_settlement(goal_purpose=GOAL_PURPOSE_MASTERY, human_required=False, completed_by="agent")
    assert verdict.allowed is False
    assert verdict.reason == "BLOCK.agent_completed_mastery_step"


def test_legacy_learning_task_agent_completion_blocked_by_derivation():
    """legacy 行（无策略块）按 X-02 同集推导：TRAINING → mastery → agent 拒。"""
    verdict = settlement_for_task_row(_FakeTask(task_type=TaskType.TRAINING), evidence_source="agent")
    assert verdict.allowed is False
    assert verdict.goal_purpose == GOAL_PURPOSE_MASTERY


def test_user_completion_settles_human_mastery():
    """正例：用户亲自完成 → 结算合法（行为保留）。"""
    verdict = human_mastery_settlement(goal_purpose=GOAL_PURPOSE_MASTERY, human_required=True, completed_by="user")
    assert verdict.allowed is True
    assert verdict.reason == "OK.human_authored_settlement"


def test_focus_timer_counts_as_user_source():
    """focus 计时器是用户自己的投入 → user（与 agent/system 区分）。"""
    verdict = settlement_for_task_row(
        _FakeTask(task_type=TaskType.TRAINING, guide_json=_policy_block()), evidence_source="focus_auto"
    )
    assert verdict.allowed is True
    assert verdict.completed_by == "user"


def test_settlement_reasons_frozen_exact_set():
    assert (
        frozenset(
            {
                "OK.human_authored_settlement",
                "OK.deliverable_delegation_settlement",
                "BLOCK.agent_completed_human_required_mastery",
                "BLOCK.agent_completed_mastery_step",
            }
        )
        == SETTLEMENT_REASONS
    )


def test_settlement_rejects_dirty_enum_input():
    with pytest.raises(ValueError):
        human_mastery_settlement(goal_purpose="master", human_required=True, completed_by="agent")
    with pytest.raises(ValueError):
        human_mastery_settlement(goal_purpose=GOAL_PURPOSE_MASTERY, human_required=True, completed_by="llm")


# ---------------------------------------------------------------------------
# 验收②：交付目标允许合法代办，不强迫用户手工重复
# ---------------------------------------------------------------------------


def test_deliverable_delegation_settles_normally():
    """正例（验收②）：deliverable 目标 agent 完成 → 照常结算。"""
    verdict = human_mastery_settlement(
        goal_purpose=GOAL_PURPOSE_DELIVERABLE, human_required=False, completed_by="agent"
    )
    assert verdict.allowed is True
    assert verdict.reason == "OK.deliverable_delegation_settlement"


def test_deliverable_declared_block_agent_completion_settles():
    verdict = settlement_for_task_row(
        _FakeTask(
            task_type=TaskType.LEARNING,
            guide_json=_policy_block(goal_purpose=GOAL_PURPOSE_DELIVERABLE, human_required=False),
        ),
        evidence_source="agent",
    )
    assert verdict.allowed is True, "声明交付目标的整理/制作可合法代办，完成即结算"


def test_deliverable_with_declared_human_required_still_blocked():
    """反例：交付目标里声明 human_required 的门，agent 代完成仍拒。"""
    verdict = settlement_for_task_row(
        _FakeTask(
            task_type=TaskType.PLANNING,
            guide_json=_policy_block(goal_purpose=GOAL_PURPOSE_DELIVERABLE, human_required=True),
        ),
        evidence_source="agent",
    )
    assert verdict.allowed is False
    assert verdict.reason == "BLOCK.agent_completed_human_required_mastery"


# ---------------------------------------------------------------------------
# 结算面集成：TaskService.complete（sprint 掌握写面 spy）
# ---------------------------------------------------------------------------


def _sprint_task(db_session, user_id, *, guide_json: dict[str, Any] | None = None) -> Task:
    return Task(
        user_id=user_id,
        title="泰勒展开真题闯关",
        type=TaskType.TRAINING,
        status=TaskStatus.IN_PROGRESS,
        estimated_minutes=40,
        guide_json=guide_json or {},
    )


@pytest.fixture
def _muted_bus(monkeypatch):
    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.task_service.event_bus_reliable.publish", _noop)
    monkeypatch.setattr("app.services.task_service.publish_srl_event", _noop)


@pytest.mark.asyncio
async def test_complete_by_agent_does_not_settle_sprint_mastery(db_session, test_user, _muted_bus, monkeypatch):
    """集成反例（验收①）：mastery 任务 agent 代完成 → 任务完成但掌握写面零触发。"""
    calls: list[tuple[Any, ...]] = []

    async def _spy_update(*args, **kwargs):
        calls.append((args, kwargs))

    async def _fake_states(user_id, node_ids):
        return {nid: {"mastery_score": 10.0, "revision": 1} for nid in node_ids}

    monkeypatch.setattr(
        "app.services.task_service.TaskService._update_sprint_pack_mastery_for_completed_task",
        _spy_update,
    )
    task = _sprint_task(
        db_session,
        test_user.id,
        guide_json=_policy_block(goal_purpose=GOAL_PURPOSE_MASTERY, human_required=True),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    completed = await TaskService.complete(db_session, task, actual_minutes=40, evidence_source="agent")

    assert completed.status == TaskStatus.COMPLETED, "完成事实照常记账（行动账本与掌握账本分离）"
    assert calls == [], "human_required 的 mastery 任务被 agent 完成时不得结算人类掌握"


@pytest.mark.asyncio
async def test_complete_by_user_still_settles_sprint_mastery(db_session, test_user, _muted_bus, monkeypatch):
    """集成正例：用户完成 → 掌握写面照常触发（行为保留，不误伤）。"""
    calls: list[tuple[Any, ...]] = []

    async def _spy_update(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(
        "app.services.task_service.TaskService._update_sprint_pack_mastery_for_completed_task",
        _spy_update,
    )
    task = _sprint_task(db_session, test_user.id)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    await TaskService.complete(db_session, task, actual_minutes=40, evidence_source="user")

    assert len(calls) == 1, "用户亲手完成照常结算人类掌握"


# ---------------------------------------------------------------------------
# 目的维度：解析 / 推导 / 逐步消解
# ---------------------------------------------------------------------------


def test_policy_block_parse_roundtrip_and_failclosed():
    block, degrade = parse_policy_block({"other": 1})
    assert block is None and degrade is None  # 无块 = legacy 正常态
    block, degrade = parse_policy_block(_policy_block())
    assert block is not None and degrade is None
    assert block.goal_purpose == GOAL_PURPOSE_MASTERY and block.human_required is True
    # 脏块 fail-closed：目的词表外 / human_required 非布尔 / 版本不符
    _, degrade = parse_policy_block(_policy_block(goal_purpose=" productivity"))
    assert degrade and "goal_purpose" in degrade
    _, degrade = parse_policy_block(_policy_block(human_required="yes"))
    assert degrade and "human_required" in degrade
    _, degrade = parse_policy_block(_policy_block(schema_version="hybrid_policy.v9"))
    assert degrade and "schema_version" in degrade


def test_derive_goal_purpose_matches_x02_learning_types():
    """防漂移：legacy 推导集 ≡ X-02 LEARNING_TASK_TYPES（单一事实源约束）。"""
    assert {TaskType.LEARNING.value, TaskType.TRAINING.value, TaskType.REFLECTION.value} == set(LEARNING_TASK_TYPES)
    assert derive_goal_purpose(TaskType.LEARNING, None) == GOAL_PURPOSE_MASTERY
    assert derive_goal_purpose("TRAINING", CognitiveOwnership.USER_CORE) == GOAL_PURPOSE_MASTERY
    assert derive_goal_purpose(TaskType.OCR, CognitiveOwnership.DELEGATED) == GOAL_PURPOSE_DELIVERABLE
    assert derive_goal_purpose(TaskType.PLANNING, None) == GOAL_PURPOSE_MIXED


def test_resolve_step_purpose_rules():
    # human_required 恒 mastery（任何目的下）
    assert resolve_step_purpose(GOAL_PURPOSE_DELIVERABLE, human_required=True) == GOAL_PURPOSE_MASTERY
    # mastery 目标的 delegated 准备步 → deliverable（Agent 准备示例/提示/检查合法）
    assert (
        resolve_step_purpose(GOAL_PURPOSE_MASTERY, human_required=False, cognitive_ownership="delegated")
        == GOAL_PURPOSE_DELIVERABLE
    )
    assert (
        resolve_step_purpose(GOAL_PURPOSE_MASTERY, human_required=False, cognitive_ownership="user_core")
        == GOAL_PURPOSE_MASTERY
    )
    # 未知 ownership 保守归 mastery
    assert (
        resolve_step_purpose(GOAL_PURPOSE_MASTERY, human_required=False, cognitive_ownership=None)
        == GOAL_PURPOSE_MASTERY
    )
    # deliverable 目标的 user_core 步骤 → mastery（该步本身即能力）
    assert (
        resolve_step_purpose(GOAL_PURPOSE_DELIVERABLE, human_required=False, cognitive_ownership="user_core")
        == GOAL_PURPOSE_MASTERY
    )


# ---------------------------------------------------------------------------
# 验收③：独立检验答案不出现在可见/可检索上下文
# ---------------------------------------------------------------------------


def _guide_with_check() -> dict[str, Any]:
    return {
        "focus_cue": "泰勒展开",
        GOAL_PURPOSE_BLOCK_KEY: {
            "schema_version": "hybrid_policy.v1",
            "goal_purpose": GOAL_PURPOSE_MASTERY,
            "human_required": True,
            "scaffold": {"stage": "independent_check", "hint_level": "none"},
            "independent_check": {
                "kind": "independent_check",
                "question": "求 f(x)=e^x 在 x=0 处的二阶泰勒展开",
                "answer": "1 + x + x^2/2",
                "solution_steps": ["展开到二阶", "e^x 的导数恒为自身"],
                "grading": {"correct_answer": "1 + x + x^2/2", "tolerance": 0},
            },
        },
    }


def test_independent_check_answer_redacted_from_projection():
    """验收③：投影入口剥除 independent_check 节点内全部答案键，题面保留。"""
    clean, scaffold, removed = task_guide_context_projection(_guide_with_check())
    assert contains_independent_check_answer(_guide_with_check()) is True, "红前载荷确含答案（反例锚定）"
    assert contains_independent_check_answer(clean) is False, "投影后无任何答案键残留"
    inner = clean[GOAL_PURPOSE_BLOCK_KEY]["independent_check"]
    assert inner["question"] == "求 f(x)=e^x 在 x=0 处的二阶泰勒展开", "题面/作答面保留"
    assert "solution_steps" in inner, "非答案键字段保留"
    assert "answer" not in inner and "answer" not in inner["grading"]
    assert any(p.endswith("answer") for p in removed) and any("grading" in p for p in removed)
    assert scaffold is not None and scaffold["stage"] == "independent_check", "脚手架面（非答案）照常投影"
    # 服务端本体不被改写（判分权威原地保留）
    assert _guide_with_check()[GOAL_PURPOSE_BLOCK_KEY]["independent_check"]["answer"] == "1 + x + x^2/2"


def test_answer_keys_outside_check_marker_untouched():
    """反例守护：非标记节点内的同名字段（用户自有材料）不受红化影响。"""
    payload = {
        "error_material": {"correct_answer": "用户自己的错题答案，不属独立检验面"},
        "notes": [{"answer": "普通笔记字段"}],
    }
    clean, removed = redact_independent_check(payload)
    assert removed == ()
    assert clean["error_material"]["correct_answer"].startswith("用户自己")
    assert clean["notes"][0]["answer"] == "普通笔记字段"


def test_flagged_subtree_answers_removed_recursively():
    payload = {
        "independent_check": True,
        "items": [{"prompt": "q1", "expected_answer": "a1"}, {"prompt": "q2", "answer_key": "a2"}],
    }
    clean, removed = redact_independent_check(payload)
    assert contains_independent_check_answer(clean) is False
    assert len(removed) == 2
    assert clean["items"][0]["prompt"] == "q1"


def test_independent_check_answer_keys_frozen():
    assert (
        frozenset(
            {
                "answer",
                "correct_answer",
                "expected_answer",
                "reference_answer",
                "model_answer",
                "solution",
                "answer_key",
            }
        )
        == INDEPENDENT_CHECK_ANSWER_KEYS
    )


# ---------------------------------------------------------------------------
# 脚手架链：示例 → 尝试 → 独立检验 + 提示渐隐
# ---------------------------------------------------------------------------


def test_scaffold_advance_requires_user_choice_and_evidence():
    """推进需要「用户选择 ∧ 证据支持」，缺一即原地（两条反例）。"""
    only_choice = next_scaffold_step(stage="example", hint_level="full", user_chose=True, evidence_supported=False)
    assert only_choice.stage == "example" and only_choice.reason == "HOLD.evidence_not_supported"
    only_evidence = next_scaffold_step(stage="example", hint_level="full", user_chose=False, evidence_supported=True)
    assert only_evidence.stage == "example" and only_evidence.reason == "OK.hint_fading_prior_example_sufficient"
    assert only_evidence.hint_level == "reduced", "前次示例充分 → 提示渐隐一档"
    neither = next_scaffold_step(stage="attempt", hint_level="none", user_chose=False, evidence_supported=False)
    assert neither.stage == "attempt" and neither.reason == "HOLD.user_did_not_choose"


def test_scaffold_chain_example_to_attempt_to_check():
    d1 = next_scaffold_step(stage="example", hint_level="full", user_chose=True, evidence_supported=True)
    assert (d1.stage, d1.reason) == ("attempt", "OK.advance_user_chose_with_evidence")
    assert d1.hint_level == "reduced", "推进即渐隐"
    d2 = next_scaffold_step(stage="attempt", hint_level="reduced", user_chose=True, evidence_supported=True)
    assert (d2.stage, d2.hint_level) == ("independent_check", "none"), "独立检验段零提示"


def test_scaffold_failure_adds_local_support_without_demotion():
    """尝试失败 → 提示档回升、阶段不回退（不把用户降级）。"""
    d = next_scaffold_step(
        stage="attempt", hint_level="none", user_chose=False, evidence_supported=False, attempt_failed=True
    )
    assert (d.stage, d.hint_level, d.reason) == ("attempt", "reduced", "SUPPORT.failure_adds_local_hint")
    d2 = next_scaffold_step(
        stage="attempt", hint_level="reduced", user_chose=False, evidence_supported=False, attempt_failed=True
    )
    assert d2.hint_level == "full", "连续失败继续回升支持"
    assert d2.stage == "attempt", "阶段永不回退"


def test_scaffold_independent_check_is_terminal():
    d = next_scaffold_step(
        stage="independent_check", hint_level="none", user_chose=True, evidence_supported=True, attempt_failed=True
    )
    assert d.stage == "independent_check" and d.reason == "OK.independent_check_reached"


def test_scaffold_rejects_dirty_state():
    with pytest.raises(ValueError):
        next_scaffold_step(stage="lecture", hint_level="full", user_chose=True, evidence_supported=True)
    with pytest.raises(ValueError):
        next_scaffold_step(stage="example", hint_level="max", user_chose=True, evidence_supported=True)


def test_scaffold_vocab_frozen_and_apply_roundtrip():
    assert frozenset({"example", "attempt", "independent_check"}) == SCAFFOLD_STAGES
    assert frozenset({"full", "reduced", "none"}) == HINT_LEVELS
    assert (
        frozenset(
            {
                "OK.advance_user_chose_with_evidence",
                "OK.hint_fading_prior_example_sufficient",
                "HOLD.user_did_not_choose",
                "HOLD.evidence_not_supported",
                "SUPPORT.failure_adds_local_hint",
                "OK.independent_check_reached",
            }
        )
        == SCAFFOLD_TRANSITION_REASONS
    )
    raw = _policy_block()
    decision = next_scaffold_step(stage="example", hint_level="full", user_chose=True, evidence_supported=True)
    updated = apply_scaffold_decision(raw, decision)
    block, degrade = parse_policy_block(updated)
    assert degrade is None and block is not None
    assert (block.scaffold.stage, block.scaffold.hint_level) == ("attempt", "reduced")


# ---------------------------------------------------------------------------
# X-02 分配面增量：goal_purpose / human_required 因子（hybrid-policy 锁）
# ---------------------------------------------------------------------------


def test_goal_purpose_vocab_reused_not_copied():
    from app.core.hybrid_policy import GOAL_PURPOSES as IMPORTED

    factors = AllocationFactors.coerce({"goal_purpose": "mastery"})
    assert factors.goal_purpose == "mastery"
    assert AllocationFactors.coerce({"goal_purpose": "learn"}).goal_purpose is None  # 脏值 → None 灰区
    assert IMPORTED == GOAL_PURPOSES


def test_x02_mastery_purpose_blocks_agent_deliverable_allows():
    """mastery 目的 → G1 生效 agent 不可行；deliverable 目的 → agent 可行（验收②分配面）。"""
    base = {
        "task_type": "LEARNING",
        "cognitive_ownership": "shared",
        "tool_advantage": "high",
        "risk_class": "low",
        "reversible": True,
        "embodiment_required": False,
        "privacy": "public",
        "confidence": 0.8,
        "explicit_intent": "delegate",
    }
    mastery = decide_allocation(AllocationFactors.coerce({**base, "goal_purpose": "mastery"}))
    assert mastery.mode != "agent" and "G1.learning_guard_no_agent" in mastery.why
    assert mastery.annotations["goal_purpose"] == "mastery"

    deliverable = decide_allocation(AllocationFactors.coerce({**base, "goal_purpose": "deliverable"}))
    assert deliverable.mode == "agent", "显式交付目标的整理/制作可合法代办"
    assert "G1.learning_guard_no_agent" not in deliverable.why


def test_x02_human_required_step_never_agent():
    """G5 反例：human_required=True 时 agent 不可行（显式委托也不翻盘）。"""
    factors = AllocationFactors.coerce(
        {
            "goal_purpose": "deliverable",
            "cognitive_ownership": "shared",
            "tool_advantage": "high",
            "explicit_intent": "delegate",
            "human_required": True,
        }
    )
    decision = decide_allocation(factors)
    assert "agent" not in decision.feasible_modes
    assert "G5.human_required_step_no_agent" in decision.why
    # vet 层同源：complete_answer 在 mastery/human_required 下仍拒（G3 路径保持）
    verdict = vet_agent_offer("complete_answer", AllocationFactors.coerce({"goal_purpose": "mastery"}))
    assert verdict.allowed is False


def test_x02_version_bumped_for_v12():
    assert ALLOCATION_POLICY_VERSION == "allocation.v1.2"
