"""V4-I07 · 学习/交付目标的人机权限与脚手架（hybrid-policy 增量策略层）。

定位（v4/04_tasks/cards/V4-I07.md，locks: hybrid-policy；规格：
``v4/03_intelligence/EXPERIENCE_AND_LEARNING.md`` §Human/Hybrid/Agent 的学习目标、
MASTER_DESIGN §5「人机合作不偷走学习」/§6「示例→自己做→检查」）：

在**现有** Human/Agent/Hybrid 步骤语义（X-01 ``ExecutionMode`` /
``CognitiveOwnership``，X-02 allocation policy）之上加两个维度，不另起第二权限真源：

1. **目的维度**（goal_purpose）：``mastery``（学会）/ ``deliverable``（交付）/
   ``mixed``（拆清准备/决策/执行/检验）。界面三种可读选择（我来做/带我做/交给
   Sparkle）的底层仍是既有 execution_mode——本模块只提供目的的封闭词表、解析与
   逐步骤消解，不改变 execution_mode 协议。
2. **human_required 约束**：mastery 目标中用户必须亲自完成的步骤标记。Agent
   完成 human_required 步骤时，**不得结算人类掌握**（本卡验收第 1 条——
   「接受建议≠任务推进，完成任务≠能力掌握」的结算面机制化）。

四个可失败面（对应卡验收三条）：

- :func:`human_mastery_settlement` / :func:`settlement_for_task_row` —— 结算门：
  mastery 目标（含 legacy 行按 X-02 ``LEARNING_TASK_TYPES`` 同集推导）中非用户
  完成的步骤不记人类掌握；deliverable 目标合法代办照常结算，不强迫用户手工
  重复（验收第 2 条）。消费方：``TaskService.complete``（sprint 掌握结算面前）。
- :func:`redact_independent_check` —— 独立检验（scaffold 第三段）的**答案**
  不进可见/可检索上下文：带 ``kind="independent_check"`` 标记的节点在投影进
  模型上下文前剥除封闭答案键集（验收第 3 条）。消费方：``api/v1/chat.py``
  task_context 注入面。答案本体允许服务端落 ``tasks.guide_json``（判分权威），
  但**任何**上下文投影必须过本门。
- :func:`next_scaffold_step` —— 脚手架链 ``example → attempt → independent_check``
  与提示渐隐（``full → reduced → none``）：只在**用户选择且证据支持**时推进；
  尝试失败 → 增加局部支持（提示档回升），**阶段永不回退**（不把用户降级）。
- :func:`resolve_step_purpose` —— 目的的逐步骤消解：human_required 步骤恒为
  mastery 语义；mastery 目标的 delegated 准备步（示例/提示/检查准备）消解为
  deliverable（Agent 准备合法，不泄露检验答案）。

词表纪律（不造第二权威）：
- ExecutionMode / CognitiveOwnership = X-01（``app.models.task`` /
  ``app.models.execution_intent``）原样复用，本模块不复制枚举；
- legacy 行目的推导与 X-02 ``LEARNING_TASK_TYPES`` 同集对齐——由
  ``tests/unit/test_hybrid_policy.py::test_derive_goal_purpose_matches_x02_learning_types``
  钉死防漂移（X-02 仍是分配权威，本模块只消费同集推导）；
- 策略块落 ``tasks.guide_json["v4_hybrid_policy"]``（既有 JSONB 列的版本化子键，
  零迁移、零新列；X-01 契约列不动——把 human_required 提升进 X-01 契约属
  contract-owner 的 ``action_plan.v1.x`` 变更，本卡不做）。

数据面 unknown 语义（B05 §2 同款纪律）：
- 块缺失 / 版本不符 / 字段脏值 → 解析降级 None + 原因，**不臆测回填**；
- legacy 行（无块）目的按 :func:`derive_goal_purpose` 确定性推导（与 X-02
  学习守卫同源），human_required 默认 False（legacy 行为不变）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.task import CognitiveOwnership, TaskType

HYBRID_POLICY_VERSION = "hybrid_policy.v1"

#: guide_json 内本卡策略块的保留键（版本化子键；零迁移）。
GOAL_PURPOSE_BLOCK_KEY = "v4_hybrid_policy"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展 = bump HYBRID_POLICY_VERSION 并过 reviewer）
# ---------------------------------------------------------------------------

#: 目的维度（EXPERIENCE_AND_LEARNING §Human/Hybrid/Agent 的学习目标：
#: mastery goal / deliverable goal / mixed goal）。
GOAL_PURPOSES: frozenset[str] = frozenset({"mastery", "deliverable", "mixed"})

GOAL_PURPOSE_MASTERY = "mastery"
GOAL_PURPOSE_DELIVERABLE = "deliverable"
GOAL_PURPOSE_MIXED = "mixed"

#: 脚手架链（MASTER_DESIGN §6「示例→自己做→检查」；只进不退）。
SCAFFOLD_STAGES: frozenset[str] = frozenset({"example", "attempt", "independent_check"})

SCAFFOLD_STAGE_EXAMPLE = "example"
SCAFFOLD_STAGE_ATTEMPT = "attempt"
SCAFFOLD_STAGE_INDEPENDENT_CHECK = "independent_check"

#: 提示档（提示渐隐：full → reduced → none；失败时局部回升）。
HINT_LEVELS: frozenset[str] = frozenset({"full", "reduced", "none"})

HINT_FULL = "full"
HINT_REDUCED = "reduced"
HINT_NONE = "none"

#: 谁完成了该步骤的归一词表。``agent`` 语义 = 「非用户产出」（agent 代执行 /
#: system 自动化一律归此，低信任面从严）。
COMPLETED_BYS: frozenset[str] = frozenset({"user", "agent"})

COMPLETED_BY_USER = "user"
COMPLETED_BY_AGENT = "agent"

#: 结算裁决 reason（封闭集；扩展 = bump）。
SETTLEMENT_REASONS: frozenset[str] = frozenset(
    {
        "OK.human_authored_settlement",  # 用户亲自完成 → 掌握结算合法
        "OK.deliverable_delegation_settlement",  # 交付目标合法代办 → 照常结算（不强迫手工重复）
        "BLOCK.agent_completed_human_required_mastery",  # 验收1：agent 代答 human_required 步骤
        "BLOCK.agent_completed_mastery_step",  # 验收1：mastery 目标中非用户完成一律不记人类掌握
    }
)

#: 脚手架转移 reason（封闭集；扩展 = bump）。
SCAFFOLD_TRANSITION_REASONS: frozenset[str] = frozenset(
    {
        "OK.advance_user_chose_with_evidence",  # 用户选择 + 证据支持 → 推进
        "OK.hint_fading_prior_example_sufficient",  # 前次示例充分 → 减少提示（渐隐）
        "HOLD.user_did_not_choose",  # 用户未选择推进 → 原地（只在用户选择时推进）
        "HOLD.evidence_not_supported",  # 证据不支持 → 原地（不硬推）
        "SUPPORT.failure_adds_local_hint",  # 尝试失败 → 提示档回升（局部支持），阶段不降
        "OK.independent_check_reached",  # 已到独立检验（链终点）
    }
)

#: 独立检验答案键（封闭集；出现在 independent_check 标记节点内即属答案面，
#: 上下文投影前必须剥除）。注意：``error_records.correct_answer`` 等用户自有
#: 材料不在此列——本键集只约束**系统生成的独立检验**节点。
#: ``solution_steps``（I07 一审 F4）：解题步骤即答案实质（工作解），与
#: ``solution`` 同面——判分权威（服务端 guide_json）原地保留，投影前剥除。
#: ``explanation``/``correct_option``/``grading.correct``（I07 二审 R2-1）：同一
#: 答案面同类键（解析文本/正确选项/判分结论），构造性泄漏与 solution 同型。
INDEPENDENT_CHECK_ANSWER_KEYS: frozenset[str] = frozenset(
    {
        "answer",
        "correct_answer",
        "expected_answer",
        "reference_answer",
        "model_answer",
        "solution",
        "solution_steps",
        "answer_key",
        "explanation",
        "correct_option",
        "correct",  # 叶子键匹配：grading.correct 的判分结论落在本键
    }
)

#: 独立检验节点的标记键/值（承载在 guide_json 策略块或任意投影载荷内）。
INDEPENDENT_CHECK_KIND = "independent_check"
INDEPENDENT_CHECK_FLAG_KEY = "independent_check"

_SCAFFOLD_ORDER = (SCAFFOLD_STAGE_EXAMPLE, SCAFFOLD_STAGE_ATTEMPT, SCAFFOLD_STAGE_INDEPENDENT_CHECK)
_HINT_ORDER = (HINT_FULL, HINT_REDUCED, HINT_NONE)


def _ref_or_none(value: Any, vocab: frozenset[str]) -> str | None:
    """脏值→None（fail-closed，不 raise；B05 unknown 语义同款）。"""
    if isinstance(value, str) and value in vocab:
        return value
    return None


# ---------------------------------------------------------------------------
# 策略块解析（guide_json["v4_hybrid_policy"]）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScaffoldState:
    """脚手架链当前态（stage / hint_level；持久化在策略块 ``scaffold`` 子键）。"""

    stage: str = SCAFFOLD_STAGE_EXAMPLE
    hint_level: str = HINT_FULL

    def to_dict(self) -> dict[str, str]:
        return {"stage": self.stage, "hint_level": self.hint_level}


@dataclass(frozen=True)
class HybridPolicyBlock:
    """解析后的策略块（脏块 → (None, 原因)，绝不半真解析）。"""

    goal_purpose: str
    human_required: bool
    scaffold: ScaffoldState
    #: independent_check 原始子结构（服务端判分权威；投影前必须过
    #: :func:`redact_independent_check`）。
    independent_check: dict[str, Any] | None = None


def parse_policy_block(guide_json: Any) -> tuple[HybridPolicyBlock | None, str | None]:
    """解析策略块；``(None, None)`` = 无块（legacy 行，正常态）；``(None, 原因)``
    = 有块但损坏/版本不符（fail-closed，调用方不得拿半真块做权限判定）。"""
    if not isinstance(guide_json, dict):
        return None, None
    raw = guide_json.get(GOAL_PURPOSE_BLOCK_KEY)
    if raw is None:
        return None, None
    if not isinstance(raw, dict):
        return None, "policy_block_not_a_dict"
    version = raw.get("schema_version")
    if version != HYBRID_POLICY_VERSION:
        return None, f"schema_version_mismatch: {version!r}"
    purpose = _ref_or_none(raw.get("goal_purpose"), GOAL_PURPOSES)
    if purpose is None:
        return None, f"goal_purpose out of vocabulary: {raw.get('goal_purpose')!r}"
    human_required = raw.get("human_required")
    if not isinstance(human_required, bool):
        return None, f"human_required not a bool: {human_required!r}"
    scaffold_raw = raw.get("scaffold")
    if scaffold_raw is None:
        scaffold = ScaffoldState()
    elif isinstance(scaffold_raw, dict):
        stage = _ref_or_none(scaffold_raw.get("stage"), SCAFFOLD_STAGES)
        hint = _ref_or_none(scaffold_raw.get("hint_level"), HINT_LEVELS)
        if scaffold_raw.get("stage") is not None and stage is None:
            return None, f"scaffold.stage out of vocabulary: {scaffold_raw.get('stage')!r}"
        if scaffold_raw.get("hint_level") is not None and hint is None:
            return None, f"scaffold.hint_level out of vocabulary: {scaffold_raw.get('hint_level')!r}"
        scaffold = ScaffoldState(stage=stage or SCAFFOLD_STAGE_EXAMPLE, hint_level=hint or HINT_FULL)
    else:
        return None, "scaffold_block_not_a_dict"
    check_raw = raw.get("independent_check")
    check = dict(check_raw) if isinstance(check_raw, dict) else None
    return (
        HybridPolicyBlock(
            goal_purpose=purpose,
            human_required=human_required,
            scaffold=scaffold,
            independent_check=check,
        ),
        None,
    )


def derive_goal_purpose(task_type: Any, cognitive_ownership: Any) -> str:
    """legacy 行（无策略块）的目的确定性推导——与 X-02 学习守卫同源同集。

    - task_type ∈ {LEARNING, TRAINING, REFLECTION}（= X-02 ``LEARNING_TASK_TYPES``，
      测试钉死防漂移）或 ownership=user_core → mastery；
    - ownership=delegated → deliverable；
    - 其余 → mixed（拆清，逐步骤再消解）。
    """
    type_value = getattr(task_type, "value", task_type)
    if isinstance(type_value, str) and type_value in _X02_ALIGNED_LEARNING_TASK_TYPES:
        return GOAL_PURPOSE_MASTERY
    ownership_value = getattr(cognitive_ownership, "value", cognitive_ownership)
    if ownership_value == CognitiveOwnership.USER_CORE.value:
        return GOAL_PURPOSE_MASTERY
    if ownership_value == CognitiveOwnership.DELEGATED.value:
        return GOAL_PURPOSE_DELIVERABLE
    return GOAL_PURPOSE_MIXED


#: 与 X-02 ``LEARNING_TASK_TYPES`` 同集（由 ``TaskType`` 成员构造，测试断言与
#: ``app.services.action_allocation_policy.LEARNING_TASK_TYPES`` 逐成员相等）。
_X02_ALIGNED_LEARNING_TASK_TYPES: frozenset[str] = frozenset(
    {TaskType.LEARNING.value, TaskType.TRAINING.value, TaskType.REFLECTION.value}
)


def resolve_step_purpose(
    goal_purpose: str | None,
    *,
    human_required: bool,
    cognitive_ownership: Any = None,
) -> str:
    """目的的逐步骤消解（mixed / legacy 行在此落地为步骤级语义）。

    - ``human_required=True`` 恒 mastery 语义（人必须亲自完成的门，任何目的下成立）；
    - mastery 目标：user_core/shared → mastery；delegated 准备步（示例/提示/
      检查准备——EXPERIENCE_AND_LEARNING「Agent准备相近示例/提示/检查」）→
      deliverable（Agent 准备合法）；未知 ownership → mastery（保守）；
    - deliverable 目标：user_core（该步本身即用户要获得的能力）→ mastery；
      其余 → deliverable（合法代办）；
    - mixed / None：user_core → mastery，其余 → mixed。
    """
    ownership_value = getattr(cognitive_ownership, "value", cognitive_ownership)
    if human_required:
        return GOAL_PURPOSE_MASTERY
    ownership_core = ownership_value == CognitiveOwnership.USER_CORE.value
    ownership_delegated = ownership_value == CognitiveOwnership.DELEGATED.value
    if goal_purpose == GOAL_PURPOSE_MASTERY:
        if ownership_delegated:
            return GOAL_PURPOSE_DELIVERABLE
        return GOAL_PURPOSE_MASTERY
    if goal_purpose == GOAL_PURPOSE_DELIVERABLE:
        return GOAL_PURPOSE_MASTERY if ownership_core else GOAL_PURPOSE_DELIVERABLE
    return GOAL_PURPOSE_MASTERY if ownership_core else GOAL_PURPOSE_MIXED


# ---------------------------------------------------------------------------
# 结算门（验收 1 / 验收 2）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SettlementVerdict:
    """一次人类掌握结算的裁决（allowed + 封闭 reason，可审计可观测）。"""

    allowed: bool
    reason: str
    goal_purpose: str
    human_required: bool
    completed_by: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "goal_purpose": self.goal_purpose,
            "human_required": self.human_required,
            "completed_by": self.completed_by,
        }


def human_mastery_settlement(
    *,
    goal_purpose: str,
    human_required: bool,
    completed_by: str,
) -> SettlementVerdict:
    """「完成任务」能否结算「人类掌握」。

    规则（验收 1/2 的精确面）：
    - 用户亲自完成 → 结算（OK.human_authored_settlement）；
    - agent（= 非用户产出）完成：
      - human_required 步骤 → **拒绝**（BLOCK.agent_completed_human_required_mastery）
        ——代答不能结算人类掌握，任何目的下成立；
      - mastery 目标步骤 → **拒绝**（BLOCK.agent_completed_mastery_step）
        ——mastery 目标里 Agent 只准备（示例/提示/检验），不产出人类掌握；
      - deliverable / mixed 的非 human_required 步骤 → 结算
        （OK.deliverable_delegation_settlement）——合法代办，不强迫用户手工重复。
    """
    purpose = _ref_or_none(goal_purpose, GOAL_PURPOSES)
    if purpose is None:
        raise ValueError(f"goal_purpose out of vocabulary: {goal_purpose!r}")
    by = _ref_or_none(completed_by, COMPLETED_BYS)
    if by is None:
        raise ValueError(f"completed_by out of vocabulary: {completed_by!r}")

    if by == COMPLETED_BY_USER:
        return SettlementVerdict(True, "OK.human_authored_settlement", purpose, human_required, by)
    if human_required:
        return SettlementVerdict(False, "BLOCK.agent_completed_human_required_mastery", purpose, human_required, by)
    if purpose == GOAL_PURPOSE_MASTERY:
        return SettlementVerdict(False, "BLOCK.agent_completed_mastery_step", purpose, human_required, by)
    return SettlementVerdict(True, "OK.deliverable_delegation_settlement", purpose, human_required, by)


#: 非用户产出的 evidence_source（task_completion_evidence.EVIDENCE_SOURCES 中
#: 非 user/focus_auto 的成员——focus 计时器是用户自己的投入，归 user）。
_NON_USER_EVIDENCE_SOURCES: frozenset[str] = frozenset({"agent", "system"})


def settlement_for_task_row(task: Any, *, evidence_source: str | None) -> SettlementVerdict:
    """从 Task 行解析策略块（legacy 行确定性推导）并给出结算裁决。

    TaskService.complete 的唯一入口（等价语义不在调用方复制）。``evidence_source``
    归一：``user``/``focus_auto`` → user；``agent``/``system``/未知 → agent
    （非用户产出从严）。
    """
    block, _degrade = parse_policy_block(getattr(task, "guide_json", None))
    if block is not None:
        purpose = block.goal_purpose
        human_required = block.human_required
    else:
        purpose = derive_goal_purpose(getattr(task, "type", None), getattr(task, "cognitive_ownership", None))
        human_required = False
    if evidence_source in ("user", "focus_auto"):
        by = COMPLETED_BY_USER
    else:
        by = COMPLETED_BY_AGENT
    return human_mastery_settlement(goal_purpose=purpose, human_required=human_required, completed_by=by)


# ---------------------------------------------------------------------------
# 脚手架链与提示渐隐（示例 → 尝试 → 独立检验）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScaffoldDecision:
    """一次脚手架推进判定（新 stage/hint_level + 封闭 reason）。"""

    stage: str
    hint_level: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"stage": self.stage, "hint_level": self.hint_level, "reason": self.reason}


def next_scaffold_step(
    *,
    stage: str,
    hint_level: str,
    user_chose: bool,
    evidence_supported: bool,
    attempt_failed: bool = False,
) -> ScaffoldDecision:
    """脚手架链转移（纯函数；冻结转移表）。

    纪律（EXPERIENCE_AND_LEARNING §脚手架渐隐原文的机制化）：
    - 只在**用户选择且证据支持**时推进（user_chose AND evidence_supported）；
    - 前次示例充分（证据支持但用户未选推进）→ 减少提示（渐隐），stage 不动；
    - 尝试失败 → 提示档回升一档（none→reduced→full 封顶），stage 不回退
      （增加局部支持，不把用户降级）；
    - independent_check 是链终点（检验本身的通过/失败归既有判分与 SM-2 面）。
    """
    current_stage = _ref_or_none(stage, SCAFFOLD_STAGES)
    current_hint = _ref_or_none(hint_level, HINT_LEVELS)
    if current_stage is None:
        raise ValueError(f"stage out of vocabulary: {stage!r}")
    if current_hint is None:
        raise ValueError(f"hint_level out of vocabulary: {hint_level!r}")

    if current_stage == SCAFFOLD_STAGE_INDEPENDENT_CHECK:
        return ScaffoldDecision(current_stage, current_hint, "OK.independent_check_reached")

    if attempt_failed and current_stage == SCAFFOLD_STAGE_ATTEMPT:
        # 失败 → 局部支持：提示档回升一档；阶段不回退（不把用户降级）。
        idx = _HINT_ORDER.index(current_hint)
        raised = _HINT_ORDER[max(0, idx - 1)]
        return ScaffoldDecision(current_stage, raised, "SUPPORT.failure_adds_local_hint")

    if user_chose and evidence_supported:
        next_idx = _SCAFFOLD_ORDER.index(current_stage) + 1
        next_stage = _SCAFFOLD_ORDER[next_idx]
        # 推进即渐隐：进入尝试/检验段提示降一档（示例段的完整提示不再跟随）。
        hint_idx = _HINT_ORDER.index(current_hint)
        return ScaffoldDecision(
            next_stage, _HINT_ORDER[min(hint_idx + 1, len(_HINT_ORDER) - 1)], "OK.advance_user_chose_with_evidence"
        )

    if evidence_supported and not user_chose and current_stage == SCAFFOLD_STAGE_EXAMPLE:
        # 前次示例充分、用户未选择推进 → 渐隐：提示降一档，stage 不动。
        idx = _HINT_ORDER.index(current_hint)
        faded = _HINT_ORDER[min(idx + 1, len(_HINT_ORDER) - 1)]
        return ScaffoldDecision(current_stage, faded, "OK.hint_fading_prior_example_sufficient")

    if not user_chose:
        return ScaffoldDecision(current_stage, current_hint, "HOLD.user_did_not_choose")
    return ScaffoldDecision(current_stage, current_hint, "HOLD.evidence_not_supported")


# ---------------------------------------------------------------------------
# 独立检验答案隔离（验收 3）
# ---------------------------------------------------------------------------


def _is_independent_check_node(node: dict[str, Any]) -> bool:
    if node.get("kind") == INDEPENDENT_CHECK_KIND:
        return True
    return node.get(INDEPENDENT_CHECK_FLAG_KEY) is True


def _strip_answers(node: Any, prefix: str, removed: list[str]) -> Any:
    """深拷贝并剥除 independent_check 子树内的答案键（返回干净副本）。"""
    if isinstance(node, dict):
        clean: dict[str, Any] = {}
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in INDEPENDENT_CHECK_ANSWER_KEYS:
                removed.append(path)
                continue
            clean[key] = _strip_answers(value, path, removed)
        return clean
    if isinstance(node, list):
        return [_strip_answers(item, f"{prefix}[{i}]", removed) for i, item in enumerate(node)]
    return node


def redact_independent_check(payload: Any) -> tuple[Any, tuple[str, ...]]:
    """剥除载荷中 independent_check 节点内的答案键，返回 ``(干净载荷, 移除路径)``。

    - 触发面：``kind == "independent_check"`` 的 dict 节点，或
      ``independent_check: true`` 旗标节点（含其整棵子树）；
    - 非标记节点内的同名字段**不**动（用户自有材料如 error_records 的
      correct_answer 不在本门语义内）；
    - 纯函数：不改输入，返回深拷贝（上下文投影侧零副作用）。
    """

    def _walk(node: Any, prefix: str, in_check: bool, removed: list[str]) -> Any:
        if isinstance(node, dict):
            active = in_check or _is_independent_check_node(node)
            clean: dict[str, Any] = {}
            for key, value in node.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                if active and key in INDEPENDENT_CHECK_ANSWER_KEYS:
                    removed.append(path)
                    continue
                clean[key] = _walk(value, path, active, removed)
            return clean
        if isinstance(node, list):
            return [_walk(item, f"{prefix}[{i}]", in_check, removed) for i, item in enumerate(node)]
        return node

    removed: list[str] = []
    clean = _walk(payload, "", False, removed)
    return clean, tuple(removed)


def contains_independent_check_answer(payload: Any) -> bool:
    """泄漏探针：载荷中 independent_check 节点内是否残留答案键（测试/守卫用）。"""
    _, removed = redact_independent_check(payload)
    return len(removed) > 0


def task_guide_context_projection(guide_json: Any) -> tuple[Any, dict[str, str] | None, tuple[str, ...]]:
    """guide_json → 聊天/模型上下文投影三元组 ``(干净 guide_json, 脚手架面, 剥除路径)``。

    api/v1/chat.py task_context 注入面的唯一入口（验收③的接线点）：
    - 独立检验答案先剥除（答案本体留在服务端 guide_json 判分权威）；
    - 脚手架链当前态（stage / hint_level / goal_purpose）单独特出——答案面之外，
      供「示例→尝试→独立检验」建议面消费；无块/脏块 → None；
    - 剥除路径供观测日志。
    """
    clean, removed = redact_independent_check(guide_json)
    try:
        block, _degrade = parse_policy_block(guide_json)
    except Exception:  # noqa: BLE001 — 投影永不抛
        block = None
    scaffold: dict[str, str] | None = None
    if block is not None:
        scaffold = {
            "stage": block.scaffold.stage,
            "hint_level": block.scaffold.hint_level,
            "goal_purpose": block.goal_purpose,
        }
    return clean, scaffold, removed


def apply_scaffold_decision(block_raw: dict[str, Any], decision: ScaffoldDecision) -> dict[str, Any]:
    """把脚手架决策写回策略块 raw dict（返回新 dict；持久化辅助，不改输入）。"""
    raw = dict(block_raw or {})
    inner = dict(raw.get(GOAL_PURPOSE_BLOCK_KEY) or {})
    inner["schema_version"] = HYBRID_POLICY_VERSION
    inner["scaffold"] = {"stage": decision.stage, "hint_level": decision.hint_level, "last_reason": decision.reason}
    raw[GOAL_PURPOSE_BLOCK_KEY] = inner
    return raw
