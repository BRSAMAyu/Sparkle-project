"""X-02 防代写守卫（anti-deskilling）—— 红绿纪律的专项测试。

RED 态证据（2026-09-19，本文件首轮）：
    无 rubric 时模型可随意「我来帮你做」——仓库内在本卡之前不存在任何
    allocation/delegation rubric（grep -r "allocation_policy|delegation rubric"
    backend/app → 0 命中），学习型任务的 mode 与 Agent 供给形态完全由 LLM
    自由裁量。下方 ``FreeformAgentBaseline`` mock 把这一现状固化为对照物：
    对 LEARNING 任务它同样返回 agent + complete_answer（现状=可代写）。
    首轮红跑：app.services.action_allocation_policy 尚不存在 →
    ModuleNotFoundError（真红，与 X-01 红态证据口径一致）。

GREEN 态：rubric 落地后，学习型任务（task_type=LEARNING / cognitive_ownership
=user_core / learning_goal）在任何偏好组合下：
    ① mode 永不为 agent（feasible set 剔除，G1）；
    ② hybrid 必须携带 user-authored 完成证据要求（G2）；
    ③ Agent「直接写完整答案」路径被拒（G3），user_core 下 draft 也被拒（G4）。
"""

from __future__ import annotations

import pytest

from app.services.action_allocation_policy import (
    AllocationFactors,
    decide_allocation,
    vet_agent_offer,
)

# 学习型任务的典型因子（默认偏好：无显式意图、无持久偏好——「默认」态）
LEARNING_FACTORS = AllocationFactors(
    task_type="LEARNING",
    task_summary="完成《计算机网络》第三章课后习题，掌握滑动窗口原理",
    cognitive_ownership="user_core",
    tool_advantage="high",  # AI 检索/讲解确有优势——但能力建构属用户
    risk_class="low",
    reversible=True,
    explicit_intent=None,
    embodiment_required=False,
    privacy="public",
    confidence=0.8,
    time_pressure="relaxed",
    user_preference=None,
)


class FreeformAgentBaseline:
    """现状对照 mock：无 rubric 约束的 LLM 自由裁量（「我来帮你做」倾向）。

    对任何任务（含学习型）都倾向 agent 全自动 + 直接交付完整答案。
    这不是假设——是本卡之前仓库内唯一的行为模式（无任何 policy 拦截）。
    """

    def decide(self, factors: AllocationFactors) -> str:
        return "agent"

    def offer(self, factors: AllocationFactors) -> str:
        return "complete_answer"


def test_baseline_mock_documents_the_threat():
    """对照物自证：现状下学习型任务确实会被 agent 代写（threat 真实存在）。"""
    baseline = FreeformAgentBaseline()
    assert baseline.decide(LEARNING_FACTORS) == "agent"
    assert baseline.offer(LEARNING_FACTORS) == "complete_answer"


@pytest.mark.parametrize(
    "label,factors",
    [
        ("task_type=LEARNING", LEARNING_FACTORS),
        (
            "cognitive_ownership=user_core",
            AllocationFactors(
                task_summary="撰写课程期末论文第一稿",
                cognitive_ownership="user_core",
                tool_advantage="high",
                risk_class="low",
            ),
        ),
        (
            "learning_goal=True",
            AllocationFactors(
                task_summary="备考四级：自己完成一套真题并复盘",
                learning_goal=True,
                tool_advantage="medium",
                risk_class="low",
            ),
        ),
        (
            "task_type=TRAINING",
            AllocationFactors(task_type="TRAINING", task_summary="每日算法训练", tool_advantage="high"),
        ),
        (
            "task_type=REFLECTION",
            AllocationFactors(task_type="REFLECTION", task_summary="本周学习复盘", tool_advantage="medium"),
        ),
    ],
    ids=["learning-type", "user-core", "learning-goal", "training-type", "reflection-type"],
)
def test_learning_task_never_gets_agent_mode(label, factors):
    """守卫①：学习型任务（各触发形态）feasible set 永不含 agent。"""
    decision = decide_allocation(factors)
    assert (
        "agent" not in decision.feasible_modes
    ), f"{label}: agent must be infeasible for learning tasks, got feasible={decision.feasible_modes}"
    assert decision.mode != "agent"
    assert "G1.learning_guard_no_agent" in decision.why


@pytest.mark.parametrize(
    "explicit_intent,user_preference,time_pressure",
    [
        (None, None, "relaxed"),
        ("delegate", None, "relaxed"),  # 用户说「帮我写」也要降级
        (None, "prefer_agent", "relaxed"),  # 持久偏好 agent 也不行
        (None, None, "urgent"),  # 时间紧也不行
    ],
    ids=["default", "explicit-delegate", "prefer-agent", "urgent"],
)
def test_learning_guard_survives_all_pressure_combos(explicit_intent, user_preference, time_pressure):
    """守卫①加强：显式委托/偏好 agent/时间紧都不能给学习型任务翻出 agent。"""
    factors = AllocationFactors(
        task_type="LEARNING",
        task_summary="自己动手实现一个红黑树",
        cognitive_ownership="user_core",
        tool_advantage="high",
        risk_class="low",
        explicit_intent=explicit_intent,
        user_preference=user_preference,
        time_pressure=time_pressure,
    )
    decision = decide_allocation(factors)
    assert decision.mode != "agent"
    assert "G1.learning_guard_no_agent" in decision.why


def test_learning_hybrid_requires_user_authored_evidence():
    """守卫②：学习 × hybrid → 必须要求 user-authored 完成证据。"""
    decision = decide_allocation(LEARNING_FACTORS)
    assert decision.mode == "hybrid"
    assert decision.requires_user_authored_evidence is True
    assert "G2.learning_evidence_user_authored" in decision.why
    assert decision.recommended_evidence_kinds  # 非空：artifact/code/quiz_result/file


def test_agent_complete_answer_path_is_rejected_for_learning():
    """守卫③（acceptance ②核心断言）：学习型任务下 Agent 完整答案路径被拒。"""
    verdict = vet_agent_offer("complete_answer", LEARNING_FACTORS)
    assert verdict.allowed is False
    assert verdict.reason == "G3.complete_answer_rejected_for_learning"
    assert verdict.suggested_downgrade in {"outline", "materials", "hint"}  # 给出合法降级路径


def test_agent_draft_rejected_for_user_core_creation():
    """守卫③延伸：user_core 创作类下 draft（半成品代写）同样被拒。"""
    verdict = vet_agent_offer("draft", LEARNING_FACTORS)
    assert verdict.allowed is False
    assert verdict.reason == "G4.draft_rejected_user_core"


@pytest.mark.parametrize(
    "kind",
    ["outline", "materials", "hint", "review"],
)
def test_hybrid_preparation_offers_still_allowed_for_learning(kind):
    """守卫不误伤：HYBRID handoff 的准备面（提纲/素材/提示/批改）合法。"""
    verdict = vet_agent_offer(kind, LEARNING_FACTORS)
    assert verdict.allowed is True
    assert verdict.reason == "OK.hybrid_preparation_allowed"


def test_shared_ownership_allows_agent_draft_for_learning():
    """shared 认知（agent 起草、人做核心决定）下 draft 合法——守卫精确打击。"""
    factors = AllocationFactors(
        task_summary="组会汇报 slides：AI 起草初版，我定结构与结论",
        cognitive_ownership="shared",
        task_type="LEARNING",
        tool_advantage="high",
        risk_class="low",
    )
    verdict = vet_agent_offer("draft", factors)
    assert verdict.allowed is True


def test_non_learning_execution_task_complete_answer_allowed():
    """非学习执行型任务（无学习守卫）成品供给合法——守卫不过度。"""
    factors = AllocationFactors(
        task_summary="把这 30 条参考文献整理成 BibTeX",
        cognitive_ownership="delegated",
        tool_advantage="high",
        risk_class="low",
    )
    verdict = vet_agent_offer("complete_answer", factors)
    assert verdict.allowed is True
    assert verdict.reason == "OK.content_generation_allowed"


# ---------------------------------------------------------------------------
# R2 返修（REVIEW_RECEIPT_2 §8 F1）：vet_agent_offer 错配对抗 + R5 权限检查
# ---------------------------------------------------------------------------


def test_vet_mechanical_high_risk_with_stale_low_risk_decision_still_needs_approval():
    """错配防御（R2 探针 P1 场景翻转）：陈旧/异因子的低风险决策（审批旗标
    False）不得替当前高风险因子免检——R1 按当下因子判定，旗标只作或运算一侧。"""
    stale = decide_allocation(
        AllocationFactors(cognitive_ownership="delegated", tool_advantage="high", risk_class="low", reversible=True)
    )
    assert stale.requires_human_approval is False
    verdict = vet_agent_offer(
        "mechanical",
        AllocationFactors(
            task_summary="批量删除共享盘上的旧文件",
            cognitive_ownership="delegated",
            tool_advantage="high",
            risk_class="high",
            reversible=False,
        ),
        decision=stale,
    )
    assert verdict.allowed is True
    assert verdict.requires_human_approval is True
    assert verdict.reason == "R1.autonomous_execution_needs_approval"


def test_vet_mechanical_medium_irreversible_without_decision_needs_approval():
    """无 decision 时 medium+不可逆同样挂审批（R1 因子路径保持不变）。"""
    verdict = vet_agent_offer(
        "mechanical",
        AllocationFactors(
            cognitive_ownership="delegated", tool_advantage="high", risk_class="medium", reversible=False
        ),
    )
    assert verdict.allowed is True
    assert verdict.requires_human_approval is True
    assert verdict.reason == "R1.autonomous_execution_needs_approval"


def test_vet_approval_flag_from_decision_alone_honored():
    """反向错配也安全：因子低风险但决策带审批旗标 → 仍挂审批（宁紧勿松）。"""
    approved = decide_allocation(AllocationFactors(tool_advantage="high", risk_class="critical", reversible=False))
    assert approved.requires_human_approval is True
    verdict = vet_agent_offer(
        "mechanical",
        AllocationFactors(cognitive_ownership="delegated", tool_advantage="high", risk_class="low", reversible=True),
        decision=approved,
    )
    assert verdict.allowed is True
    assert verdict.requires_human_approval is True


@pytest.mark.parametrize(
    "kind",
    ["complete_answer", "draft", "outline", "materials", "hint", "review", "mechanical"],
)
def test_vet_restricted_privacy_rejects_all_agent_supply(kind):
    """R2 探针 P2 场景翻转：restricted = agent 零接触——**一切**供给形态拒收
    （含准备面；与 decide_allocation 的 feasible={human} 同语义）。"""
    verdict = vet_agent_offer(
        kind,
        AllocationFactors(
            task_summary="处理我的私人健康档案并生成摘要",
            privacy="restricted",
            tool_advantage="high",
            risk_class="low",
        ),
    )
    assert verdict.allowed is False
    assert verdict.reason == "R5.restricted_agent_supply_forbidden"


@pytest.mark.parametrize(
    "kind,allowed",
    [
        ("complete_answer", False),
        ("mechanical", False),
        ("draft", True),
        ("outline", True),
        ("materials", True),
        ("hint", True),
        ("review", True),
    ],
    ids=["complete", "mechanical", "draft", "outline", "materials", "hint", "review"],
)
def test_vet_sensitive_privacy_blocks_autonomous_kinds_only(kind, allowed):
    """sensitive = 禁全自动 agent：拒「agent 独立交付/独立执行」形态，
    保留 hybrid 准备面（人在环）——精确打击，不误伤。"""
    verdict = vet_agent_offer(
        kind,
        AllocationFactors(
            task_summary="整理我的私密课程笔记", privacy="sensitive", tool_advantage="high", risk_class="low"
        ),
    )
    assert verdict.allowed is allowed
    if not allowed:
        assert verdict.reason == "R5.sensitive_autonomous_supply_forbidden"


def test_vet_sensitive_complete_answer_suggests_draft_downgrade():
    """sensitive 下 complete_answer 的合法降级路径：draft（人修改后交付）。"""
    verdict = vet_agent_offer(
        "complete_answer",
        AllocationFactors(task_summary="生成一份涉密报表", privacy="sensitive", tool_advantage="high"),
    )
    assert verdict.allowed is False
    assert verdict.suggested_downgrade == "draft"


def test_vet_sensitive_mechanical_has_no_downgrade():
    """sensitive 下 mechanical 无 agent 侧降级——该内容只能人执行或先解除密级。"""
    verdict = vet_agent_offer(
        "mechanical",
        AllocationFactors(task_summary="打包发送涉密附件", privacy="sensitive", tool_advantage="high"),
    )
    assert verdict.allowed is False
    assert verdict.suggested_downgrade is None
