"""V4-D01 · experience_event.v1 —— 呈现回执 / 呈现投影契约（冻结词表 + 确定性投影器）。

契约真源：v4/evidence/V4-B05/contract_receipt_min.md §3（B05 已 DONE_REVIEWED，
本模块是其实现面；词表/字段/不变量照契约冻结，扩展 = bump 版本过 reviewer——
C-01/X-01/X-03/D-05 同款纪律）。纯 stdlib、无模型参与、确定性：同输入恒同事件。

三条不变量（契约 I1/I2/I3 + §3 E1–E4，本模块强制其中可结构化判定的全部）：

- **E1** ``kind=state_confirmed`` ⇒ ``commit_state=committed`` 且 ``receipt_ref``
  必选。无例外。
- **E2** ``commit_state=error`` ⇒ ``error_state`` 必选；``committed`` ⇒
  ``error_state`` 必为 None（互斥，不混用）。
- **E3/I1** 事件无权限字段：结构封闭（``to_dict`` 键集冻结），消费方不得由
  kind/subject 推导任何写操作资格——本模块不产、也容不下权限语义。
- **E4/I3** ``receipt_ref`` scheme 必须落在封闭集
  （``EXPERIENCE_RECEIPT_REF_SCHEMES``，含 ``intervention_lifecycle://``）内；
  词表外 scheme 拒绝（伪造依据面）。
- **I2** 成功必须可溯源：receipt 必选 kind 的 ``receipt_ref=None`` 在构造期
  直接拒绝（服务层另须查证权威回执真实存在后才投影——见
  ``app/services/experience_event_service.py``）。

commit_state 唯一真源 = X-03 权威回执的 ``TerminalReason`` / ``ACTION_ERROR_CODES``
（``app/core/action_command.py``），本模块提供全函数投影（契约 §6）：

- ``TerminalReason.committed`` → ``(committed, None)``；
- ``TerminalReason.expired`` → ``(error, expired)``；
- ``TerminalReason.user_cancelled / user_rejected`` → **不产生事件**（返回
  None；投影器跳过 + 调用方计数——用户亲自取消/拒绝即时可知，补发属呈现噪音）；
- ``ACTION_ERROR_CODES`` 五值 1:1 映射入 ``error_state``；第 6 值
  ``ACTION_INVALID_COMMAND`` 显式排除——它是命令构造/前置校验期错误，不产生
  权威回执、无 proposal 身份可投影；权威回执若携带它必须 fail-loud
  （:class:`ExperienceProjectionRefused`），不得静默映射（契约 §6 R1-C3 断言）。

与既有权威的关系（不造第二权威）：
- 词表 ``dedupe_key`` 公式照契约冻结：``sha256(receipt_ref + kind +
  subject.version_token)``（内容寻址，FIX-507 内容寻址 decision_id 同款先例）；
- ``event_id`` 派生自 ``dedupe_key``（``eev_<sha256[:32]>``，
  :func:`derive_lifecycle_event_id` D-01/D-02 派生风格）：同权威回执重放恒同
  id，丢事件可重放、消费方按 event_id 安全去重（F03 重播抑制键）。时间字段
  （issued_at/expires_at）**不进** id 派生——重放时点不同不改变事件身份。
"""

from __future__ import annotations

import enum
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

EXPERIENCE_EVENT_SCHEMA_VERSION = "experience_event.v1"

# ---------------------------------------------------------------------------
# 封闭词表（冻结；扩展需 bump 契约版本 + reviewer）
# ---------------------------------------------------------------------------


class ExperienceEventKind(enum.StrEnum):
    """呈现事件 kind（契约 §3 最小七元集；封闭）。"""

    STATE_CONFIRMED = "state_confirmed"
    STATE_SYNCING = "state_syncing"
    CORRECTION_APPLIED = "correction_applied"
    CALIBRATION_NOTICE = "calibration_notice"
    RESUME_AVAILABLE = "resume_available"
    PROGRESS_DELTA = "progress_delta"
    TERMINAL_FAILED = "terminal_failed"


EXPERIENCE_EVENT_KINDS: frozenset[str] = frozenset(k.value for k in ExperienceEventKind)

#: receipt_ref 必选的 kind（契约 §3：null 仅允许 state_syncing / resume_available /
#: terminal_failed 中非命令类）。
RECEIPT_REF_REQUIRED_KINDS: frozenset[str] = frozenset(
    {
        ExperienceEventKind.STATE_CONFIRMED.value,
        ExperienceEventKind.PROGRESS_DELTA.value,
        ExperienceEventKind.CORRECTION_APPLIED.value,
        ExperienceEventKind.CALIBRATION_NOTICE.value,
    }
)

#: ``kind=state_confirmed`` 恒为成功类呈现（E1：⇒ committed）。失败类呈现专用
#: 词表成员是 ``terminal_failed``——五错误态永不混入 committed 呈现（卡验收 3）。
SUCCESS_PRESENTATION_KINDS: frozenset[str] = frozenset({ExperienceEventKind.STATE_CONFIRMED.value})


class ExperienceCommitState(enum.StrEnum):
    """commit 投影态（唯一真源 = X-03 权威回执终态/错误码，上层不得改写）。"""

    COMMITTED = "committed"
    ERROR = "error"


COMMIT_STATE_VOCABULARY: frozenset[str] = frozenset(c.value for c in ExperienceCommitState)


class ExperienceErrorState(enum.StrEnum):
    """error_state 五值（1:1 复用 ``ACTION_ERROR_CODES`` 五值，不造第二词表）。"""

    VERSION_CONFLICT = "version_conflict"
    UNAUTHORIZED = "unauthorized"
    NOT_PENDING = "not_pending"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"


ERROR_STATE_VOCABULARY: frozenset[str] = frozenset(e.value for e in ExperienceErrorState)


class ExperienceSubjectType(enum.StrEnum):
    """subject 类型（契约 §3 六元封闭集；X-03 subject 绑定纪律同款）。"""

    TASK = "task"
    GOAL = "goal"
    RUN = "run"
    INTERVENTION = "intervention"
    MEMORY = "memory"
    PLAN = "plan"


SUBJECT_TYPE_VOCABULARY: frozenset[str] = frozenset(t.value for t in ExperienceSubjectType)


class PresentationModality(enum.StrEnum):
    """呈现模态（文本/像素/声/触统一入口的模态轴；空数组合法——全关价值仍须成立）。"""

    VISUAL = "visual"
    AUDIO = "audio"
    HAPTIC = "haptic"


PRESENTATION_MODALITY_VOCABULARY: frozenset[str] = frozenset(m.value for m in PresentationModality)

#: receipt_ref 封闭 scheme（契约 §3 六元集；E4/I3：词表外 scheme 一律拒绝）。
EXPERIENCE_RECEIPT_REF_SCHEMES: frozenset[str] = frozenset(
    {
        "action_command",  # action_command://<proposal_id>（X-03 权威回执）
        "run",  # run://<run_id>
        "outcome",  # outcome://<outcome_id>（D-02 账本行）
        "intervention_lifecycle",  # intervention_lifecycle://<decision_id>（D-05 exposed 行）
        "calibration_receipt",  # calibration_receipt://<ref>（A-06）
        "context_selection",  # context_selection://<receipt_id>
    }
)

#: ``ACTION_ERROR_CODES`` 第 6 值：显式排除出映射（fail-loud 断言面，见模块 docstring）。
PROJECTION_REFUSED_ERROR_CODE = "ACTION_INVALID_COMMAND"

_ACTION_ERROR_CODE_TO_ERROR_STATE: dict[str, ExperienceErrorState] = {
    "ACTION_VERSION_CONFLICT": ExperienceErrorState.VERSION_CONFLICT,
    "ACTION_UNAUTHORIZED": ExperienceErrorState.UNAUTHORIZED,
    "ACTION_NOT_PENDING": ExperienceErrorState.NOT_PENDING,
    "ACTION_EXPIRED": ExperienceErrorState.EXPIRED,
    "ACTION_NOT_FOUND": ExperienceErrorState.NOT_FOUND,
}

_TERMINAL_REASON_TO_COMMIT: dict[str, tuple[ExperienceCommitState, ExperienceErrorState | None]] = {
    "committed": (ExperienceCommitState.COMMITTED, None),
    "expired": (ExperienceCommitState.ERROR, ExperienceErrorState.EXPIRED),
}

# import 期断言：投影映射与源词表严格对齐（缺项/多项 fail-fast，D-05 A-02 纪律）。
from app.core.action_command import ACTION_ERROR_CODES, TERMINAL_REASON_VOCABULARY  # noqa: E402

assert set(_ACTION_ERROR_CODE_TO_ERROR_STATE) == set(ACTION_ERROR_CODES.values()) - {
    PROJECTION_REFUSED_ERROR_CODE
}, "error_state mapping must be 1:1 with ACTION_ERROR_CODES minus the refused code"
assert set(_TERMINAL_REASON_TO_COMMIT) <= TERMINAL_REASON_VOCABULARY
assert TERMINAL_REASON_VOCABULARY - set(_TERMINAL_REASON_TO_COMMIT) == {
    "user_cancelled",
    "user_rejected",
}, "only user_cancelled/user_rejected may map to skip (no event)"

_COPY_KEY_MAX = 140
_SUBJECT_ID_MAX = 128
_ASSET_REF_MAX = 200


# ---------------------------------------------------------------------------
# 投影异常（fail-loud 面）
# ---------------------------------------------------------------------------


class ExperienceProjectionRefused(RuntimeError):
    """权威回执携带不可投影语义（如 ACTION_INVALID_COMMAND）时的 fail-loud 拒绝。

    不是降级：调用方必须告警并检查上游为何产出了带该错误码的权威回执——
    静默映射进 error_state 会伪造呈现语义（契约 §6 R1-C3 投影器断言）。
    """


class ExperienceEventValidationError(ValueError):
    """事件结构校验失败（E1/E2/E4/封闭词表任一被破坏）。"""


# ---------------------------------------------------------------------------
# 幂等键（内容寻址；重放安全的身份派生）
# ---------------------------------------------------------------------------


def derive_dedupe_key(*, receipt_ref: str | None, kind: str, version_token: str) -> str:
    """``dedupe_key = sha256(receipt_ref + kind + subject.version_token)``（契约公式冻结）。

    receipt_ref 为 None 时按空串参与拼接（仅 receipt_ref 可空 kind 合法路径）。
    """
    seed = f"{receipt_ref or ''}{str(kind)}{str(version_token)}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def derive_experience_event_id(dedupe_key: str) -> str:
    """确定性事件 id（``eev_<sha256[:32]>``）：同 dedupe_key 恒同 id。

    时间不进派生——丢事件后按权威回执重放，任意时点重算恒得同 id，
    消费方按 event_id 去重即实现「同事件重播不重复触觉/音效」（F03 键位）。
    """
    seed = json.dumps(
        {"schema": EXPERIENCE_EVENT_SCHEMA_VERSION, "dedupe_key": str(dedupe_key)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return "eev_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# 终态/错误码 → commit 投影（全函数；契约 §6 表）
# ---------------------------------------------------------------------------


def project_terminal_reason(terminal_reason: str) -> tuple[ExperienceCommitState, ExperienceErrorState | None] | None:
    """``TerminalReason`` → ``(commit_state, error_state)`` 全函数。

    - ``committed`` → ``(committed, None)``；``expired`` → ``(error, expired)``；
    - ``user_cancelled`` / ``user_rejected`` → ``None``（**不产生事件**：投影器
      跳过，调用方记 skip 计数）；
    - 词表外值 → :class:`ExperienceProjectionRefused`（fail-loud：权威回执出现
      未登记终态属上游漂移，不得静默投影）。
    """
    value = str(terminal_reason or "")
    mapped = _TERMINAL_REASON_TO_COMMIT.get(value)
    if mapped is not None:
        return mapped
    if value in TERMINAL_REASON_VOCABULARY:
        return None
    raise ExperienceProjectionRefused(f"terminal_reason {terminal_reason!r} is outside the X-03 vocabulary")


def project_error_state(error_code: str) -> ExperienceErrorState:
    """``ACTION_ERROR_CODES`` 五值 → ``error_state``（1:1，不造第二词表）。

    ``ACTION_INVALID_COMMAND`` → :class:`ExperienceProjectionRefused`（契约 §6
    投影器断言：该码不可能出现在权威回执上；出现即上游漂移，fail-loud）。
    词表外码 → 同样 fail-loud。
    """
    value = str(error_code or "")
    if value == PROJECTION_REFUSED_ERROR_CODE:
        raise ExperienceProjectionRefused(
            "ACTION_INVALID_COMMAND never produces an authoritative receipt; "
            "refusing to project it into experience_event error_state (contract §6 R1-C3)"
        )
    mapped = _ACTION_ERROR_CODE_TO_ERROR_STATE.get(value)
    if mapped is None:
        raise ExperienceProjectionRefused(f"error_code {error_code!r} is outside the ACTION_ERROR_CODES vocabulary")
    return mapped


def _receipt_ref_scheme(receipt_ref: str) -> str:
    return receipt_ref.split("://", 1)[0] if "://" in receipt_ref else ""


# ---------------------------------------------------------------------------
# 冻结结构
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperienceSubject:
    """``subject``：事件锚定的对象 + 投影时点版本 token（X-03 绑定纪律）。"""

    type: str
    id: str
    version_token: str

    def __post_init__(self) -> None:
        if self.type not in SUBJECT_TYPE_VOCABULARY:
            raise ExperienceEventValidationError(f"subject.type {self.type!r} outside closed vocabulary")
        subject_id = str(self.id or "").strip()
        if not subject_id or len(subject_id) > _SUBJECT_ID_MAX:
            raise ExperienceEventValidationError("subject.id must be a non-empty string (<=128)")
        token = str(self.version_token or "").strip()
        if not token:
            # version_token 缺失不得以 ""/0 冒充（对齐回执 input_versions 纪律）：
            # 投影时点必须给出可验证的版本位；确实无版本的权威由服务层显式传
            # 约定常量并在 detail 侧可追溯。
            raise ExperienceEventValidationError("subject.version_token must be a non-empty string")
        object.__setattr__(self, "id", subject_id)
        object.__setattr__(self, "version_token", token)

    def to_dict(self) -> dict[str, str]:
        return {"type": self.type, "id": self.id, "version_token": self.version_token}


@dataclass(frozen=True)
class ExperiencePresentation:
    """``presentation``：模态 + 冻结文案表键（非模型自由文本）。

    ``copy_key`` 的键→文案冻结表 owner = V4-F03 实现卡（契约 §3 R1-C5）；
    本模块只冻结键纪律（非空、``<域>.<名>`` 两段式）。``asset_ref`` 仅指向
    已过审 token 集。
    """

    modalities: tuple[str, ...]
    copy_key: str
    asset_ref: str | None = None

    def __post_init__(self) -> None:
        mods = tuple(str(m) for m in self.modalities)
        if len(set(mods)) != len(mods):
            raise ExperienceEventValidationError("presentation.modalities must not contain duplicates")
        for mod in mods:
            if mod not in PRESENTATION_MODALITY_VOCABULARY:
                raise ExperienceEventValidationError(f"presentation.modality {mod!r} outside closed vocabulary")
        copy_key = str(self.copy_key or "").strip()
        parts = copy_key.split(".")
        if not copy_key or len(copy_key) > _COPY_KEY_MAX or len(parts) != 2 or not all(parts):
            raise ExperienceEventValidationError(
                "presentation.copy_key must be a two-part '<domain>.<name>' key from the frozen copy table"
            )
        object.__setattr__(self, "modalities", mods)
        object.__setattr__(self, "copy_key", copy_key)
        asset = self.asset_ref
        if asset is not None:
            asset = str(asset).strip() or None
            if asset is not None and len(asset) > _ASSET_REF_MAX:
                raise ExperienceEventValidationError("presentation.asset_ref too long (<=200)")
            object.__setattr__(self, "asset_ref", asset)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "modalities": list(self.modalities),
            "copy_key": self.copy_key,
        }
        if self.asset_ref is not None:
            payload["asset_ref"] = self.asset_ref
        return payload


@dataclass(frozen=True)
class ExperienceEvent:
    """``experience_event.v1`` 呈现回执（封闭结构；I1：无任何权限语义字段）。

    用 :meth:`ExperienceEvent.project` 构造（构造期强制 E1/E2/E4 + 封闭词表）。
    """

    schema_version: str
    event_id: str
    kind: str
    receipt_ref: str | None
    commit_state: str
    error_state: str | None
    subject: ExperienceSubject
    presentation: ExperiencePresentation
    dedupe_key: str
    issued_at: str
    expires_at: str | None

    @classmethod
    def project(
        cls,
        *,
        kind: str,
        commit_state: str,
        subject: ExperienceSubject,
        presentation: ExperiencePresentation,
        receipt_ref: str | None = None,
        error_state: str | None = None,
        issued_at: datetime,
        expires_at: datetime | None = None,
    ) -> ExperienceEvent:
        """投影构造：校验全部结构不变量后返回冻结事件（确定性，无模型参与）。"""
        if kind not in EXPERIENCE_EVENT_KINDS:
            raise ExperienceEventValidationError(f"kind {kind!r} outside closed vocabulary")
        if commit_state not in COMMIT_STATE_VOCABULARY:
            raise ExperienceEventValidationError(f"commit_state {commit_state!r} outside closed vocabulary")
        if error_state is not None and error_state not in ERROR_STATE_VOCABULARY:
            raise ExperienceEventValidationError(f"error_state {error_state!r} outside closed vocabulary")

        ref: str | None = None
        if receipt_ref is not None:
            ref = str(receipt_ref).strip() or None
        if ref is not None and _receipt_ref_scheme(ref) not in EXPERIENCE_RECEIPT_REF_SCHEMES:
            # E4/I3：伪造/词表外 ref scheme 拒绝（不降级为通用事件）。
            raise ExperienceEventValidationError(
                f"receipt_ref scheme {(_receipt_ref_scheme(ref) or '<missing>')!r} outside EXPERIENCE_RECEIPT_REF_SCHEMES"
            )
        if kind in RECEIPT_REF_REQUIRED_KINDS and ref is None:
            # I2：receipt 必选 kind 无权威回执 → 构造期即拒绝（服务层还须查证
            # 回执真实存在，双门）。
            raise ExperienceEventValidationError(f"kind={kind} requires receipt_ref (invariant I2/E1)")
        if kind == ExperienceEventKind.STATE_CONFIRMED.value and commit_state != ExperienceCommitState.COMMITTED.value:
            raise ExperienceEventValidationError("invariant E1: kind=state_confirmed requires commit_state=committed")
        if commit_state == ExperienceCommitState.ERROR.value:
            if error_state is None:
                raise ExperienceEventValidationError("invariant E2: commit_state=error requires error_state")
            if kind == ExperienceEventKind.STATE_CONFIRMED.value:
                raise ExperienceEventValidationError(
                    "invariant E1: kind=state_confirmed can never carry error_state (five error states never mix "
                    "into committed presentation; failure uses kind=terminal_failed)"
                )
        elif error_state is not None:
            raise ExperienceEventValidationError("invariant E2: error_state requires commit_state=error")

        dedupe_key = derive_dedupe_key(receipt_ref=ref, kind=kind, version_token=subject.version_token)
        return cls(
            schema_version=EXPERIENCE_EVENT_SCHEMA_VERSION,
            event_id=derive_experience_event_id(dedupe_key),
            kind=kind,
            receipt_ref=ref,
            commit_state=commit_state,
            error_state=error_state,
            subject=subject,
            presentation=presentation,
            dedupe_key=dedupe_key,
            issued_at=issued_at.isoformat(),
            expires_at=expires_at.isoformat() if expires_at is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """封闭键集序列化（键集冻结 = E3/I1 的结构面：无任何权限字段可容身）。"""
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "kind": self.kind,
            "receipt_ref": self.receipt_ref,
            "commit_state": self.commit_state,
            "error_state": self.error_state,
            "subject": self.subject.to_dict(),
            "presentation": self.presentation.to_dict(),
            "dedupe_key": self.dedupe_key,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }


__all__ = [
    "EXPERIENCE_EVENT_SCHEMA_VERSION",
    "EXPERIENCE_EVENT_KINDS",
    "COMMIT_STATE_VOCABULARY",
    "ERROR_STATE_VOCABULARY",
    "SUBJECT_TYPE_VOCABULARY",
    "PRESENTATION_MODALITY_VOCABULARY",
    "EXPERIENCE_RECEIPT_REF_SCHEMES",
    "RECEIPT_REF_REQUIRED_KINDS",
    "SUCCESS_PRESENTATION_KINDS",
    "PROJECTION_REFUSED_ERROR_CODE",
    "ExperienceCommitState",
    "ExperienceErrorState",
    "ExperienceEvent",
    "ExperienceEventKind",
    "ExperienceEventValidationError",
    "ExperiencePresentation",
    "ExperienceProjectionRefused",
    "ExperienceSubject",
    "ExperienceSubjectType",
    "PresentationModality",
    "derive_dedupe_key",
    "derive_experience_event_id",
    "project_error_state",
    "project_terminal_reason",
]
