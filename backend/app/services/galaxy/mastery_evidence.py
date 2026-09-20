"""Evidence-aware mastery model for Galaxy (G-01, V3).

Replaces "time = mastery": node brightness now represents *evidenced growth*.

Core properties (acceptance contract):
1. Same 30 minutes with different outcomes no longer produce the same mastery.
2. The formula is transparent: every fusion step exposes prior / observation /
   kalman_gain / posterior, so any mastery value can be explained and tested.
3. No evidence -> no mastery: pure time-on-task is capped at
   ``LEGACY_TIME_MASTERY_CAP`` and can never reach "mastered" on its own.
4. Self-report is a separate channel: it is recorded but never fused into the
   mastery posterior, so an identical self-reported score is never equivalent
   to a quiz score.
5. Legacy data (pre-evidence mastery values) is preserved but flagged as
   ``legacy_estimate``; the flag clears once real evidence exists.

The fusion math reuses the M-chain evidence engine pattern
(``app/services/evidence/belief_state.py``): a 1D Kalman update where
confidence maps to observation variance and the Kalman gain decides how far
each observation moves the posterior. This module is a pure-function port onto
the 0-100 mastery scale with *no* DB/Redis dependency, so the whole model is
unit-testable in isolation. Persistence adapters live in
``app/services/galaxy/stats_service.py`` (mastery_audit_log rows).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ---------------------------------------------------------------------------
# Evidence vocabulary
# ---------------------------------------------------------------------------


class MasteryEvidenceType(str, Enum):
    """Sources of mastery evidence. Weights follow GALAXY.md V3 contract:

    quiz / performance / artifact / review / self-report are tracked
    separately — self-report is NEVER mixed with quiz evidence.
    """

    QUIZ = "quiz"  # 测验/考试成绩（高权重、低不确定）
    TASK_OUTCOME = "task_outcome"  # 任务完成质量（中权重）
    CHAT_SIGNAL = "chat_signal"  # 对话中的掌握信号（中低权重、高不确定）
    MATERIAL_REF = "material_ref"  # 材料引用（低权重）
    SELF_REPORT = "self_report"  # 自评（单独通道，不参与融合）
    TIME_ON_TASK = "time_on_task"  # 纯学习时长（0 掌握权重，仅活动痕迹）


#: Confidence scaling per evidence type. 0 means "does not move the posterior".
EVIDENCE_WEIGHTS: dict[MasteryEvidenceType, float] = {
    MasteryEvidenceType.QUIZ: 1.0,
    MasteryEvidenceType.TASK_OUTCOME: 0.6,
    MasteryEvidenceType.CHAT_SIGNAL: 0.35,
    MasteryEvidenceType.MATERIAL_REF: 0.2,
    MasteryEvidenceType.SELF_REPORT: 0.0,  # separate channel, excluded from fusion
    MasteryEvidenceType.TIME_ON_TASK: 0.0,  # activity trace only
}

#: Minimum observation variance per evidence type (uncertainty floor). Mirrors
#: the M-chain heuristic floors: weaker sources can never claim precision.
EVIDENCE_UNCERTAINTY_FLOORS: dict[MasteryEvidenceType, float] = {
    MasteryEvidenceType.QUIZ: 0.01,
    MasteryEvidenceType.TASK_OUTCOME: 0.04,
    MasteryEvidenceType.CHAT_SIGNAL: 0.09,
    MasteryEvidenceType.MATERIAL_REF: 0.12,
    MasteryEvidenceType.SELF_REPORT: 0.16,
    MasteryEvidenceType.TIME_ON_TASK: 0.25,
}

#: Types that constitute *real* evidence for the legacy-flag decision.
REAL_EVIDENCE_TYPES: frozenset[MasteryEvidenceType] = frozenset(
    {
        MasteryEvidenceType.QUIZ,
        MasteryEvidenceType.TASK_OUTCOME,
        MasteryEvidenceType.CHAT_SIGNAL,
        MasteryEvidenceType.MATERIAL_REF,
    }
)

# ---------------------------------------------------------------------------
# Fusion constants (transparent, testable parameters)
# ---------------------------------------------------------------------------

#: Latent-space bounds, same as M-chain BeliefVariable.
MIN_VARIANCE = 0.01
MAX_VARIANCE = 0.25
#: A node with no evidence starts at maximum uncertainty (variance 0.25).
LEGACY_PRIOR_VARIANCE = MAX_VARIANCE

#: Pure time-on-task can push mastery up to this cap, never beyond.
#: 40 sits below the "mastered" threshold (80) and above collapse (10):
#: time proves exposure, not competence.
LEGACY_TIME_MASTERY_CAP = 40.0

#: Exponential decay parameters (applied between evidence events on replay).
#: Retention = exp(-ln(2) * days / half_life), floored at DECAY_FLOOR.
EVIDENCE_HALF_LIFE_DAYS = 14.0
DECAY_FLOOR = 5.0
#: Mastery-dependent stability: high mastery decays slower (1x..3x half-life),
#: consistent with DecayService stability semantics.
DECAY_STABILITY_FACTOR = 2.0

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvidenceObservation:
    """One observed piece of mastery evidence.

    value: mastery-equivalent observation on the 0-100 scale
    confidence: 0-1 extractor/source confidence (weighted by evidence type)
    """

    evidence_type: MasteryEvidenceType
    value: float
    confidence: float = 0.8
    observed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.value) <= 100.0:
            raise ValueError(f"evidence value must be within [0, 100], got {self.value}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(f"evidence confidence must be within [0, 1], got {self.confidence}")


@dataclass
class FusionStep:
    """Transparent trace of one Bayesian update (explainability contract)."""

    evidence_type: str
    prior_mean: float
    prior_variance: float
    observed_value: float
    observation_variance: float
    kalman_gain: float
    posterior_mean: float
    posterior_variance: float


@dataclass
class MasteryBelief:
    """Fused mastery posterior on the 0-100 scale."""

    mean: float
    variance: float = MAX_VARIANCE
    evidence_count: int = 0
    self_report_count: int = 0
    breakdown: dict[str, int] = field(default_factory=dict)
    trace: list[FusionStep] = field(default_factory=list)

    @property
    def is_legacy_estimate(self) -> bool:
        """True when no *real* evidence (self-report/time excluded) exists."""
        return not any(k in {t.value for t in REAL_EVIDENCE_TYPES} for k in self.breakdown)


@dataclass(frozen=True)
class EvidenceHistoryEntry:
    """One persisted evidence row (from mastery_audit_log), ready to replay."""

    evidence_type: MasteryEvidenceType
    value: float
    confidence: float
    observed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Transparent fusion (1D Kalman, per M-chain belief_state.update_from_evidence)
# ---------------------------------------------------------------------------


def _observation_variance(observation: EvidenceObservation) -> float:
    """Map (type weight x confidence) to observation variance.

    High weight x high confidence -> low variance -> large Kalman gain.
    Each type keeps an uncertainty floor so weak sources can never dominate.
    """
    weight = EVIDENCE_WEIGHTS[observation.evidence_type]
    floor = EVIDENCE_UNCERTAINTY_FLOORS[observation.evidence_type]
    effective_confidence = max(0.01, min(0.99, observation.confidence * weight)) if weight > 0 else 0.0
    return max(floor, min(MAX_VARIANCE, (1.0 - effective_confidence) ** 2))


def fuse_mastery(
    prior_mean: float,
    prior_variance: float,
    observations: list[EvidenceObservation],
) -> MasteryBelief:
    """Fuse observations into the mastery posterior with a transparent trace.

    Sequential 1D Kalman updates (same algebra as the M-chain FusionEngine):
        kalman_gain   = prior_variance / (prior_variance + obs_variance)
        posterior     = prior + kalman_gain * (observation - prior)
        posterior_var = (1 - kalman_gain) * prior_variance
    """
    belief = MasteryBelief(
        mean=_clamp100(prior_mean),
        variance=max(MIN_VARIANCE, min(MAX_VARIANCE, prior_variance)),
    )
    for observation in sorted(observations, key=lambda o: o.observed_at or datetime.min):
        if observation.evidence_type is MasteryEvidenceType.SELF_REPORT:
            # Separate channel: recorded for observability, never fused.
            belief.self_report_count += 1
            belief.breakdown[observation.evidence_type.value] = (
                belief.breakdown.get(observation.evidence_type.value, 0) + 1
            )
            continue
        if observation.evidence_type is MasteryEvidenceType.TIME_ON_TASK:
            # Zero mastery weight: pure exposure never moves the posterior.
            belief.breakdown[observation.evidence_type.value] = (
                belief.breakdown.get(observation.evidence_type.value, 0) + 1
            )
            continue

        prior_mean_latent = belief.mean / 100.0
        observed_latent = _clamp100(observation.value) / 100.0
        obs_variance = _observation_variance(observation)
        prior_variance = max(MIN_VARIANCE, min(MAX_VARIANCE, belief.variance))
        total_variance = prior_variance + obs_variance
        kalman_gain = prior_variance / total_variance if total_variance > 0 else 0.0

        posterior_latent = prior_mean_latent + kalman_gain * (observed_latent - prior_mean_latent)
        posterior_variance = max(MIN_VARIANCE, min(MAX_VARIANCE, (1.0 - kalman_gain) * prior_variance))

        belief.mean = _clamp100(posterior_latent * 100.0)
        belief.variance = posterior_variance
        belief.evidence_count += 1
        belief.breakdown[observation.evidence_type.value] = (
            belief.breakdown.get(observation.evidence_type.value, 0) + 1
        )
        belief.trace.append(
            FusionStep(
                evidence_type=observation.evidence_type.value,
                prior_mean=round(prior_mean_latent * 100.0, 4),
                prior_variance=round(prior_variance, 6),
                observed_value=_clamp100(observation.value),
                observation_variance=round(obs_variance, 6),
                kalman_gain=round(kalman_gain, 6),
                posterior_mean=round(belief.mean, 4),
                posterior_variance=round(posterior_variance, 6),
            )
        )
    return belief


# ---------------------------------------------------------------------------
# Time decay (testable parameters)
# ---------------------------------------------------------------------------


def apply_evidence_decay(
    mean: float,
    variance: float,
    days_elapsed: float,
    *,
    half_life_days: float = EVIDENCE_HALF_LIFE_DAYS,
) -> tuple[float, float]:
    """Decay mastery toward DECAY_FLOOR; uncertainty grows with staleness.

    Retention = exp(-ln2 * days / half_life), half-life stretched by mastery
    (stable knowledge fades slower). Returns (decayed_mean, decayed_variance).
    """
    if days_elapsed <= 0:
        return mean, variance
    stability = 1.0 + (max(0.0, min(100.0, mean)) / 100.0) * DECAY_STABILITY_FACTOR
    effective_half_life = max(0.1, half_life_days * stability)
    retention = math.exp(-math.log(2.0) * days_elapsed / effective_half_life)
    decayed = DECAY_FLOOR + (mean - DECAY_FLOOR) * retention
    # Stale evidence loses precision: variance relaxes toward max uncertainty.
    decay_fraction = 1.0 - retention
    decayed_variance = min(MAX_VARIANCE, variance + (MAX_VARIANCE - variance) * decay_fraction)
    return max(DECAY_FLOOR, decayed), decayed_variance


# ---------------------------------------------------------------------------
# Replay: deterministic fused state from persisted evidence history
# ---------------------------------------------------------------------------


def recompute_evidence_state(
    legacy_mastery: float,
    history: list[EvidenceHistoryEntry],
) -> MasteryBelief:
    """Replay the evidence ledger: fuse each *real* evidence entry in time
    order, applying decay over the gap between consecutive events. Starts from
    the legacy value at max uncertainty. Deterministic, so tests pin numbers.

    Terminal decay (last event -> now) is intentionally NOT applied here: the
    stored mastery_score is maintained by DecayService (daily Ebbinghaus job),
    and replay must not double-count that time dimension.
    """
    belief = fuse_mastery(legacy_mastery, LEGACY_PRIOR_VARIANCE, [])  # empty prior belief

    real = sorted(
        (e for e in history if e.evidence_type in REAL_EVIDENCE_TYPES),
        key=lambda e: e.observed_at or datetime.min,
    )
    previous_at: datetime | None = None
    for entry in real:
        if previous_at is not None and entry.observed_at is not None:
            gap_days = max(0.0, (entry.observed_at - previous_at).total_seconds() / 86400.0)
            if gap_days > 0:
                mean, variance = apply_evidence_decay(belief.mean, belief.variance, gap_days)
                belief.mean, belief.variance = mean, variance
        step_belief = fuse_mastery(belief.mean, belief.variance, [entry])
        belief.mean = step_belief.mean
        belief.variance = step_belief.variance
        belief.evidence_count += step_belief.evidence_count
        belief.trace.extend(step_belief.trace)
        for key, count in step_belief.breakdown.items():
            belief.breakdown[key] = belief.breakdown.get(key, 0) + count
        if entry.observed_at is not None:
            previous_at = entry.observed_at

    # Non-real channels still count toward observability (self-report channel).
    for entry in history:
        if entry.evidence_type not in REAL_EVIDENCE_TYPES:
            belief.breakdown[entry.evidence_type.value] = belief.breakdown.get(entry.evidence_type.value, 0) + 1
            if entry.evidence_type is MasteryEvidenceType.SELF_REPORT:
                belief.self_report_count += 1
    return belief


def _clamp100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


# ---------------------------------------------------------------------------
# Legacy time-only delta (bounded)
# ---------------------------------------------------------------------------


def legacy_time_delta(study_minutes: int, importance_level: int, base_points: float = 5.0) -> float:
    """The legacy formula (kept for compatibility, now explicitly bounded).

    delta = base * min(minutes/30, 2) * (1 + (importance-1)*0.1)
    Callers must additionally cap accumulation at LEGACY_TIME_MASTERY_CAP.
    """
    time_factor = min(study_minutes / 30.0, 2.0)
    difficulty_factor = 1 + (importance_level - 1) * 0.1
    return base_points * time_factor * difficulty_factor


def capped_legacy_mastery(current_mastery: float, delta: float) -> float:
    """Apply a time-only delta with the legacy cap: exposure proves presence,
    not competence. Once mastery exceeds LEGACY_TIME_MASTERY_CAP, time alone
    adds nothing (never lowers it either).
    """
    if current_mastery >= LEGACY_TIME_MASTERY_CAP:
        return current_mastery
    return min(current_mastery + max(0.0, delta), LEGACY_TIME_MASTERY_CAP)


# ---------------------------------------------------------------------------
# Audit-log persistence adapters (reason/request_id codec)
# ---------------------------------------------------------------------------

EVIDENCE_REASON_PREFIX = "evidence:"

#: Existing update_node_mastery reasons that already represent *quiz-grade*
#: evidence (error-book and exam sprint flows write these today).
QUIZ_EVIDENCE_REASONS: frozenset[str] = frozenset(
    {
        "exam_sprint_diagnostic",
        "post_exam_review_weak_node",
        "error_diagnosis",
        "error_review",
        "correct_answer",
    }
)

#: G-01 R-1 收口（显式标记）：客户端自报绝对值路径（``/sync/mastery`` 与
#: manual update REST 入口）写入的 reason 词表。这些 reason **不携带任何
#: 掌握证据**——客户端塞的绝对值只是「设备端状态上云」，按 R-1 处置契约
#: 永不摘 legacy 旗、永不进证据账本；首条真实证据（quiz 级）几乎完全覆盖
#: 被污染先验（quiz K≈0.96）。classify_audit_reason 对它们显式返回 None，
#: 不依赖 fall-through；未被收编的任意客户端字符串同样 fail-closed 判 None。
NON_EVIDENCE_REASONS: frozenset[str] = frozenset(
    {
        "offline_sync",  # /sync/mastery 移动端离线同步回传
        "manual_update",  # /nodes/{id}/mastery 手动改分入口
        "focus_session",  # 专注会话（纯时长，非证据）
        "task_complete",  # 任务完成（时长型，非掌握证据）
    }
)


def encode_evidence_reason(evidence_type: MasteryEvidenceType) -> str:
    """reason column value for a new evidence audit row (<=100 chars)."""
    return f"{EVIDENCE_REASON_PREFIX}{evidence_type.value}"


def encode_observation_payload(value: float, confidence: float) -> str:
    """request_id column payload encoding the observation (<=100 chars)."""
    return f"obs={round(float(value), 2)};conf={round(float(confidence), 2)}"


def parse_observation_payload(payload: str | None) -> tuple[float, float] | None:
    """Inverse of encode_observation_payload; returns (value, confidence)."""
    if not payload:
        return None
    parts: dict[str, str] = {}
    for chunk in str(payload).split(";"):
        if "=" in chunk:
            key, _, raw = chunk.partition("=")
            parts[key.strip()] = raw.strip()
    try:
        return float(parts["obs"]), float(parts["conf"])
    except (KeyError, ValueError):
        return None


def classify_audit_reason(reason: str | None) -> MasteryEvidenceType | None:
    """Map a mastery_audit_log.reason to its evidence type.

    Returns None for reasons that carry no mastery evidence (client
    self-report sync, focus minutes, manual nudges...). Those never clear the
    legacy flag. ``NON_EVIDENCE_REASONS``（客户端绝对值路径）显式判 None
    （G-01 R-1 收口），其余未知字符串走同一 fall-through，方向一致。
    """
    reason = (reason or "").strip()
    if reason in NON_EVIDENCE_REASONS:
        return None
    if reason.startswith(EVIDENCE_REASON_PREFIX):
        raw = reason[len(EVIDENCE_REASON_PREFIX):]
        try:
            return MasteryEvidenceType(raw)
        except ValueError:
            return None
    if reason in QUIZ_EVIDENCE_REASONS:
        return MasteryEvidenceType.QUIZ
    return None


def decay_days_between(last_event: datetime, now: datetime) -> float:
    """Day gap used by replay decay; clamped at >= 0."""
    return max(0.0, (now - last_event).total_seconds() / 86400.0)


__all__ = [
    "DECAY_FLOOR",
    "EVIDENCE_HALF_LIFE_DAYS",
    "EVIDENCE_WEIGHTS",
    "EVIDENCE_UNCERTAINTY_FLOORS",
    "LEGACY_PRIOR_VARIANCE",
    "LEGACY_TIME_MASTERY_CAP",
    "MasteryBelief",
    "MasteryEvidenceType",
    "EvidenceHistoryEntry",
    "EvidenceObservation",
    "FusionStep",
    "NON_EVIDENCE_REASONS",
    "REAL_EVIDENCE_TYPES",
    "apply_evidence_decay",
    "capped_legacy_mastery",
    "classify_audit_reason",
    "encode_evidence_reason",
    "encode_observation_payload",
    "fuse_mastery",
    "legacy_time_delta",
    "parse_observation_payload",
    "recompute_evidence_state",
]
