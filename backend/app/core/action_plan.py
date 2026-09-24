"""X-01 · ActionPlan V3 契约 —— tasks 域的 Outcome / Execution / Cognitive Ownership 语义。

冻结声明（v3/07_tasks/cards/X-01.md，locks: action-contract）：
- **不重建 task system**：V3 语义以最小加法落在今日真值 ``tasks`` 表（B-06 D-TASK），
  新列全部 nullable，``action_schema_version IS NULL`` 即 legacy 行（V2.x 完全兼容）。
- **execution_mode 唯一协议 = ExecutionIntent**（B-06 §1.5）：HUMAN/AGENT/HYBRID 词表
  直接复用 ``app.models.execution_intent.ExecutionMode``（human/agent/hybrid，小写），
  本契约**不新造第二套执行模式枚举**；``tasks.execution_mode`` 复用既有 String(20)
  镜像列（dev DB 1231 行全 NULL，2026-09-19 复核），只新增应用层封闭校验。
- **cognitive_ownership 首版定义（D13，全仓 0 实现的盲点补充）**：
    - ``user_core``  —— 该步骤本身即用户想获得的能力/判断/创作（学习、反思、
      关系沟通）：不可委托给 agent 完成后只交结果（HUMAN_AGENT_HYBRID §2 维度 1）。
    - ``shared``     —— 混合认知：agent 准备素材/校对，人做核心决定或创作
      （对应 HYBRID 模式 ``Agent prepares → Human decides → Agent checks``）。
    - ``delegated``  —— 机械性/低认知价值步骤（检索、整理、格式转换），用户无需
      认知参与，可整体委托 agent。
  cognitive_ownership 与 execution_mode 是两个正交轴：例如 execution_mode=hybrid +
  cognitive_ownership=user_core（agent 查文献、用户写论文）是合法且常见的组合。
- **source_refs ref 语义对齐 C-01 decision_context.v1（封闭 scheme）**：
  C-01 的 {memory, user_state, plan, document, profile} 原样包含；action 域扩展
  {goal, task, subtask, chat, decision, run}（run → execution_intents）。scheme 封闭，
  扩展需 bump 契约版本。**待对齐点（D-01 并行中）**：D-01 Event/Evidence Lineage 的
  intervention/action/run/outcome ID 关联词表若引入新 ref 形态，需在此对齐扩展。
- **completion_evidence 类型化**（ACTION_AND_INTERVENTION_ENGINE §4）：plan 侧声明
  「什么算完成证据」——每条必须带 ``evidence_kind``（封闭枚举，覆盖 artifact/file/
  code/quiz_result/user_confirmation/self_report/system_event），可选 ``ref``（同封闭
  scheme）；禁止自由文本一列了事。outcome 侧的 actual/self-reported/estimated/unknown
  验证分级属 D-01 事件域，本契约不重复定义。
- 契约快照 parity guard：backend/tests/unit/test_action_plan_contract.py +
  tests/test_action_plan_v3_integration.py（结构化列守卫）。变更词表需 bump
  ``ACTION_PLAN_SCHEMA_VERSION`` 并过两位 reviewer。

消费方接入点：
- Planner / Aurora（proposal 生成）：构造 ``ActionPlanContract`` → ``validate()`` →
  ``apply_to_task(task)``；
- TaskService（REST 写路径）：``app.schemas.task.ActionPlanIn`` 在 parse 时归一化 +
  全量校验，service 落列；``Task.action_plan`` 属性供 ``TaskDetail`` 读回；
- card_protocol（目标协议，文档级映射见 v3-output/X-01/REPORT.md）：TASK card
  metadata 增量携带 V3 块，切换前不落 card_protocol 代码。

读侧统一门（X-01 返修 F1/F2，REVIEW_RECEIPT_2）：REST 投影（``Task.action_plan``）与
类型化重构（``action_plan_from_task``）**必须**走同一个 ``action_plan_projection``——
版本门 + 全封闭词表 + execution_mode 归一，任一不过 → 整块降级为 None + WARN 日志
（可观测降级）。禁止任何读路径绕过此门直接投影列值（曾使单行脏数据打挂
GET /tasks 等全部任务端点）。

消费方组合指引（F5，文档级警示，上 UI 消费卡前必须落成硬规则）：
- ``agent × user_core``：定义级矛盾（user_core 不可委托只交结果），Planner 产出此组合时必须改写；
- ``hybrid × delegated``：hybrid 必有 human 决策点，与 delegated 否认参与矛盾；
- ``human × shared``：shared 的 "Agent checks" 阶段在 human 模式无执行载体。

与 V2 ``tasks.success_criteria`` 的优先级规则（F6）：``action_schema_version`` 非空时
``desired_outcome`` 为唯一完成标准语义，``success_criteria`` 视为 V2 遗留冻结展示；
两者并存期间 UI 不得同时呈现为生效标准。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, replace
from typing import Any

from loguru import logger

from app.models.execution_intent import ExecutionMode
from app.models.task import CognitiveOwnership, RiskClass

ACTION_PLAN_SCHEMA_VERSION = "action_plan.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 契约版本并过两位 reviewer）
# ---------------------------------------------------------------------------

#: plan 侧「什么算完成证据」的类型（ACTION_AND_INTERVENTION_ENGINE §4 的机制化）。
#: 文件、代码、答题结果、用户确认、自报结果、系统事件。
EVIDENCE_KINDS: frozenset[str] = frozenset(
    {
        "artifact",  # 产生可检查的产物（笔记/文档/作品）
        "file",  # 上传/落盘文件
        "code",  # 可运行/可评审的代码
        "quiz_result",  # 答题/测验结果
        "user_confirmation",  # 用户显式确认完成
        "self_report",  # 自报结果（低信任，outcome 侧分级属 D-01）
        "system_event",  # 系统事件（如 streak/专注会话记录）
    }
)

#: smallest_useful_step 的「为什么算 useful」——ACTION_AND_INTERVENTION_ENGINE §2 的
#: 六条判据。空集 = 「打开 IDE 看一眼」式伪步骤，契约层拒绝。
USEFUL_STEP_REASONS: frozenset[str] = frozenset(
    {
        "produces_artifact",  # 产生 artifact
        "reduces_uncertainty",  # 消除关键 uncertainty
        "builds_capability",  # 形成可验证能力
        "unblocks_dependency",  # 解锁依赖
        "enables_decision",  # 完成真实决策
        "advances_goal",  # 使 goal state 实质前进
    }
)

#: source_refs 的封闭 ref scheme。前 5 个与 C-01 decision_context.v1 的
#: DECISION_REF_SCHEMES 完全一致（ref 语义对齐）；后 6 个为 action 域扩展。
ACTION_SOURCE_REF_SCHEMES: frozenset[str] = frozenset(
    {
        # ── C-01 对齐（勿改名） ──────────────────────────────────────────
        "memory",  # memory://episodic/<id> 等 memory 真源
        "user_state",  # user_state://<field>（state_aggregator 投影）
        "plan",  # plan://<plan_id>
        "document",  # document://<file_id>
        "profile",  # profile://<user_id 或 profile 段>
        # ── action 域扩展 ──────────────────────────────────────────────
        "goal",  # goal://<goal_id>
        "task",  # task://<task_id>（依赖/前置任务）
        "subtask",  # subtask://<subtask_id>
        "chat",  # chat://<message_id>（来源对话）
        "decision",  # decision://<decision_record_id>
        "run",  # run://<execution_intent_id>（D-01 lineage 的 run 域）
    }
)


class EvidenceKind(enum.StrEnum):
    ARTIFACT = "artifact"
    FILE = "file"
    CODE = "code"
    QUIZ_RESULT = "quiz_result"
    USER_CONFIRMATION = "user_confirmation"
    SELF_REPORT = "self_report"
    SYSTEM_EVENT = "system_event"


class UsefulStepReason(enum.StrEnum):
    PRODUCES_ARTIFACT = "produces_artifact"
    REDUCES_UNCERTAINTY = "reduces_uncertainty"
    BUILDS_CAPABILITY = "builds_capability"
    UNBLOCKS_DEPENDENCY = "unblocks_dependency"
    ENABLES_DECISION = "enables_decision"
    ADVANCES_GOAL = "advances_goal"


# ORM 侧枚举（CognitiveOwnership / RiskClass）定义在 app.models.task（与 TaskType
# 同址），此处仅 re-export 供消费方单点导入。
__all__ = [
    "ACTION_PLAN_SCHEMA_VERSION",
    "ACTION_SOURCE_REF_SCHEMES",
    "EVIDENCE_KINDS",
    "USEFUL_STEP_REASONS",
    "ActionPlanContract",
    "CognitiveOwnership",
    "CompletionEvidenceSpec",
    "EvidenceKind",
    "RiskClass",
    "SmallestUsefulStep",
    "UsefulStepReason",
    "action_plan_from_task",
    "action_plan_projection",
    "clear_action_plan",
    "normalize_execution_mode",
]


def normalize_execution_mode(raw: Any) -> ExecutionMode | None:
    """把历史/客户端大小写不一的 execution_mode 归一到 ExecutionMode 词表。

    ``tasks.execution_mode`` 是 String(20) 既有镜像列（ExecutionMode.value 小写为
    今日写入惯例）；DTO 边界统一经此归一，未知值返回 None（由调用方决定拒绝）。
    """
    if isinstance(raw, ExecutionMode):
        return raw
    if raw is None:
        return None
    if isinstance(raw, enum.Enum):
        raw = getattr(raw, "value", raw)
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return ExecutionMode(raw.strip().lower())
    except ValueError:
        return None


def _ref_scheme(ref: str) -> str:
    return ref.split("://", 1)[0] if "://" in ref else ""


# ---------------------------------------------------------------------------
# 契约 dataclass（字段集被 tests/unit/test_action_plan_contract.py 冻结）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SmallestUsefulStep:
    """最小有用步骤：描述 + 「为什么 useful」的封闭判据集（非自然语言自证）。"""

    description: str
    useful_because: tuple[str, ...]

    def validate(self) -> tuple[str, ...]:
        violations: list[str] = []
        if not (self.description or "").strip():
            violations.append("smallest_useful_step.description must be non-empty")
        reasons = tuple(self.useful_because or ())
        if not reasons:
            violations.append("smallest_useful_step.useful_because must be non-empty (伪步骤不合法)")
        unknown = set(reasons) - USEFUL_STEP_REASONS
        if unknown:
            violations.append(f"useful_because out of vocabulary: {sorted(unknown)}")
        return tuple(violations)

    def to_dict(self) -> dict[str, Any]:
        return {"description": self.description, "useful_because": list(self.useful_because)}


@dataclass(frozen=True)
class CompletionEvidenceSpec:
    """单条完成证据规格：必须类型化（evidence_kind 封闭枚举），ref 可选。"""

    evidence_kind: str | None
    ref: str | None = None
    description: str | None = None

    def validate(self) -> tuple[str, ...]:
        violations: list[str] = []
        if self.evidence_kind not in EVIDENCE_KINDS:
            violations.append(f"completion_evidence.evidence_kind must be one of {sorted(EVIDENCE_KINDS)}")
        if self.ref is not None and _ref_scheme(self.ref) not in ACTION_SOURCE_REF_SCHEMES:
            violations.append(f"completion_evidence.ref has unknown scheme: {self.ref!r}")
        return tuple(violations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_kind": self.evidence_kind,
            "ref": self.ref,
            "description": self.description,
        }


@dataclass(frozen=True)
class ActionPlanContract:
    """ActionPlan V3：tasks 域单条任务的结构化行动契约（proposal 侧）。

    落库形态 = ``to_task_columns()`` 展开到 ``tasks`` 表的 9 列（execution_mode 复用
    既有列）；``action_schema_version IS NULL`` 的行为 legacy（V2.x），读取端
    ``action_plan_from_task`` 对 legacy 返回 None。
    """

    desired_outcome: str
    smallest_useful_step: SmallestUsefulStep
    completion_evidence: tuple[CompletionEvidenceSpec, ...]
    execution_mode: ExecutionMode
    cognitive_ownership: CognitiveOwnership
    source_refs: tuple[str, ...] = ()
    risk_class: RiskClass | None = None
    reversible: bool | None = None
    schema_version: str = ACTION_PLAN_SCHEMA_VERSION

    def validate(self) -> tuple[str, ...]:
        violations: list[str] = []
        if self.schema_version != ACTION_PLAN_SCHEMA_VERSION:
            violations.append(f"schema_version mismatch: {self.schema_version!r}")
        if not (self.desired_outcome or "").strip():
            violations.append("desired_outcome must be non-empty")
        if not isinstance(self.execution_mode, ExecutionMode):
            violations.append(f"execution_mode must be ExecutionMode, got {self.execution_mode!r}")
        if not isinstance(self.cognitive_ownership, CognitiveOwnership):
            violations.append(f"cognitive_ownership must be CognitiveOwnership, got {self.cognitive_ownership!r}")
        violations.extend(self.smallest_useful_step.validate())
        if not self.completion_evidence:
            violations.append("completion_evidence must contain at least one typed entry")
        for evidence in self.completion_evidence:
            violations.extend(evidence.validate())
        if self.risk_class is not None and not isinstance(self.risk_class, RiskClass):
            violations.append(f"risk_class must be RiskClass, got {self.risk_class!r}")
        for ref in self.source_refs or ():
            if _ref_scheme(ref) not in ACTION_SOURCE_REF_SCHEMES:
                violations.append(f"source ref has unknown or missing scheme: {ref!r}")
        return tuple(violations)

    def to_task_columns(self) -> dict[str, Any]:
        """契约 → tasks 表列值（service 写路径的唯一展开点）。"""
        return {
            "action_schema_version": self.schema_version,
            "desired_outcome": self.desired_outcome,
            "smallest_useful_step": self.smallest_useful_step.to_dict(),
            "completion_evidence": [entry.to_dict() for entry in self.completion_evidence],
            "execution_mode": self.execution_mode.value,
            "cognitive_ownership": self.cognitive_ownership.value,
            "source_refs": list(self.source_refs),
            "risk_class": self.risk_class.value if self.risk_class else None,
            "reversible": self.reversible,
        }

    def apply_to_task(self, task: Any) -> None:
        """把契约写到 Task ORM 对象（幂等：整块覆盖 V3 列）。"""
        for column, value in self.to_task_columns().items():
            setattr(task, column, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "desired_outcome": self.desired_outcome,
            "smallest_useful_step": self.smallest_useful_step.to_dict(),
            "completion_evidence": [entry.to_dict() for entry in self.completion_evidence],
            "execution_mode": self.execution_mode.value,
            "cognitive_ownership": self.cognitive_ownership.value,
            "source_refs": list(self.source_refs),
            "risk_class": self.risk_class.value if self.risk_class else None,
            "reversible": self.reversible,
        }

    def replace(self, **changes: Any) -> ActionPlanContract:
        return replace(self, **changes)


def action_plan_projection(task: Any) -> dict[str, Any] | None:
    """统一读侧门（F1/F2）：REST 投影与类型化重构共用，禁止绕过。

    判别顺序（任一不过 → 整块 None + WARN）：
    1. ``action_schema_version`` 为空 → legacy 行（正常态，**不打日志**）；
    2. 版本门：schema_version != ACTION_PLAN_SCHEMA_VERSION；
    3. execution_mode 归一失败（镜像列词表外值）；
    4. 结构完整 + 全封闭词表（useful_because / evidence_kind / cognitive_ownership /
       risk_class / source_refs scheme）。

    降级必须留痕：WARN 带 task 标识与原因——区分「没有 V3 计划」与「V3 计划损坏/版本不符」。
    版本 bump 未迁移存量行时该 WARN 会随读放大（已知代价，观测优先于静默；可加限流）。
    """
    schema_version = getattr(task, "action_schema_version", None)
    if not schema_version:
        return None

    def _degrade(reason: str) -> None:
        task_id = getattr(task, "id", None)
        logger.warning("ActionPlan V3 投影降级为 legacy (task_id={}): {}", task_id, reason)

    mode = normalize_execution_mode(getattr(task, "execution_mode", None))
    if mode is None:
        _degrade(f"execution_mode {getattr(task, 'execution_mode', None)!r} missing or out of vocabulary")
        return None
    if schema_version != ACTION_PLAN_SCHEMA_VERSION:
        _degrade(f"schema_version {schema_version!r} != {ACTION_PLAN_SCHEMA_VERSION!r} (版本门)")
        return None
    desired_outcome = getattr(task, "desired_outcome", None)
    if not desired_outcome or not isinstance(desired_outcome, str):
        _degrade("desired_outcome missing or not a string (半写行?)")
        return None
    step_raw = getattr(task, "smallest_useful_step", None) or {}
    useful_because = tuple(step_raw.get("useful_because") or ())
    if not (step_raw.get("description") and useful_because):
        _degrade("smallest_useful_step incomplete (description/useful_because)")
        return None
    if not (set(useful_because) <= USEFUL_STEP_REASONS):
        _degrade(f"useful_because out of vocabulary: {sorted(set(useful_because) - USEFUL_STEP_REASONS)}")
        return None
    evidence_raw = getattr(task, "completion_evidence", None) or []
    evidence = tuple(entry for entry in evidence_raw if isinstance(entry, dict))
    if not evidence:
        _degrade("completion_evidence empty or non-dict entries")
        return None
    for entry in evidence:
        if entry.get("evidence_kind") not in EVIDENCE_KINDS:
            _degrade(f"completion_evidence.evidence_kind {entry.get('evidence_kind')!r} out of vocabulary")
            return None
        ref = entry.get("ref")
        if ref is not None and _ref_scheme(ref) not in ACTION_SOURCE_REF_SCHEMES:
            _degrade(f"completion_evidence.ref unknown scheme: {ref!r}")
            return None
    ownership_raw = getattr(task, "cognitive_ownership", None)
    ownership_value = ownership_raw.value if isinstance(ownership_raw, CognitiveOwnership) else ownership_raw
    if ownership_value not in {member.value for member in CognitiveOwnership}:
        _degrade(f"cognitive_ownership {ownership_raw!r} out of vocabulary")
        return None
    risk_raw = getattr(task, "risk_class", None)
    risk_value = risk_raw.value if isinstance(risk_raw, RiskClass) else risk_raw
    if risk_value is not None and risk_value not in {member.value for member in RiskClass}:
        _degrade(f"risk_class {risk_raw!r} out of vocabulary")
        return None
    source_refs = tuple(getattr(task, "source_refs", None) or ())
    for ref in source_refs:
        if _ref_scheme(ref) not in ACTION_SOURCE_REF_SCHEMES:
            _degrade(f"source ref unknown scheme: {ref!r}")
            return None

    return {
        "schema_version": schema_version,
        "desired_outcome": desired_outcome,
        "smallest_useful_step": {"description": step_raw.get("description"), "useful_because": list(useful_because)},
        "completion_evidence": [
            {
                "evidence_kind": entry.get("evidence_kind"),
                "ref": entry.get("ref"),
                "description": entry.get("description"),
            }
            for entry in evidence
        ],
        "execution_mode": mode.value,
        "cognitive_ownership": ownership_value,
        "source_refs": list(source_refs),
        "risk_class": risk_value,
        "reversible": getattr(task, "reversible", None),
    }


def action_plan_from_task(task: Any) -> ActionPlanContract | None:
    """从 Task 行重构契约；与 REST 投影共用 ``action_plan_projection`` 统一门。

    legacy 行（action_schema_version NULL）→ None；脏/未来值行 → None（同一门，
    同一次 WARN）——两条读路径对同一行永远给出同一答案。
    """
    projection = action_plan_projection(task)
    if projection is None:
        return None
    return ActionPlanContract(
        desired_outcome=projection["desired_outcome"],
        smallest_useful_step=SmallestUsefulStep(
            description=projection["smallest_useful_step"]["description"],
            useful_because=tuple(projection["smallest_useful_step"]["useful_because"]),
        ),
        completion_evidence=tuple(
            CompletionEvidenceSpec(
                evidence_kind=entry["evidence_kind"],
                ref=entry["ref"],
                description=entry["description"],
            )
            for entry in projection["completion_evidence"]
        ),
        execution_mode=ExecutionMode(projection["execution_mode"]),
        cognitive_ownership=CognitiveOwnership(projection["cognitive_ownership"]),
        source_refs=tuple(projection["source_refs"]),
        risk_class=RiskClass(projection["risk_class"]) if projection["risk_class"] else None,
        reversible=projection["reversible"],
        schema_version=projection["schema_version"],
    )


def clear_action_plan(task: Any) -> None:
    """显式清除 V3 语义：任务回到 legacy 形态（V2.x 兼容路径）。"""
    for column in (
        "action_schema_version",
        "desired_outcome",
        "smallest_useful_step",
        "completion_evidence",
        "cognitive_ownership",
        "source_refs",
        "risk_class",
        "reversible",
    ):
        setattr(task, column, None)
