"""A-02 · Intervention Catalog —— 17 项干预的声明式策略元数据（aurora_intervention_catalog.v1）。

冻结声明（v3/07_tasks/cards/A-02.md，Stream AURORA，Gate V3-2，locks aurora-policy）：
- **词表真源是 A-01 契约**：目录 key 集结构派生自
  ``app.core.aurora_decision.AURORA_INTERVENTION_TYPES``（本模块零干预名抄写——
  元数据表按名给属性，但 key 集合本身 = 契约词表；缺项/多项在 import 时 fail-fast，
  卡面 ``coexecute``/``connect`` 拼写漂移由此不可能进入运行时）。A-01 已把
  ``co_execute``/``connect_peer`` 冻结为契约拼写（AURORA_V3 §2 真源）。
- **每个 catalog item 有 capability / permission / expected outcome**（卡面
  acceptance ①）：干预不是「字符串自由动作」——它是带结构前提（能力/权限/上下文/
  分配事实）的封闭目录成员，policy engine（``app.aurora.intervention_policy``）
  据此做规则先过滤。
- catalog 是**语义集合**（AURORA_V3 §2：「不要求一类一个 Agent」）：expected_outcome
  描述用户侧行为结果，execution 的「谁来做」归 X-02（``decide_allocation``），
  ``nominal_execution_mode`` 只是契约镜像标称值（无 allocation 事实时的缺省，
  见模块尾部说明），不是第二套分配 rubric。

边界（与 A-01 四边界一致，不重建真源）：
- 任务结构归 X-01；执行分配归 X-02；证据装配归 C-01；A-02 拥有「干预目录 +
  选择可行性判定」（A-02 管「选哪个干预」，X-02 管「谁执行」）。
- spine ``_RULE_TABLE`` 的 primary_strategy（自由串）仍是 spine 行为真源；
  ``SPINE_STRATEGY_TO_INTERVENTION`` 是**投影映射**（供决策面把既有策略族
  翻译进封闭目录），覆盖率由测试对 ``_RULE_TABLE`` 全量强制（tests/contract）。

冻结纪律：字段集、封闭词表（INTERVENTION_CAPABILITIES / INTERVENTION_PERMISSIONS）、
逐 item 元数据、指纹 sha256 被 backend/tests/contract/test_intervention_catalog_contract.py
双钉（精确内容 + sha256）；任何变更需 bump ``INTERVENTION_CATALOG_VERSION``
并过 reviewer。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from app.core.aurora_decision import AURORA_INTERVENTION_TYPES

INTERVENTION_CATALOG_VERSION = "aurora_intervention_catalog.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump catalog 版本 + reviewer）
# ---------------------------------------------------------------------------

#: 干预的运行时能力需求维度（capability = 系统此刻有没有这个执行面）。
INTERVENTION_CAPABILITIES: frozenset[str] = frozenset(
    {
        "chat",  # 对话面（消息收发）
        "llm_generate",  # 生成面（解释/练习/批改的模型生成）
        "memory_read",  # 记忆/知识检索面
        "task_write",  # 任务/计划结构写面
        "scheduler",  # 定时/唤醒面
        "peer_network",  # 同侪/社群面
        "tool_execution",  # 外部工具执行面（agent 代办）
    }
)

#: 干预的用户/系统授权需求维度（permission = 有没有获准用这个面）。
#: capability 与 permission 分离是 X-02「工具优势 × 隐私权限」同款纪律：
#: 能做 ≠ 被准做。
INTERVENTION_PERMISSIONS: frozenset[str] = frozenset(
    {
        "memory_read",  # 读用户记忆/材料
        "plan_adjust",  # 调整用户计划/任务结构
        "task_execute",  # 代执行用户任务（X-02 分配允许的镜像）
        "model_write",  # 写用户/情境模型（建模会话产出）
        "peer_contact",  # 触达同侪网络
        "proactive_contact",  # 主动触达（推送/提醒，proactive_policy 预算面）
    }
)

#: 契约 execution_mode 标称镜像的合法值（词表真源 ExecutionMode，此处只断言子集）。
_NOMINAL_MODES: frozenset[str] = frozenset({"human", "agent", "hybrid"})

_INERT_NAMES: frozenset[str] = frozenset({"no_action", "abstain"})


@dataclass(frozen=True)
class InterventionCatalogItem:
    """单个干预的声明式元数据（policy engine 的判定输入，纯数据无行为）。

    - ``capability_requirements`` / ``permission_requirements``：封闭词表子集，
      缺任一即被规则层剔除（R1/R2）；
    - ``expected_outcome``：非空声明式结果描述（卡面 acceptance ①）；
    - ``requires_task_context``：干预需要一个活动任务/目标锚点（如 practice
      练的是「什么的」练习）——缺锚点 = R3 确定性拒绝；
    - ``requires_allocation`` + ``allocation_modes``：干预需要 X-02 分配事实
      支撑（delegate/execute/co_execute），且分配 mode 必须落在允许集内——
      缺 mode = R4（P3-8：不得静默放行），mode 冲突 = R5；
    - ``is_proactive``：主动触达型（受 quiet hours / proactive 预算门）；
    - ``is_inert``：无执行方（契约面 execution_mode 必须为 None 的唯一域，
      与 A-01 ``_INERT_INTERVENTIONS`` 同集）；
    - ``nominal_execution_mode``：契约标称镜像（见模块 docstring；X-02 分配
      事实存在时以分配 mode 为准，``consistent_with_allocation`` 校验）。
    """

    name: str
    capability_requirements: frozenset[str]
    permission_requirements: frozenset[str]
    expected_outcome: str
    requires_task_context: bool
    requires_allocation: bool
    allocation_modes: frozenset[str]
    is_proactive: bool
    is_inert: bool = False  # 仅 no_action/abstain 为 True（构造校验强制）
    nominal_execution_mode: str | None = None  # inert 恒 None（构造校验强制）

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "capability_requirements": sorted(self.capability_requirements),
            "permission_requirements": sorted(self.permission_requirements),
            "expected_outcome": self.expected_outcome,
            "requires_task_context": self.requires_task_context,
            "requires_allocation": self.requires_allocation,
            "allocation_modes": sorted(self.allocation_modes),
            "is_proactive": self.is_proactive,
            "is_inert": self.is_inert,
            "nominal_execution_mode": self.nominal_execution_mode,
        }


class InterventionCatalogError(RuntimeError):
    """目录构造失败（契约词表与元数据表失配）——import 时 fail-fast。"""


# ---------------------------------------------------------------------------
# 逐 item 元数据（声明式；key 集必须精确等于 AURORA_INTERVENTION_TYPES）
# ---------------------------------------------------------------------------
# 语义判据（可评审的依据，逐字段）：
# - clarify/explain/retrieve/reflect：对话域，不需要任务锚点（A-01：无
#   allocation_ref 的纯对话域控制决策可独占携带 mode）；
# - rescope/split/schedule/practice/review/remind：作用于任务/计划结构或
#   需要提醒对象 → requires_task_context（卡面点名 practice）；
# - delegate/execute/co_execute：执行面干预，「谁执行」是决策本体 → 必须
#   携带 X-02 分配事实（卡面点名 delegate；P3-8 缺 mode 确定性拒绝）；
# - remind/connect_peer：主动触达面（proactive_policy 预算 + quiet hours 门）；
# - pause：负荷下调（L2 burnout 族），有信号锚即可，不强制任务锚点；
# - abstain/no_action：确定性出口，无能力/权限前提（inert，无执行方）。
_ITEM_METADATA: dict[str, dict[str, Any]] = {
    "clarify": {
        "capability_requirements": frozenset({"chat"}),
        "permission_requirements": frozenset(),
        "expected_outcome": "歧义/上下文缺口被一个可回答的问题消解，后续决策获得判别信息",
        "requires_task_context": False,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "hybrid",
    },
    "explain": {
        "capability_requirements": frozenset({"chat", "llm_generate"}),
        "permission_requirements": frozenset(),
        "expected_outcome": "用户对当前概念/步骤的理解提升（解释可被指认来源）",
        "requires_task_context": False,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "agent",
    },
    "retrieve": {
        "capability_requirements": frozenset({"memory_read"}),
        "permission_requirements": frozenset({"memory_read"}),
        "expected_outcome": "相关材料/记忆被召回并作为证据进入决策上下文",
        "requires_task_context": False,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "agent",
    },
    "rescope": {
        "capability_requirements": frozenset({"task_write"}),
        "permission_requirements": frozenset({"plan_adjust"}),
        "expected_outcome": "目标/计划范围对齐当前现实（含范围收缩与抢救路径）",
        "requires_task_context": True,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "hybrid",
    },
    "split": {
        "capability_requirements": frozenset({"task_write", "llm_generate"}),
        "permission_requirements": frozenset({"plan_adjust"}),
        "expected_outcome": "过大任务被分解为当下可完成的单元（easy-win 粒度）",
        "requires_task_context": True,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "hybrid",
    },
    "schedule": {
        "capability_requirements": frozenset({"task_write", "scheduler"}),
        "permission_requirements": frozenset({"plan_adjust"}),
        "expected_outcome": "任务获得与现实时间约束一致的安排（含 deadline 重排）",
        "requires_task_context": True,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "hybrid",
    },
    "practice": {
        "capability_requirements": frozenset({"llm_generate"}),
        "permission_requirements": frozenset(),
        "expected_outcome": "用户通过针对性练习（worked example / 难度适配）自己获得能力",
        "requires_task_context": True,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "hybrid",
    },
    "review": {
        "capability_requirements": frozenset({"llm_generate"}),
        "permission_requirements": frozenset(),
        "expected_outcome": "用户的产出获得批改反馈，错误与高收益复习点被识别",
        "requires_task_context": True,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "agent",
    },
    "delegate": {
        "capability_requirements": frozenset({"tool_execution"}),
        "permission_requirements": frozenset({"task_execute"}),
        "expected_outcome": "任务交由 agent 执行（非学习核心），且经 X-02 分配允许",
        "requires_task_context": True,
        "requires_allocation": True,
        "allocation_modes": frozenset({"agent"}),
        "is_proactive": False,
        "nominal_execution_mode": "agent",
    },
    "execute": {
        "capability_requirements": frozenset({"tool_execution", "llm_generate"}),
        "permission_requirements": frozenset({"task_execute"}),
        "expected_outcome": "agent 直接完成该步骤并交付（用户核心学习步骤被 X-02 学习守卫排除在外）",
        "requires_task_context": True,
        "requires_allocation": True,
        "allocation_modes": frozenset({"agent"}),
        "is_proactive": False,
        "nominal_execution_mode": "agent",
    },
    "co_execute": {
        "capability_requirements": frozenset({"tool_execution", "chat"}),
        "permission_requirements": frozenset({"task_execute"}),
        "expected_outcome": "人机协作完成：agent 准备，用户保核心决策/创作点，agent 校对",
        "requires_task_context": True,
        "requires_allocation": True,
        "allocation_modes": frozenset({"hybrid"}),
        "is_proactive": False,
        "nominal_execution_mode": "hybrid",
    },
    "reflect": {
        "capability_requirements": frozenset({"chat", "llm_generate"}),
        "permission_requirements": frozenset({"model_write"}),
        "expected_outcome": "建模会话产出经用户确认的模型更新（写路径走白名单 surface）",
        "requires_task_context": False,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "hybrid",
    },
    "connect_peer": {
        "capability_requirements": frozenset({"peer_network"}),
        "permission_requirements": frozenset({"peer_contact", "proactive_contact"}),
        "expected_outcome": "同侪经验/资源被接入当前学习情境（同伴观察可回流调整）",
        "requires_task_context": False,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": True,
        "nominal_execution_mode": "hybrid",
    },
    "pause": {
        "capability_requirements": frozenset({"chat", "task_write"}),
        "permission_requirements": frozenset({"plan_adjust"}),
        "expected_outcome": "负荷被下调（break/降载/最小过线），过载与倦怠风险被抑制",
        "requires_task_context": False,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "nominal_execution_mode": "hybrid",
    },
    "remind": {
        "capability_requirements": frozenset({"scheduler"}),
        "permission_requirements": frozenset({"proactive_contact"}),
        "expected_outcome": "用户在合适时机被提醒承诺/期限/未启动任务（受 proactive 预算约束）",
        "requires_task_context": True,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": True,
        "nominal_execution_mode": "agent",
    },
    "abstain": {
        "capability_requirements": frozenset(),
        "permission_requirements": frozenset(),
        "expected_outcome": "主动不介入：边界被尊重（隐私/克制），本轮不作用于用户",
        "requires_task_context": False,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "is_inert": True,
        "nominal_execution_mode": None,
    },
    "no_action": {
        "capability_requirements": frozenset(),
        "permission_requirements": frozenset(),
        "expected_outcome": "无干预：本轮不存在值得作用的合法动作（带封闭原因码）",
        "requires_task_context": False,
        "requires_allocation": False,
        "allocation_modes": frozenset(),
        "is_proactive": False,
        "is_inert": True,
        "nominal_execution_mode": None,
    },
}


def _build_catalog() -> Mapping[str, InterventionCatalogItem]:
    """结构派生构造：key 集 = AURORA_INTERVENTION_TYPES（import，非抄写）。

    缺元数据 / 多余元数据 / 词表外元数据值 → ``InterventionCatalogError``
    （import 时 fail-fast，拼写漂移不可能存活）。
    """
    unknown = set(_ITEM_METADATA) - set(AURORA_INTERVENTION_TYPES)
    if unknown:
        raise InterventionCatalogError(
            f"catalog metadata has entries outside the frozen contract vocabulary: {sorted(unknown)}"
        )
    items: dict[str, InterventionCatalogItem] = {}
    for name in sorted(AURORA_INTERVENTION_TYPES):
        meta = _ITEM_METADATA.get(name)
        if meta is None:
            raise InterventionCatalogError(
                f"catalog metadata missing for frozen intervention {name!r} "
                f"(contract vocabulary has {len(AURORA_INTERVENTION_TYPES)} members)"
            )
        item = InterventionCatalogItem(name=name, **meta)
        _validate_item(item)
        items[name] = item
    return MappingProxyType(items)


def _validate_item(item: InterventionCatalogItem) -> None:
    if not item.capability_requirements <= INTERVENTION_CAPABILITIES:
        raise InterventionCatalogError(
            f"{item.name}: unknown capabilities {sorted(item.capability_requirements - INTERVENTION_CAPABILITIES)}"
        )
    if not item.permission_requirements <= INTERVENTION_PERMISSIONS:
        raise InterventionCatalogError(
            f"{item.name}: unknown permissions {sorted(item.permission_requirements - INTERVENTION_PERMISSIONS)}"
        )
    if not (item.expected_outcome or "").strip():
        raise InterventionCatalogError(f"{item.name}: expected_outcome must be non-empty")
    if not item.allocation_modes <= _NOMINAL_MODES:
        raise InterventionCatalogError(
            f"{item.name}: unknown allocation modes {sorted(item.allocation_modes - _NOMINAL_MODES)}"
        )
    if item.requires_allocation and not item.allocation_modes:
        raise InterventionCatalogError(f"{item.name}: requires_allocation without allowed allocation_modes")
    if item.is_inert != (item.name in _INERT_NAMES):
        raise InterventionCatalogError(
            f"{item.name}: is_inert={item.is_inert} inconsistent with A-01 inert set {sorted(_INERT_NAMES)}"
        )
    if item.is_inert and item.nominal_execution_mode is not None:
        raise InterventionCatalogError(f"{item.name}: inert intervention must not carry nominal_execution_mode")
    if not item.is_inert and (
        item.nominal_execution_mode is None or item.nominal_execution_mode not in _NOMINAL_MODES
    ):
        raise InterventionCatalogError(f"{item.name}: actionable intervention needs a nominal execution mode")


#: 冻结目录（只读视图；构造失败 = import 失败 = 测试红）。
INTERVENTION_CATALOG: Mapping[str, InterventionCatalogItem] = _build_catalog()


def catalog_fingerprint() -> str:
    """目录规范形（版本 + 逐 item 排序 dump）的 sha256[:16]。

    供 policy evaluation 与契约 annotations 携带——「这次决策用的是哪版目录」
    可审计（A-01 决策 id 同款的可追溯纪律）。
    """
    canonical = json.dumps(
        {
            "version": INTERVENTION_CATALOG_VERSION,
            "items": [INTERVENTION_CATALOG[name].to_dict() for name in sorted(INTERVENTION_CATALOG)],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 既有策略面 → 目录投影（映射现有 policies，卡面 Work 1 的机制化面）
# ---------------------------------------------------------------------------

#: spine ``_RULE_TABLE``（app/signals/policy_engine.py）的 primary/secondary
#: strategy 自由串 → 封闭目录成员的投影映射。**全量覆盖**由契约测试强制
#: （枚举 _RULE_TABLE 全部 strategy 值逐一断言有映射）——不存在的策略串
#: 不允许（否则又回到「字符串自由动作」）。语义判据：
#: - 结构性（计划/范围/粒度/节奏调整）→ rescope/split/schedule；
#: - 知识/能力修复与适配 → practice；批改/复习 → review；
#: - 材料召回 → retrieve；诊断提问 → clarify；任务启动提醒 → remind；
#: - 降载/休息/危机最小化 → pause；简化/安抚性解释 → explain；
#: - 同侪接入 → connect_peer；纯语气/关系面（无结构动作）→ no_action
#:   （语气是 response directive 的参数，不是控制干预）。
SPINE_STRATEGY_TO_INTERVENTION: dict[str, str] = {
    "recover_execution_rhythm": "rescope",
    "repair_current_bottleneck": "practice",
    "activate_material_retrieval": "retrieve",
    "exam_rescue_sprint": "rescope",
    "minimum_pass_path": "rescope",
    "enforce_crisis_mode": "pause",
    "minimum_pass_only": "rescope",
    "repair_knowledge_bottleneck": "practice",
    "prevent_new_chapter": "rescope",
    "sustain_momentum": "no_action",
    "gradual_challenge_increase": "practice",
    "rekindle_engagement": "rescope",
    "insert_easy_win": "split",
    "prompt_diagnostic": "clarify",
    "nudge_task_start": "remind",
    "recover_from_missed_task": "rescope",
    "adjust_plan": "rescope",
    "urgent_exam_prep": "review",
    "high_yield_review": "review",
    "show_cohort_hint": "connect_peer",
    "show_peer_resource": "connect_peer",
    "adjust_partner_reported_pacing": "rescope",
    "reduce_next_48h_load": "pause",
    "increase_next_48h_activation": "rescope",
    "apply_partner_focus_patch": "rescope",
    "apply_partner_difficulty_patch": "practice",
    "encourage_partner_observed_morale": "no_action",
    "reduce_cognitive_pressure": "pause",
    "simplify_context": "explain",
    "reduce_affective_pressure": "pause",
    "insert_reassurance": "explain",
    "prevent_burnout": "pause",
    "suggest_break": "pause",
    "switch_to_worked_example": "practice",  # shadow learning 动态切换值（_apply_shadow_learning）
}
