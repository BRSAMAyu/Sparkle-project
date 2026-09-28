"""V4-D03 · 撤回派生影响与投影重算契约（``retraction.recompute.v1``，冻结词表 + 确定性函数）。

设计真源：``v4/03_intelligence/DATA_AND_GRAPH.md`` §撤回与重算（本卡 specs 明文引用）：

- 「outcome撤回→**依赖索引查受影响**节点/insight/experience→**标pending_recompute**
  →**从仍有效事件按确定顺序重新投影**→**新version发布**。」
- 「Kalman/Bayesian更新**非简单可逆**，**不能直接减去"撤回分"**。」
- 「重算过程中UI显示旧视图已失效/更新中，**不展示双份相矛盾成长**。」
- 「用户删除材料亦使相关引用不可用，但**不自动删除其他合法来源的事实**。」
- 卡 V4-D03 验收：①并发旧job不能复活已删内容；②非线性状态按有效事件回放而非
  减旧分数；③重算中UI与工具均标过期，不继续旧建议。

本模块是**统一层，不是第二权威**——既有权威原样复用、import 期断言钉死：

1. **epoch 机制**（C-07/M-07）：per-user ``memory_epoch`` 是派生状态世代计数唯一
   权威（``app/services/memory_invalidation_pipeline.py``；删除/纠正/权限收紧
   bump）。撤回登记复用**同一个** epoch（不造第二计数器）；一切钉 epoch 的读侧
   门（context 快照、I01 resume freshness、profile context）因此自动判 stale。
2. **revocation 机制**（M-07）：``MemoryInvalidationPipeline``（状态变更+审计+
   epoch bump+``memory.invalidated`` 事件同事务）仍是记忆域撤回唯一写路径；本
   契约的撤回登记是**同构兄弟入口**（结果/推断域），不改动记忆域管线。
3. **能力节点重放**（G-01/V3-FIX-292/299）：融合唯一权威 =
   ``app/services/galaxy/mastery_evidence.recompute_evidence_state``（Kalman 前向
   融合 + 确定顺序 + 幂等）。本模块**不含任何融合数学**——import 期断言其存在，
   重算一律委托；**逆推减分在结构上不可能**（本模块没有任何接收"分数增量"做
   减法的函数位）。
4. **outcome 身份**（D-02）：``outc_<sha256[:32]>``（``derive_outcome_id``）；
   证据账本行到 outcome 的依赖边由 G-02 吸收器写入 ``request_id`` 的 ``oc=``
   分段标记承载（``outcome_absorption_service._evidence_request_id``，分号精确
   分段防 hex 子串碰撞）。本模块提供该标记的**解析/构造**函数，测试与
   G-02 编码器做往返一致性钉死。

新增的最小事实面（此前全仓无）：

- **撤回三分类** :class:`RetractionKind`（封闭）：``material_deleted`` 删除材料
  / ``inference_retracted`` 撤回推断 / ``result_retracted`` 撤回结果。三者是
  不同撤回语义：材料删除使其**引用**不可用；推断撤回移除**派生结论**；结果
  撤回移除**证据来源**。共同纪律：只降级被撤回物自身的派生贡献，**永不**
  连坐其他合法来源（§plan_recompute 的 ``unaffected`` 判定）。
- **撤回身份** :func:`derive_retraction_id`（``rtr_<sha256[:32]>``，内容寻址，
  D-01/D-02 派生风格；**不含时间**）：同一 (user, kind, target) 重放恒同 id
  ——撤回幂等可重放的机制基础（重放登记同一 id，账本不双记）。
- **影响规划** :func:`plan_recompute`：依赖索引判定——派生投影的来源指针集
  （:class:`SourcePointer`，(source_type, source_id) 精确身份对，**无子串、无
  模糊**）含被撤回物 → ``affected``（标 pending_recompute）；不含 →
  ``unaffected``（**保留合法其他来源**，不删除、不改写）。
- **有效事件回放装配** :func:`assemble_valid_replay`：从事件集中剔除被撤回
  身份，按 ``(occurred_at, event_id)`` 确定顺序输出仍有效事件——「按有效事件
  回放」的序语义单一出处。执行侧（galaxy）委托既有重放器，测试钉两者一致。
- **发布栅栏** :func:`evaluate_publish_gate`：重算 job 携带其计算所依据的
  ``base_epoch``；发布时点逐门判定——epoch 已前进（**并发旧job不得写回**）、
  回放输入未含全部已知撤回排除、目标已被删——任一命中即丢弃本次结果（丢弃
  而非部分应用；重算重新入队）。配合**持久墓碑**（账本行
  ``effect_kind='retracted'``，:data:`RETRACTED_EFFECT_KIND`，重放结构性跳过
  ——MasteryEffectKind.RETRACTED，import 期断言一致），旧 job 即使绕过栅栏
  重放账本也拿不回被撤回证据的效果（防御纵深，验收①）。
- **读侧门** :func:`evaluate_read_gate`：pending_recompute 或投影 epoch 落后
  当前 epoch → ``stale=True`` 且 ``suggestions_allowed=False``——UI 标过期与
  工具不继续旧建议是**同一个门的两个出口**（验收③），不存在"UI 标了过期、
  工具还在用旧建议"的分裂态。
- **版本发布** :func:`next_projection_version`：重算发布使逻辑时钟严格 +1，
  永不复位（新 version 发布，DATA_AND_GRAPH 序语义）。

与消费面的衔接（本卡接线范围见 service 层）：星图能力节点走
``app/services/retraction_recompute_service.py``（登记墓碑 + epoch bump +
栅栏下重算写回）；insight/strategy 面为读时计算/后续卡接线，本契约提供统一
判定词表，不在本卡造第二存储。

变更流程：三分类词表/影响判定/栅栏理由/读门语义属冻结契约，改动需 bump
``RETRACTION_RECOMPUTE_SCHEMA_VERSION`` 并过 reviewer（C-01/D-01/D-02/D-05
同款纪律）。
"""

# rule-bj: exempt V4-D03 冻结契约模块（撤回派生影响/投影重算）；生产触发方按卡序接线（结果撤回的 UI/FSM 入口、insight/strategy 面消费）——登记 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Collection, Iterable, Sequence

from app.services.galaxy.mastery_evidence import MasteryEffectKind

RETRACTION_RECOMPUTE_SCHEMA_VERSION = "retraction.recompute.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 契约版本 + reviewer）
# ---------------------------------------------------------------------------


class RetractionKind(StrEnum):
    """撤回三分类（卡面「严格区分删除材料、撤回推断、撤回结果」的机制化）。

    三类共享同一纪律（只移除被撤回物自身的派生贡献），但依赖索引的匹配语义
    不同：材料按引用指针匹配；推断按派生身份匹配；结果按 outcome 依赖边
    （``oc=`` 标记）匹配。**词表成员不得混用**——把材料删除当结果撤回登记会
    走错依赖边，构造期即拒。
    """

    MATERIAL_DELETED = "material_deleted"  # 删除材料（文件撤回/记忆删除 → 引用不可用）
    INFERENCE_RETRACTED = "inference_retracted"  # 撤回推断（派生 insight/策略结论被否）
    RESULT_RETRACTED = "result_retracted"  # 撤回结果（outcome 撤销 → 证据来源移除）


RETRACTION_KINDS: frozenset[str] = frozenset(k.value for k in RetractionKind)


class DerivedFace(StrEnum):
    """受影响派生面（卡面「策略/insight/能力节点」；封闭）。"""

    CAPABILITY_NODE = "capability_node"  # 星图能力节点（G-01 mastery 重放）
    INSIGHT = "insight"  # 洞察卡（读时计算面）
    STRATEGY = "strategy"  # 策略信念（Bayesian 信念快照面）


DERIVED_FACES: frozenset[str] = frozenset(f.value for f in DerivedFace)

#: 各撤回类型的候选受影响面（依赖索引的类型级入口；face 是否真受影响仍由
#: :func:`plan_recompute` 按来源指针逐投影判定——类型只定**候选**，不定结论）。
CANDIDATE_FACES_BY_KIND: dict[str, frozenset[str]] = {
    RetractionKind.MATERIAL_DELETED.value: frozenset(DERIVED_FACES),
    RetractionKind.INFERENCE_RETRACTED.value: frozenset({DerivedFace.INSIGHT.value, DerivedFace.STRATEGY.value}),
    RetractionKind.RESULT_RETRACTED.value: frozenset(DERIVED_FACES),
}


class RecomputeStatus(StrEnum):
    """派生投影重算状态机（``fresh → pending_recompute → recomputed``；可再循环）。"""

    FRESH = "fresh"
    PENDING_RECOMPUTE = "pending_recompute"
    RECOMPUTED = "recomputed"


RECOMPUTE_STATUSES: frozenset[str] = frozenset(s.value for s in RecomputeStatus)


class RetractionImpact(StrEnum):
    """影响判定二值（``unaffected`` 是显式一等结论——保留合法其他来源）。"""

    AFFECTED = "affected"
    UNAFFECTED = "unaffected"


class PublishGateDecision(StrEnum):
    """发布栅栏判定（封闭；``allow`` 之外一律**整体丢弃**，不部分应用）。"""

    ALLOW = "allow"
    DISCARD_STALE_EPOCH = "discard_stale_epoch"  # 并发旧 job：计算所依 epoch 已过期
    DISCARD_MISSING_EXCLUSION = "discard_missing_exclusion"  # 回放输入未含全部已知撤回
    DISCARD_TARGET_GONE = "discard_target_gone"  # 派生目标自身已被删


PUBLISH_GATE_DECISIONS: frozenset[str] = frozenset(d.value for d in PublishGateDecision)

#: 重算中 UI/工具统一过期标记键（冻结文案键位；文案内容归呈现层冻结表）。
STALE_UI_MARKER = "stale_recomputing"

#: 持久墓碑值：mastery_audit_log.effect_kind 的撤回标记（重放结构性跳过）。
#: import 期断言与 G-01 词表一致（MasteryEffectKind.RETRACTED）。
RETRACTED_EFFECT_KIND = "retracted"

_ASSERT_RETRACTED_KIND_CONSISTENT = (
    MasteryEffectKind.RETRACTED.value == RETRACTED_EFFECT_KIND
), "mastery_evidence.MasteryEffectKind.RETRACTED 与 retraction_recompute.RETRACTED_EFFECT_KIND 不一致"

# ---------------------------------------------------------------------------
# 撤回身份（内容寻址，幂等可重放）
# ---------------------------------------------------------------------------


def derive_retraction_id(
    user_id: str,
    kind: RetractionKind | str,
    target_type: str,
    target_id: str,
) -> str:
    """``rtr_<sha256[:32]>``——撤回的幂等身份。

    派生输入 = (user_id, kind, target_type, target_id)，**不含时间/epoch**：
    同一撤回（同一用户对同一目标同类型）任意时点重放恒同 id。登记面据此
    去重（重放不双记事件、不双 bump epoch、不双墓碑）。
    """
    kind_value = RetractionKind(kind).value
    payload = "\x1f".join(
        (
            "retraction.recompute.v1",
            str(user_id),
            kind_value,
            str(target_type),
            str(target_id),
        )
    )
    return f"rtr_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:32]}"


# ---------------------------------------------------------------------------
# outcome 依赖边标记（G-02 ``oc=`` 分段编码的解析/构造；分号精确分段）
# ---------------------------------------------------------------------------


def outcome_marker_hex(outcome_id: str) -> str:
    """outcome id → 32 位 hex（去 ``outc_`` 前缀、去连字符；G-02 同编码）。"""
    text = str(outcome_id).strip().lower()
    if text.startswith("outc_"):
        text = text[len("outc_") :]
    return text.replace("-", "")


def extract_outcome_marker(request_id: str | None) -> str | None:
    """从账本行 ``request_id`` 提取 ``oc=`` 段（分号精确分段，无子串包含）。

    G-02 编码：``obs=60;conf=0.8;oc=<32hex>[;tk=<32hex>]``。段匹配按 ``;``
    精确切分——hex 子串碰撞不构成同因（吸收器原文纪律，本解析同款）。
    无标记/畸形输入 → None（调用方按"无依赖边"处理，不猜）。
    """
    if not request_id:
        return None
    for segment in str(request_id).split(";"):
        if segment.startswith("oc="):
            return segment[len("oc=") :] or None
    return None


# ---------------------------------------------------------------------------
# 影响规划（依赖索引）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourcePointer:
    """来源指针：``(source_type, source_id)`` 精确身份对。

    匹配只认二元组相等；``(type_a, id_x)`` 与 ``(type_b, id_x)`` 不是同一来源
    （D-02 分域纪律同款：值相同不构成身份相同）。
    """

    source_type: str
    source_id: str

    def identity(self) -> tuple[str, str]:
        return (self.source_type, self.source_id)


@dataclass(frozen=True)
class DerivedProjection:
    """派生投影描述子（依赖索引的被检对象；纯描述，不绑定存储形状）。

    ``computed_epoch``：投影计算所钉的派生世代（None=未钉，读门按落后处理）。
    """

    face: DerivedFace | str
    subject_id: str
    source_pointers: tuple[SourcePointer, ...]
    computed_epoch: int | None = None
    status: RecomputeStatus | str = RecomputeStatus.FRESH


@dataclass(frozen=True)
class ImpactVerdict:
    """单投影影响判定（``unaffected`` = 保留合法其他来源，不删不改）。"""

    face: str
    subject_id: str
    impact: RetractionImpact
    matched_pointers: tuple[SourcePointer, ...]


def plan_recompute(
    kind: RetractionKind | str,
    target: SourcePointer,
    projections: Sequence[DerivedProjection],
) -> tuple[ImpactVerdict, ...]:
    """依赖索引判定：哪些派生投影由被撤回物派生（精确身份匹配）。

    - 候选面按撤回类型收窄（:data:`CANDIDATE_FACES_BY_KIND`）；候选面外的投影
      直接 ``unaffected``（不检查指针）；
    - 命中 = 投影的任一 :class:`SourcePointer` 与 target **二元组相等**；
    - 判定是纯函数：同输入恒同判定（回放安全）。
    """
    kind_value = RetractionKind(kind).value
    candidates = CANDIDATE_FACES_BY_KIND[kind_value]
    target_identity = target.identity()
    verdicts: list[ImpactVerdict] = []
    for projection in projections:
        face_value = DerivedFace(projection.face).value
        if face_value not in candidates:
            verdicts.append(
                ImpactVerdict(
                    face=face_value,
                    subject_id=projection.subject_id,
                    impact=RetractionImpact.UNAFFECTED,
                    matched_pointers=(),
                )
            )
            continue
        matched = tuple(p for p in projection.source_pointers if p.identity() == target_identity)
        verdicts.append(
            ImpactVerdict(
                face=face_value,
                subject_id=projection.subject_id,
                impact=RetractionImpact.AFFECTED if matched else RetractionImpact.UNAFFECTED,
                matched_pointers=matched,
            )
        )
    return tuple(verdicts)


# ---------------------------------------------------------------------------
# 有效事件回放装配（「从仍有效事件按确定顺序重新投影」的序语义单一出处）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayEvent:
    """回放事件（最小形状：身份 + 发生时点；载荷留在执行侧权威）。"""

    event_id: str
    occurred_at: datetime | None


@dataclass(frozen=True)
class ValidReplayPlan:
    """回放装配结果（有效事件确定顺序 + 显式排除计数，不静默）。"""

    valid_events: tuple[ReplayEvent, ...]
    removed_event_ids: tuple[str, ...]


def assemble_valid_replay(
    events: Iterable[ReplayEvent],
    retracted_ids: Collection[str],
) -> ValidReplayPlan:
    """剔除被撤回事件身份，按 ``(occurred_at, event_id)`` 确定顺序输出。

    - 排除按**精确身份**（整 id 相等，非子串）；
    - 排序键 ``occurred_at`` 为 None 的事件排在最前（稳定次序仍由 event_id
      决定）——同输入恒同序列（回放安全、幂等）；
    - 被排除身份显式返回（消费方可核对「减掉的是谁」），**不是**静默丢弃。
    """
    retracted = {str(r) for r in retracted_ids}
    kept: list[ReplayEvent] = []
    removed: list[str] = []
    for event in events:
        if event.event_id in retracted:
            removed.append(event.event_id)
        else:
            kept.append(event)
    kept.sort(key=lambda e: (e.occurred_at is not None, e.occurred_at or datetime.min, e.event_id))
    return ValidReplayPlan(valid_events=tuple(kept), removed_event_ids=tuple(removed))


# ---------------------------------------------------------------------------
# 发布栅栏（并发旧 job 不能复活已删内容——验收①的判定面）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PublishGateVerdict:
    decision: PublishGateDecision
    reason_detail: str | None = None

    @property
    def allowed(self) -> bool:
        return self.decision is PublishGateDecision.ALLOW


def evaluate_publish_gate(
    *,
    base_epoch: int | None,
    current_epoch: int | None,
    excluded_ids: Collection[str],
    retracted_ids: Collection[str],
    target_exists: bool,
) -> PublishGateVerdict:
    """重算 job 发布前逐门判定（任一命中 → 整体丢弃，不部分应用）。

    1. **epoch 栅栏**：job 携带 ``base_epoch``（开始计算时读到的派生世代）；
       发布时点 ``current_epoch`` 已前进 ⇒ 计算期间落了新的撤回/删除 ⇒ 本结果
       基于过期世界，丢弃（并发旧 job 写回的栅栏）。任一侧 None（无法钉代）
       按 fail-closed 丢弃——**放行需要两侧世代可证相等**。
    2. **排除完备栅栏**：job 回放输入的排除集必须 ⊇ 当前已知撤回集；缺任何一个
       ⇒ 输入早于某次撤回，丢弃。
    3. **目标存活栅栏**：派生目标（如星图节点）自身已被删 ⇒ 无处发布，丢弃。
    """
    if base_epoch is None or current_epoch is None or int(base_epoch) != int(current_epoch):
        return PublishGateVerdict(
            PublishGateDecision.DISCARD_STALE_EPOCH,
            reason_detail=f"base_epoch={base_epoch} current_epoch={current_epoch}",
        )
    missing = {str(r) for r in retracted_ids} - {str(e) for e in excluded_ids}
    if missing:
        return PublishGateVerdict(
            PublishGateDecision.DISCARD_MISSING_EXCLUSION,
            reason_detail=f"missing_exclusions={sorted(missing)[:8]}",
        )
    if not target_exists:
        return PublishGateVerdict(PublishGateDecision.DISCARD_TARGET_GONE)
    return PublishGateVerdict(PublishGateDecision.ALLOW)


# ---------------------------------------------------------------------------
# 读侧门（重算中 UI 与工具均标过期、不继续旧建议——验收③的判定面）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReadGate:
    """读侧门出口（UI 与工具消费同一个门，不存在分裂态）。"""

    stale: bool
    suggestions_allowed: bool
    ui_marker: str | None
    status: str


def evaluate_read_gate(
    *,
    status: RecomputeStatus | str,
    computed_epoch: int | None,
    current_epoch: int | None,
) -> ReadGate:
    """重算期/世代落后 ⇒ ``stale=True`` 且 ``suggestions_allowed=False``。

    - ``pending_recompute``：重算中——无条件过期（UI 标 ``stale_recomputing``，
      工具不得继续旧建议）；
    - 世代比对：投影钉的 ``computed_epoch`` 落后当前 epoch ⇒ 过期（同出口）；
      ``computed_epoch=None``（未钉）按落后处理（fail-closed）；
    - 两侧世代不可比（current_epoch=None）时不额外判过期——世代语义由各自
      消费面权威（C-07 读侧门）负责，本门不越权代判。
    """
    status_value = RecomputeStatus(status).value
    if status_value == RecomputeStatus.PENDING_RECOMPUTE.value:
        return ReadGate(stale=True, suggestions_allowed=False, ui_marker=STALE_UI_MARKER, status=status_value)
    if current_epoch is not None:
        if computed_epoch is None or int(computed_epoch) < int(current_epoch):
            return ReadGate(stale=True, suggestions_allowed=False, ui_marker=STALE_UI_MARKER, status=status_value)
    return ReadGate(stale=False, suggestions_allowed=True, ui_marker=None, status=status_value)


# ---------------------------------------------------------------------------
# 版本发布（新 version 发布；逻辑时钟不复位）
# ---------------------------------------------------------------------------


def next_projection_version(current_version: int | None) -> int:
    """重算发布使逻辑时钟严格 +1（None/负值按 0 起步；永不回退）。"""
    base = int(current_version) if current_version is not None else 0
    if base < 0:
        base = 0
    return base + 1


# ---------------------------------------------------------------------------
# 状态转移（纯函数；状态机之外不产状态）
# ---------------------------------------------------------------------------


def mark_pending(projection: DerivedProjection) -> DerivedProjection:
    """影响判定命中 ⇒ 标 pending_recompute（世代不变；等待重算发布）。"""
    return DerivedProjection(
        face=projection.face,
        subject_id=projection.subject_id,
        source_pointers=projection.source_pointers,
        computed_epoch=projection.computed_epoch,
        status=RecomputeStatus.PENDING_RECOMPUTE,
    )


def mark_recomputed(projection: DerivedProjection, *, at_epoch: int) -> DerivedProjection:
    """重算发布 ⇒ recomputed + 钉新世代（发布即新鲜起点）。"""
    return DerivedProjection(
        face=projection.face,
        subject_id=projection.subject_id,
        source_pointers=projection.source_pointers,
        computed_epoch=int(at_epoch),
        status=RecomputeStatus.RECOMPUTED,
    )


__all__ = [
    "CANDIDATE_FACES_BY_KIND",
    "DERIVED_FACES",
    "DerivedFace",
    "DerivedProjection",
    "ImpactVerdict",
    "PublishGateDecision",
    "PublishGateVerdict",
    "ReadGate",
    "RECOMPUTE_STATUSES",
    "RETRACTED_EFFECT_KIND",
    "RETRACTION_KINDS",
    "RETRACTION_RECOMPUTE_SCHEMA_VERSION",
    "RecomputeStatus",
    "RetractionImpact",
    "RetractionKind",
    "STALE_UI_MARKER",
    "SourcePointer",
    "ValidReplayPlan",
    "ReplayEvent",
    "assemble_valid_replay",
    "derive_retraction_id",
    "evaluate_publish_gate",
    "evaluate_read_gate",
    "extract_outcome_marker",
    "mark_pending",
    "mark_recomputed",
    "next_projection_version",
    "outcome_marker_hex",
    "plan_recompute",
]
