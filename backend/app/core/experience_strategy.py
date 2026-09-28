"""V4-I05 · 经验策略影子验证与有界启用 —— 策略候选的影子对照 + 有界 live 门（纯函数层）。

定位（v4/04_tasks/cards/V4-I05.md + v4/03_intelligence/EXPERIENCE_AND_LEARNING.md
「学习闭环」：``策略候选shadow → 满足发布门后有限live → 持续看负迁移 → 可回退``）：
A-05 policy patch 已有六面白名单 + 真源证据门 + 版本化（``policy_patch`` 契约层），
但候选从 evidenced 到 active 只有档位一个条件（repeated 即自动激活），缺三块：

1. **影子对照（本模块核心）**：策略候选启用前先在**影子臂**里跑「若启用会改变
   什么」的两臂投影——control 臂（不启用）/ treatment 臂（启用后经既有
   ``reorder_nominations`` 单一权威重排），差量内容寻址可审计；shadow 档下
   该投影**只观察**（指标+结构化日志），决策路径零变化（I04 shadow 红线同律：
   shadow 返回与 off 逐字节恒等）。
2. **有界启用（bounded live）**：live 档启用带显式边界——
   - 作用域：patch 既有 scope 绑定（goal_type/friction_tag 精确匹配，V3 语义）；
   - 时长：激活时缺省补观察窗（``expires_at`` = now + 服务层配置窗口小时数），
     窗过即 expired（既有读时门收敛）；
   - 前置条件：``precondition_verdict``——precondition 事实缺失 fail-closed
     不启用；``do_not_apply_when`` 命中即门出（``human_required_step`` 对齐
     I07 human_required/mastery 硬规则——经验启用**结构性不绕过**该门：patch
     应用面只经 A-02/X-02 既有守卫，本层不新增任何绕行通道）；
   - 回退：既有 revoke（终态 + 审计）+ 行为开关回 off/shadow。
3. **证据纪律（验收②③的判定面）**：
   - **缺失结果 censored**：观察面（``ObservationFace``）只从 M-06 记录的方向
     谓词取方向证据（``has_positive/negative_association_evidence``——censored/
     unknown 计数原样保留、永不产生方向；M-06 红线 1 的消费侧同律，零重实现）；
     ``benefit_verdict`` 对 censored-only 的观察给
     ``censored_insufficient_evidence``——既不是收益也不是失败（不能给负 reward
     逼系统更强催促）。
   - **重复摘要不累积为多源证据**：``fold_evidence_refs`` 保序折叠（同一引用
     重复 N 次 = 1 条证据）；服务层在 propose 入口折叠后落库 → 档位只按唯一
     引用计（重复引用无法把 single_observation 顶成 repeated 绕过确认门）。
   - **负向证据参与收益判定（negative evidence 补齐）**：prefer 需正向计数
     **严格大于**负向（失败等价保留——平手/反超 = ``no_benefit``），demote
     对称；无收益策略 live 档不静默自动启用（留 evidenced 等显式 confirm）。
4. **撤回传播（验收③，D03 strategy 面消费）**：证据源被撤回（D03
   ``RetractionKind`` 三类）后引用它的策略**失效**——``strategy_withdrawal_plan``
   复用 D03 ``plan_recompute`` 依赖索引（face=``DerivedFace.STRATEGY``，精确
   ``SourcePointer`` 身份对），命中者由服务层 revoke（actor=``evidence_withdrawal``，
   理由 ``evidence_source_withdrawn`` 入审计历史）；unaffected（合法其他来源）
   显式保留——不删不改。

纪律（不造第二权威）：
- **六表面权限封闭**：策略卡 surface 必须 ∈ ``POLICY_PATCH_SURFACES``（恰好
  六面），payload 经既有 ``validate_patch_request``（V1/V2/V3 fail-closed）——
  「prompt/code/任意新字段」没有合法 surface 名，走不到任何写路径（卡面验收①：
  不新增任意 prompt/code 字段，不越六表面权限——结构保证，非约定）；
- **重排/因子投影单一权威**：影子 treatment 臂直接调用 A-05 既有
  ``reorder_nominations`` + 因子投影函数（本模块零第二实现）；
- **词表零越权**：precondition 值域逐一 import 既有权威（D-05
  ``GOAL_SLICE_TYPES``/``INTERVENTION_FRICTION_TAGS``、I07
  ``hybrid_policy.GOAL_PURPOSES``）；撤回分类/依赖索引 = D03 既有词表；
  本模块自有的封闭词表（模式/门出理由/收益判定）是 I05 输出结构的一部分，
  由冻结测试钉死；
- 零 IO、零模型调用、零写路径、零迁移——本模块只做判定与投影；行为开关
  ``settings.EXPERIENCE_STRATEGY_MODE`` ∈ {off, shadow, live}（默认
  **shadow** = 观察零行为；live 需显式开；未知值 fail-closed 按 off，不猜）。

变更流程：本模块任何词表/判定语义改动需 bump
``EXPERIENCE_STRATEGY_VERSION`` 并过 reviewer（policy_patch/M-06 同款纪律）。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence

from loguru import logger

from app.core.experience_memory import scan_output_for_causal_assertions
from app.core.policy_patch import (
    POLICY_PATCH_SURFACES,
    SURFACE_PAYLOAD_KEYS,
    PolicyPatch,
    validate_patch_request,
)
from app.core.policy_patch import (
    allocation_user_preference as _allocation_preference_value,
)
from app.core.policy_patch import (
    explanation_style as _explanation_style_value,
)
from app.core.policy_patch import (
    proactive_gate_overrides as _proactive_overrides,
)
from app.core.retraction_recompute import (
    CANDIDATE_FACES_BY_KIND,
    DerivedFace,
    DerivedProjection,
    ImpactVerdict,
    RetractionKind,
    SourcePointer,
    plan_recompute,
)

EXPERIENCE_STRATEGY_VERSION = "experience_strategy.v4.i05.v1"

# ---------------------------------------------------------------------------
# 行为开关（off/shadow/live；默认 shadow = 观察零行为；未知值 fail-closed off）
# ---------------------------------------------------------------------------

STRATEGY_MODE_OFF = "off"
STRATEGY_MODE_SHADOW = "shadow"
STRATEGY_MODE_LIVE = "live"

STRATEGY_MODES: frozenset[str] = frozenset({STRATEGY_MODE_OFF, STRATEGY_MODE_SHADOW, STRATEGY_MODE_LIVE})

#: import 期钉死：off ∈ 词表（fail-closed 目标必须自洽）；shadow 无行为语义由
#: 服务层消费测试钉死（本模块只认词表）。
assert STRATEGY_MODE_OFF in STRATEGY_MODES and STRATEGY_MODE_SHADOW in STRATEGY_MODES


def resolve_strategy_mode(value: Any) -> str:
    """模式解析（fail-closed）：未知/空值按 **off**（比 shadow 更严格——不猜）。

    「live 需显式开」：只有字面 ``"live"``（大小写/空白容忍）进 live；任何
    其它值（含拼错的 ``"Live!"``、``"enabled"``）都不可能放大权限。
    """
    mode = str(value or "").strip().lower()
    if mode not in STRATEGY_MODES:
        logger.warning("[ExperienceStrategy] unknown EXPERIENCE_STRATEGY_MODE={!r}; fail-closed to off", value)
        return STRATEGY_MODE_OFF
    return mode


# ---------------------------------------------------------------------------
# 六表面权限封闭（验收①：不越六表面权限）
# ---------------------------------------------------------------------------

#: 本模块消费的 surface 白名单 = A-05 六面**同一对象**（import 复用，非复制）。
#: import 期断言：恰好六面——上游若增删面，本模块立即显式失步（fail-fast），
#: 不允许策略层静默跟随扩权。
STRATEGY_ALLOWED_SURFACES: frozenset[str] = POLICY_PATCH_SURFACES
assert len(STRATEGY_ALLOWED_SURFACES) == 6, "A-05 six-surface whitelist drifted; strategy layer must re-review"


# ---------------------------------------------------------------------------
# 证据折叠（验收②：重复摘要不累积为多源证据）
# ---------------------------------------------------------------------------


def fold_evidence_refs(refs: Iterable[Any]) -> tuple[str, ...]:
    """证据引用保序折叠：精确重复只计一次（lineage 折叠的引用身份面）。

    - 只折叠**全等**引用（``memory://experience/<id>``/``decision://aurora_<id>``
      的身份就是全文——同 id 同真源行，重复出现是重放/汇总伪影不是新证据）；
    - 非字符串成员原样保留（交由 ``validate_patch_request`` 的 V4 拒绝，
      折叠不掩盖形态非法）；
    - 保序去重：首个出现位置定序（确定性输出，重放恒同）。
    """
    seen: set[str] = set()
    folded: list[str] = []
    duplicates = 0
    for ref in refs:
        if isinstance(ref, str):
            if ref in seen:
                duplicates += 1
                continue
            seen.add(ref)
            folded.append(ref)
        else:
            folded.append(ref)
    if duplicates:
        logger.debug("[ExperienceStrategy] folded {} duplicate evidence refs", duplicates)
    return tuple(folded)


#: 空源集版本常量（确定性；无证据策略的稳定版本号）。
EVALUATION_VERSION_EMPTY = "evalver_none"


def evaluation_version(source_refs: Sequence[str]) -> str:
    """折叠源集的内容寻址版本（``evalver_<sha256[:16]>``）。

    版本输入 = **折叠后**排序引用——同一策略的证据集任一变化（新观察窗口、
    源撤回后重投影）→ 版本必然变化；重复引用不改变版本（折叠语义一致）。
    """
    folded = fold_evidence_refs(source_refs)
    if not folded:
        return EVALUATION_VERSION_EMPTY
    digest = hashlib.sha256("\n".join(sorted(folded)).encode("utf-8")).hexdigest()[:16]
    return f"evalver_{digest}"


# ---------------------------------------------------------------------------
# 观察面（验收②：缺失结果 censored；方向证据只来自 M-06 方向谓词）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ObservationFace:
    """策略的同域观察面（相关性计数；零因果断言字段）。

    - ``n_positive``/``n_negative``：唯一源记录的方向计数和（M-06
      ``observed_with_positive/negative`` 原样投影——相关性，非效果）；
    - ``censored_total``/``n_unknown``：观察完整性计数（保留但**永不**进入
      ``has_direction_evidence``——缺失结果是删失，不是失败也不是收益）；
    - ``n_refs_raw``/``n_refs_folded``：折叠面（raw > folded 即发生过重复
      摘要折叠，审计可见）。
    """

    n_positive: int = 0
    n_negative: int = 0
    censored_total: int = 0
    n_unknown: int = 0
    n_records: int = 0
    n_refs_raw: int = 0
    n_refs_folded: int = 0

    @property
    def evidence_count(self) -> int:
        """观察子集 = 正 + 负（失败等价保留；censored/unknown 永不入）。"""
        return self.n_positive + self.n_negative

    @property
    def has_direction_evidence(self) -> bool:
        return self.evidence_count > 0

    @property
    def duplicate_folded_count(self) -> int:
        return max(0, self.n_refs_raw - self.n_refs_folded)

    def to_dict(self) -> dict[str, int]:
        return {
            "n_positive": self.n_positive,
            "n_negative": self.n_negative,
            "censored_total": self.censored_total,
            "n_unknown": self.n_unknown,
            "n_records": self.n_records,
            "n_refs_raw": self.n_refs_raw,
            "n_refs_folded": self.n_refs_folded,
            "evidence_count": self.evidence_count,
            "duplicate_folded_count": self.duplicate_folded_count,
        }


#: ObservationFace 序列化键集（冻结）。
OBSERVATION_FACE_KEYS: tuple[str, ...] = (
    "n_positive",
    "n_negative",
    "censored_total",
    "n_unknown",
    "n_records",
    "n_refs_raw",
    "n_refs_folded",
    "evidence_count",
    "duplicate_folded_count",
)


def observation_face_from_records(
    records: Iterable[Any],
    *,
    source_refs: Sequence[str] = (),
) -> ObservationFace:
    """M-06 记录序列 → 观察面（每条**唯一**记录计一次；censored 纪律消费侧）。

    方向计数只读 M-06 记录的 ``observed_with_positive/negative``（其上游 D-05
    已把 censored/unknown 排除在 n_positive/n_negative 之外）；censored/unknown
    计数原样累加进完整性面。鸭子类型消费（``record_id`` 去重），不 import 具体类。
    """
    folded_refs = fold_evidence_refs(source_refs)
    seen_ids: set[str] = set()
    n_positive = n_negative = censored = unknown = 0
    n_records = 0
    for record in records:
        record_id = str(getattr(record, "record_id", "") or id(record))
        if record_id in seen_ids:
            continue  # 同一记录（同窗口重放）不二次累计——重复摘要不累积
        seen_ids.add(record_id)
        n_records += 1
        n_positive += int(getattr(record, "observed_with_positive", 0) or 0)
        n_negative += int(getattr(record, "observed_with_negative", 0) or 0)
        censored += (
            int(getattr(record, "censored_not_yet_due", 0) or 0)
            + int(getattr(record, "censored_window_closed", 0) or 0)
            + int(getattr(record, "censored_user_churned", 0) or 0)
        )
        unknown += int(getattr(record, "n_unknown_status", 0) or 0)
    return ObservationFace(
        n_positive=n_positive,
        n_negative=n_negative,
        censored_total=censored,
        n_unknown=unknown,
        n_records=n_records,
        n_refs_raw=len(tuple(source_refs)),
        n_refs_folded=len(folded_refs),
    )


# ---------------------------------------------------------------------------
# 收益判定（验收③：无收益策略不静默启用；负向证据参与判定）
# ---------------------------------------------------------------------------

BENEFIT_OBSERVED = "benefit_observed"
BENEFIT_NO_BENEFIT = "no_benefit"
BENEFIT_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
BENEFIT_CENSORED_INSUFFICIENT = "censored_insufficient_evidence"

#: 收益判定词表（封闭）。censored 是**显式不结论**（与 no_benefit 区分——
#: 缺失结果不能当失败计，也不能当收益计）。
BENEFIT_VERDICTS: frozenset[str] = frozenset(
    {BENEFIT_OBSERVED, BENEFIT_NO_BENEFIT, BENEFIT_INSUFFICIENT_EVIDENCE, BENEFIT_CENSORED_INSUFFICIENT}
)

#: 方向需求（A-05 证据门同词表：prefer → positive / demote → negative）。
BENEFIT_DIRECTIONS: frozenset[str] = frozenset({"positive", "negative"})


def benefit_verdict(face: ObservationFace, *, required_direction: str) -> str:
    """收益判定（可解释规则；稀少样本不做概率装饰）。

    - 无观察子集：有删失/unknown → ``censored_insufficient_evidence``（显式
      不结论）；完全无观察 → ``insufficient_evidence``；
    - 有观察：所需方向计数**严格大于**反向才 ``benefit_observed``（负向证据
      等权参与——平手或反超即 ``no_benefit``，失败不降级不隐藏）。
    """
    if required_direction not in BENEFIT_DIRECTIONS:
        raise ValueError(f"required_direction {required_direction!r} out of vocabulary")
    if not face.has_direction_evidence:
        if face.censored_total > 0 or face.n_unknown > 0:
            return BENEFIT_CENSORED_INSUFFICIENT
        return BENEFIT_INSUFFICIENT_EVIDENCE
    if required_direction == "positive":
        return BENEFIT_OBSERVED if face.n_positive > face.n_negative else BENEFIT_NO_BENEFIT
    return BENEFIT_OBSERVED if face.n_negative > face.n_positive else BENEFIT_NO_BENEFIT


# ---------------------------------------------------------------------------
# 策略卡（A-05 patch 的纯投影信封；零存储、可随时确定性重建）
# ---------------------------------------------------------------------------

#: do_not_apply_when 封闭词表（每个键有既有权威落点）：
#: - ``human_required_step``：决策情境声明当前步 human_required（I07 掌握门；
#:   经验启用不得绕过 human_required/mastery 门）；
#: - ``user_revoked``：同内容 patch 曾被用户纠正撤销（内容寻址 id 复活被状态机
#:   结构性阻断——本键是**审计显式面**，服务层消费时如实回报）；
#: - ``cross_domain_transfer``：情境在策略 scope 之外（跨域转移只做影子实验，
#:   不默认启用——EXPERIENCE_AND_LEARNING §经验卡）。
DO_NOT_APPLY_KEYS: frozenset[str] = frozenset({"human_required_step", "user_revoked", "cross_domain_transfer"})

#: precondition 键封闭词表（值域逐一 import 既有权威，零复制零漂移）。
PRECONDITION_FACT_KEYS: frozenset[str] = frozenset({"goal_type", "friction_tag", "execution_mode", "goal_purpose"})

#: 门出理由（封闭；审计面用，非 POLICY_PATCH_REASONS 成员——A-05 核心词表零改动）。
GATE_REASONS: frozenset[str] = frozenset(
    {
        "precondition_unmet",
        "missing_fact",
        "do_not_apply_human_required_step",
        "do_not_apply_user_revoked",
        "do_not_apply_cross_domain_transfer",
        "window_closed",
    }
)


def _precondition_value_vocabulary(key: str) -> frozenset[str]:
    """precondition 值域（既有权威 import，不复制）。"""
    from app.core.intervention_lifecycle import EXECUTION_MODE_SLICES, GOAL_SLICE_TYPES, INTERVENTION_FRICTION_TAGS

    if key == "goal_type":
        return GOAL_SLICE_TYPES
    if key == "friction_tag":
        return INTERVENTION_FRICTION_TAGS
    if key == "execution_mode":
        return EXECUTION_MODE_SLICES
    if key == "goal_purpose":
        from app.core.hybrid_policy import GOAL_PURPOSES

        return GOAL_PURPOSES
    raise ValueError(f"unknown precondition key {key!r}")


@dataclass(frozen=True)
class ExperienceStrategyCard:
    """经验策略卡 = A-05 patch 的受控信封（EXPERIENCE_AND_LEARNING §经验卡最小结构）。

    - ``patch_id``：approved_patch_ref（A-05 patch 单一权威；卡不另立身份源）；
    - ``surface``/``payload``：六面之内（构造期经 ``validate_patch_request``
      重验——任意 prompt/code 字段结构上进不来）；
    - ``required_preconditions``：v1 = patch 既有 scope 绑定的显式化
      （goal_type/friction_tag 精确匹配 =「初版仅在同目标生效」）；
    - ``do_not_apply_when``：v1 固定全量评估三键（见 ``DO_NOT_APPLY_KEYS``）；
    - ``observations``/``evaluation_version``/``valid_until``：观察面 + 版本 +
      观察窗（``valid_until`` = patch ``expires_at`` 的卡面视图）。
    """

    strategy_id: str
    patch_id: str
    user_id: str
    surface: str
    payload: Mapping[str, str]
    scope_goal_type: str | None
    scope_friction_tag: str | None
    required_preconditions: tuple[tuple[str, str], ...]
    do_not_apply_when: tuple[str, ...]
    source_refs: tuple[str, ...]
    evaluation_version: str
    observations: ObservationFace
    valid_until: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXPERIENCE_STRATEGY_VERSION,
            "strategy_id": self.strategy_id,
            "patch_id": self.patch_id,
            "user_id": self.user_id,
            "surface": self.surface,
            "payload": dict(self.payload),
            "scope_goal_type": self.scope_goal_type,
            "scope_friction_tag": self.scope_friction_tag,
            "required_preconditions": [[key, value] for key, value in self.required_preconditions],
            "do_not_apply_when": list(self.do_not_apply_when),
            "source_refs": list(self.source_refs),
            "evaluation_version": self.evaluation_version,
            "observations": self.observations.to_dict(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
        }


#: 策略卡序列化顶层键集（冻结）。
STRATEGY_CARD_PAYLOAD_KEYS: tuple[str, ...] = (
    "schema_version",
    "strategy_id",
    "patch_id",
    "user_id",
    "surface",
    "payload",
    "scope_goal_type",
    "scope_friction_tag",
    "required_preconditions",
    "do_not_apply_when",
    "source_refs",
    "evaluation_version",
    "observations",
    "valid_until",
)


def derive_strategy_id(
    *,
    patch_id: str,
    source_refs: Sequence[str],
    valid_until: datetime | None,
    scope_goal_type: str | None,
    scope_friction_tag: str | None,
) -> str:
    """确定性策略 id（``expstrat_<sha256[:32]>``；同 (patch, 折叠源, 窗) 恒同 id）。"""
    seed = json.dumps(
        {
            "schema": EXPERIENCE_STRATEGY_VERSION,
            "patch_id": str(patch_id),
            "source_refs": sorted(fold_evidence_refs(source_refs)),
            "evaluation_version": evaluation_version(source_refs),
            "valid_until": valid_until.isoformat() if valid_until else None,
            "scope_goal_type": scope_goal_type,
            "scope_friction_tag": scope_friction_tag,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "expstrat_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def strategy_card_for_patch(
    patch: PolicyPatch,
    *,
    evidence_records: Iterable[Any] = (),
    now: datetime | None = None,
) -> ExperienceStrategyCard:
    """A-05 patch → 策略卡（纯投影；构造期红线全开，违规 fail-loud）。

    - surface ∈ 六面（越权即 ValueError——验收①结构保证）；
    - payload 经既有 ``validate_patch_request`` 重验（任意新键 = V2 拒绝）；
    - 观察面：evidence_records 中与 patch 证据需求匹配的记录（调用方已按
      scope/需求过滤时直传；本函数再按 ``record_id`` 去重——折叠语义一致）；
    - ``now`` 仅用于幂等（不进 id 种子）。
    """
    if patch.surface not in STRATEGY_ALLOWED_SURFACES:
        raise ValueError(f"surface {patch.surface!r} not in six-surface whitelist (V1)")
    violations = validate_patch_request(
        surface=patch.surface,
        payload=patch.payload,
        evidence_refs=patch.evidence_refs,
        scope_goal_type=patch.scope_goal_type,
        scope_friction_tag=patch.scope_friction_tag,
        provenance=patch.provenance,
    )
    if violations:
        raise ValueError(f"strategy card rejected by A-05 validation: {violations}")

    folded_refs = fold_evidence_refs(patch.evidence_refs)
    face = observation_face_from_records(evidence_records, source_refs=patch.evidence_refs)
    preconditions: list[tuple[str, str]] = []
    if patch.scope_goal_type is not None:
        preconditions.append(("goal_type", patch.scope_goal_type))
    if patch.scope_friction_tag is not None:
        preconditions.append(("friction_tag", patch.scope_friction_tag))
    return ExperienceStrategyCard(
        strategy_id=derive_strategy_id(
            patch_id=patch.patch_id,
            source_refs=folded_refs,
            valid_until=patch.expires_at,
            scope_goal_type=patch.scope_goal_type,
            scope_friction_tag=patch.scope_friction_tag,
        ),
        patch_id=patch.patch_id,
        user_id=patch.user_id,
        surface=patch.surface,
        payload=dict(patch.payload),
        scope_goal_type=patch.scope_goal_type,
        scope_friction_tag=patch.scope_friction_tag,
        required_preconditions=tuple(preconditions),
        do_not_apply_when=tuple(sorted(DO_NOT_APPLY_KEYS)),
        source_refs=folded_refs,
        evaluation_version=evaluation_version(folded_refs),
        observations=face,
        valid_until=patch.expires_at,
    )


# ---------------------------------------------------------------------------
# 前置条件判定（fail-closed；do_not_apply 优先）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PreconditionOutcome:
    """一次启用前置判定：``applicable=False`` 时 ``reasons`` 非空（封闭码）。"""

    applicable: bool
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"applicable": self.applicable, "reasons": list(self.reasons)}


def precondition_verdict(
    card: ExperienceStrategyCard,
    context: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> PreconditionOutcome:
    """启用前置判定（fail-closed；缺事实 = 不启用，绝不猜）。

    判定序（审计序即判定序，冻结）：
    1. 观察窗（``valid_until`` 已过 → ``window_closed``）；
    2. do_not_apply_when（命中即门出——``human_required_step`` 等，键名即理由码）；
    3. required_preconditions（情境事实缺失 → ``missing_fact`` fail-closed；
       值不匹配 → ``precondition_unmet``）。
    """
    blocked: list[str] = []
    if card.valid_until is not None and now is not None and now >= card.valid_until:
        blocked.append("window_closed")
    for key in card.do_not_apply_when:
        if key not in DO_NOT_APPLY_KEYS:
            raise ValueError(f"do_not_apply key {key!r} out of vocabulary")
        if context.get(key):
            blocked.append(f"do_not_apply_{key}")
    for key, value in card.required_preconditions:
        if key not in PRECONDITION_FACT_KEYS:
            raise ValueError(f"precondition key {key!r} out of vocabulary")
        fact = context.get(key)
        if fact is None:
            blocked.append("missing_fact")
        elif str(fact) != str(value):
            blocked.append("precondition_unmet")
    if blocked:
        unknown = [reason for reason in blocked if reason not in GATE_REASONS]
        if unknown:  # 防御：理由码必须封闭（键名拼接面漂移即显式失败）
            raise ValueError(f"gate reasons out of vocabulary: {unknown}")
        return PreconditionOutcome(False, tuple(dict.fromkeys(blocked)))
    return PreconditionOutcome(True, ())


# ---------------------------------------------------------------------------
# 影子对照（两臂投影；treatment 臂经 A-05 单一权威）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShadowComparison:
    """一次影子对照的可审计工件（control / treatment / 差量 / 观察面）。"""

    comparison_id: str
    stage: str
    control_nominated: tuple[str, ...]
    treatment_nominated: tuple[str, ...]
    changed: bool
    cards: tuple[ExperienceStrategyCard, ...]
    gate_outcomes: tuple[tuple[str, PreconditionOutcome], ...]
    benefit_verdicts: tuple[tuple[str, str], ...]
    allocation_user_preference: str | None
    proactive_gate_overrides: Mapping[str, bool]
    explanation_style: str | None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": EXPERIENCE_STRATEGY_VERSION,
            "comparison_id": self.comparison_id,
            "stage": self.stage,
            "control_nominated": list(self.control_nominated),
            "treatment_nominated": list(self.treatment_nominated),
            "changed": self.changed,
            "cards": [card.to_dict() for card in self.cards],
            "gate_outcomes": [
                {"strategy_id": strategy_id, **outcome.to_dict()} for strategy_id, outcome in self.gate_outcomes
            ],
            "benefit_verdicts": [
                {"strategy_id": strategy_id, "verdict": verdict} for strategy_id, verdict in self.benefit_verdicts
            ],
            "allocation_user_preference": self.allocation_user_preference,
            "proactive_gate_overrides": dict(self.proactive_gate_overrides or {}),
            "explanation_style": self.explanation_style,
        }
        violations = scan_output_for_causal_assertions(payload)
        if violations:  # 因果断言字段结构性不存在（M-06 红线 2 的消费侧同律）
            raise ValueError(f"shadow comparison payload violates causal-assertion red line: {violations}")
        return payload


def compare_shadow_arms(
    comparison_id: str,
    *,
    stage: str,
    control_nominated: Sequence[str],
    treatment_nominated: Sequence[str],
    cards: Sequence[ExperienceStrategyCard],
    gate_outcomes: Sequence[tuple[str, PreconditionOutcome]],
    benefit_verdicts: Sequence[tuple[str, str]],
    allocation_user_preference: str | None = None,
    proactive_gate_overrides: Mapping[str, bool] | None = None,
    explanation_style: str | None = None,
) -> ShadowComparison:
    """组装影子对照工件（差量判定 + 内容寻址校验；纯函数）。"""
    control = tuple(str(n) for n in control_nominated)
    treatment = tuple(str(n) for n in treatment_nominated)
    return ShadowComparison(
        comparison_id=str(comparison_id),
        stage=str(stage),
        control_nominated=control,
        treatment_nominated=treatment,
        changed=control != treatment,
        cards=tuple(cards),
        gate_outcomes=tuple(gate_outcomes),
        benefit_verdicts=tuple(benefit_verdicts),
        allocation_user_preference=allocation_user_preference,
        proactive_gate_overrides=dict(proactive_gate_overrides or {}),
        explanation_style=explanation_style,
    )


def derive_comparison_id(
    *,
    stage: str,
    user_id: str,
    control_nominated: Sequence[str],
    treatment_nominated: Sequence[str],
    strategy_ids: Sequence[str],
    evaluation_versions: Sequence[str],
) -> str:
    """对照工件内容寻址 id（``expshadow_<sha256[:16]>``；同输入恒同 id）。"""
    seed = json.dumps(
        {
            "schema": EXPERIENCE_STRATEGY_VERSION,
            "stage": str(stage),
            "user_id": str(user_id),
            "control": list(control_nominated),
            "treatment": list(treatment_nominated),
            "strategies": sorted(strategy_ids),
            "evaluation_versions": sorted(evaluation_versions),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "expshadow_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def apply_live_bounds(
    cards: Sequence[ExperienceStrategyCard],
    context: Mapping[str, Any],
    *,
    now: datetime,
) -> tuple[tuple[ExperienceStrategyCard, ...], tuple[tuple[str, PreconditionOutcome], ...]]:
    """有界启用的应用面过滤（live 语义单一出处；shadow 只观察本函数结果）。

    逐卡 ``precondition_verdict``：通过者进 allowed（随后仍走 A-02/X-02 既有
    守卫面——本函数不产出任何绕行通道）；被门出者带封闭理由码进 gate_outcomes
    （审计面）。
    """
    allowed: list[ExperienceStrategyCard] = []
    gated: list[tuple[str, PreconditionOutcome]] = []
    for card in cards:
        outcome = precondition_verdict(card, context, now=now)
        if outcome.applicable:
            allowed.append(card)
        else:
            gated.append((card.strategy_id, outcome))
    return tuple(allowed), tuple(gated)


def project_treatment_arm(
    nominated: Sequence[str],
    allowed_cards: Sequence[ExperienceStrategyCard],
    evidence_records: Iterable[Any],
    *,
    goal_type: str | None = None,
    friction_tag: str | None = None,
    now: datetime | None = None,
) -> tuple[tuple[str, ...], str | None, Mapping[str, bool], str | None]:
    """treatment 臂投影（重排与因子全部经 A-05 既有纯函数——零第二实现）。"""
    patches = [
        PolicyPatch(
            patch_id=card.patch_id,
            user_id=card.user_id,
            surface=card.surface,
            payload=dict(card.payload),
            state="active",
            scope_goal_type=card.scope_goal_type,
            scope_friction_tag=card.scope_friction_tag,
            evidence_refs=card.source_refs,
        )
        for card in allowed_cards
    ]
    from app.core.policy_patch import reorder_nominations

    ranking = reorder_nominations(
        [str(n) for n in nominated],
        patches,
        goal_type=goal_type,
        friction_tag=friction_tag,
        now=now,
        evidence_records=evidence_records,
    )
    return (
        ranking.nominated,
        _allocation_preference_value(patches),
        _proactive_overrides(patches),
        _explanation_style_value(patches),
    )


def surface_payload_key(surface: str) -> str:
    """面的主语义键（SURFACE_PAYLOAD_KEYS 的显式再出口；未知面 ValueError）。"""
    if surface not in STRATEGY_ALLOWED_SURFACES:
        raise ValueError(f"surface {surface!r} not in six-surface whitelist")
    return SURFACE_PAYLOAD_KEYS[surface]


# ---------------------------------------------------------------------------
# 撤回传播（验收③：撤回源后相关策略失效；D03 strategy 面消费）
# ---------------------------------------------------------------------------

#: 证据引用 → D03 ``SourcePointer`` 身份域（封闭映射；ref 形态由 A-05 V4 门保证）。
SOURCE_POINTER_TYPE_MEMORY = "expmem_record"
SOURCE_POINTER_TYPE_DECISION = "decision_evidence"

SOURCE_POINTER_TYPES: frozenset[str] = frozenset({SOURCE_POINTER_TYPE_MEMORY, SOURCE_POINTER_TYPE_DECISION})


def source_pointer_of_ref(ref: str) -> SourcePointer | None:
    """证据引用 → 来源身份指针（``memory://experience/<rid>``/``decision://aurora_<id>``）。

    词表外/畸形 ref → None（调用方 fail-closed：不能定位来源的策略不参与
    撤回判定——保守不猜）。
    """
    value = str(ref)
    if value.startswith("memory://experience/"):
        rest = value[len("memory://experience/") :]
        if rest.startswith("expmem_") and len(rest) == len("expmem_") + 16:
            return SourcePointer(SOURCE_POINTER_TYPE_MEMORY, rest)
        return None
    if value.startswith("decision://"):
        rest = value[len("decision://") :]
        if rest.startswith("aurora_") and len(rest) == len("aurora_") + 32:
            return SourcePointer(SOURCE_POINTER_TYPE_DECISION, rest)
        return None
    return None


def strategy_withdrawal_plan(
    kind: RetractionKind | str,
    target: SourcePointer,
    cards: Sequence[ExperienceStrategyCard],
) -> tuple[ImpactVerdict, ...]:
    """撤回 → 策略影响判定（D03 ``plan_recompute`` strategy 面；精确身份匹配）。

    - 每张卡 = 一个 ``DerivedProjection(face=STRATEGY, subject_id=strategy_id,
      source_pointers=折叠源的身份指针集)``；
    - 命中 = 卡的任一来源指针与撤回目标**二元组相等**（跨域同值不构成同源——
      D-02 分域同律）；``unaffected`` = 合法其他来源显式保留；
    - 纯函数：同输入恒同判定（回放安全）。
    """
    kind_value = RetractionKind(kind).value
    candidates = CANDIDATE_FACES_BY_KIND[kind_value]
    assert DerivedFace.STRATEGY.value in candidates, "strategy face must be candidate for retraction kind"
    projections = [
        DerivedProjection(
            face=DerivedFace.STRATEGY,
            subject_id=card.strategy_id,
            source_pointers=tuple(
                pointer for pointer in (source_pointer_of_ref(ref) for ref in card.source_refs) if pointer is not None
            ),
        )
        for card in cards
    ]
    return plan_recompute(kind_value, target, projections)


__all__ = [
    "EXPERIENCE_STRATEGY_VERSION",
    "STRATEGY_MODE_OFF",
    "STRATEGY_MODE_SHADOW",
    "STRATEGY_MODE_LIVE",
    "STRATEGY_MODES",
    "STRATEGY_ALLOWED_SURFACES",
    "EVALUATION_VERSION_EMPTY",
    "BENEFIT_OBSERVED",
    "BENEFIT_NO_BENEFIT",
    "BENEFIT_INSUFFICIENT_EVIDENCE",
    "BENEFIT_CENSORED_INSUFFICIENT",
    "BENEFIT_VERDICTS",
    "BENEFIT_DIRECTIONS",
    "DO_NOT_APPLY_KEYS",
    "PRECONDITION_FACT_KEYS",
    "GATE_REASONS",
    "OBSERVATION_FACE_KEYS",
    "STRATEGY_CARD_PAYLOAD_KEYS",
    "SOURCE_POINTER_TYPE_MEMORY",
    "SOURCE_POINTER_TYPE_DECISION",
    "SOURCE_POINTER_TYPES",
    "ObservationFace",
    "ExperienceStrategyCard",
    "PreconditionOutcome",
    "ShadowComparison",
    "resolve_strategy_mode",
    "fold_evidence_refs",
    "evaluation_version",
    "observation_face_from_records",
    "benefit_verdict",
    "derive_strategy_id",
    "strategy_card_for_patch",
    "precondition_verdict",
    "compare_shadow_arms",
    "derive_comparison_id",
    "apply_live_bounds",
    "project_treatment_arm",
    "surface_payload_key",
    "source_pointer_of_ref",
    "strategy_withdrawal_plan",
]
