from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.core.user_insight_state import UserInsightState


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat()


class M1SourceModule(BaseModel):
    module_name: str = "M1"
    source_of_truth: str = "L0"
    source_families: list[str] = Field(default_factory=list)
    source_family_counts: dict[str, int] = Field(default_factory=dict)
    signal_count: int = 0
    coverage_registry: list[dict[str, Any]] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)


class M2CanonicalModule(BaseModel):
    module_name: str = "M2"
    canonical_state: UserInsightState = Field(default_factory=UserInsightState)
    recent_pain_point_count: int = 0
    recent_win_count: int = 0
    active_bottleneck_count: int = 0


class M3InferenceModule(BaseModel):
    module_name: str = "M3"
    multi_span_analysis: dict[str, Any] = Field(default_factory=dict)
    prediction_summaries: dict[str, Any] = Field(default_factory=dict)
    readiness: dict[str, Any] = Field(default_factory=dict)


class M4CalibrationModule(BaseModel):
    module_name: str = "M4"
    calibration_summary: dict[str, Any] = Field(default_factory=dict)
    confidence_metadata: dict[str, float] = Field(default_factory=dict)
    freshness_metadata: dict[str, str] = Field(default_factory=dict)
    uncertainty_markers: list[dict[str, Any]] = Field(default_factory=list)


class M5TransparencyModule(BaseModel):
    module_name: str = "M5"
    transparency_payload: dict[str, Any] = Field(default_factory=dict)
    available_controls: list[str] = Field(default_factory=list)


class UserProjectionContract(BaseModel):
    contract_version: str = "ws-m1c.2026-04-19.v1"
    generated_at: str = Field(default_factory=_utcnow_iso)
    write_lane: str = "L1"
    cache_policy: str = "projection_cache_only"

    m1_sources: M1SourceModule = Field(default_factory=M1SourceModule)
    m2_canonical: M2CanonicalModule = Field(default_factory=M2CanonicalModule)
    m3_inference: M3InferenceModule = Field(default_factory=M3InferenceModule)
    m4_calibration: M4CalibrationModule = Field(default_factory=M4CalibrationModule)
    m5_transparency: M5TransparencyModule = Field(default_factory=M5TransparencyModule)

    @property
    def canonical_state(self) -> UserInsightState:
        return self.m2_canonical.canonical_state

    @classmethod
    def from_compiled_state(
        cls,
        *,
        state: UserInsightState,
        merged_preferences: dict[str, Any] | None = None,
    ) -> UserProjectionContract:
        from app.services.user_insight_transparency_service import UserInsightTransparencyService

        merged_preferences = merged_preferences or {}
        signal_evidence = list(state.signal_evidence or [])
        source_families = sorted(
            {
                str(item.family).strip()
                for item in signal_evidence
                if str(getattr(item, "family", "")).strip()
            }
        )
        source_family_counts: dict[str, int] = {}
        for item in signal_evidence:
            family = str(getattr(item, "family", "")).strip()
            if family:
                source_family_counts[family] = source_family_counts.get(family, 0) + 1

        transparency_payload = UserInsightTransparencyService().build_payload(
            state=state,
            merged_preferences=merged_preferences,
            inferred_backups={},
        )
        available_controls = sorted(
            {
                str(control).strip()
                for claim in list(transparency_payload.get("claims") or [])
                if isinstance(claim, dict)
                for control in list(claim.get("controls") or [])
                if str(control).strip()
            }
        )
        registry = cls._build_m1_coverage_registry(
            state=state,
            source_family_counts=source_family_counts,
        )

        return cls(
            m1_sources=M1SourceModule(
                source_families=source_families,
                source_family_counts=source_family_counts,
                signal_count=len(signal_evidence),
                coverage_registry=registry,
                coverage_notes=[
                    "Canonical projection remains cache-only and does not mutate L0 raw evidence.",
                    "Source-family inventory is derived from signal_evidence families at compile time.",
                    "Coverage registry tracks thin Stage 6 domains without introducing a second source-of-truth.",
                ],
            ),
            m2_canonical=M2CanonicalModule(
                canonical_state=state,
                recent_pain_point_count=len(state.recent_pain_points or []),
                recent_win_count=len(state.recent_wins or []),
                active_bottleneck_count=len(state.active_bottlenecks or []),
            ),
            m3_inference=M3InferenceModule(
                multi_span_analysis=dict(state.multi_span_analysis or {}),
                prediction_summaries=dict(state.prediction_summaries or {}),
                readiness=dict(state.readiness or {}),
            ),
            m4_calibration=M4CalibrationModule(
                calibration_summary=dict(state.calibration_summary or {}),
                confidence_metadata=dict(state.confidence_metadata or {}),
                freshness_metadata=dict(state.freshness_metadata or {}),
                uncertainty_markers=[
                    dict(item)
                    for item in list(state.uncertainty_markers or [])
                    if isinstance(item, dict)
                ],
            ),
            m5_transparency=M5TransparencyModule(
                transparency_payload=transparency_payload,
                available_controls=available_controls,
            ),
        )

    @staticmethod
    def _build_m1_coverage_registry(
        *,
        state: UserInsightState,
        source_family_counts: dict[str, int],
    ) -> list[dict[str, Any]]:
        signal_ids = {
            str(item.signal_id).strip()
            for item in list(state.signal_evidence or [])
            if str(getattr(item, "signal_id", "")).strip()
        }

        def _entry(
            domain_id: str,
            *,
            required_signal_ids: set[str],
            auxiliary_count: int = 0,
            source_families: list[str] | None = None,
        ) -> dict[str, Any]:
            present_signals = sorted(signal_ids.intersection(required_signal_ids))
            evidence_count = len(present_signals) + auxiliary_count
            if evidence_count >= 2:
                status = "present"
                quality = "strong"
            elif evidence_count == 1:
                status = "partial"
                quality = "thin"
            else:
                status = "missing"
                quality = "missing"
            families = sorted(
                family
                for family in (source_families or [])
                if source_family_counts.get(family, 0) > 0
            )
            return {
                "domain_id": domain_id,
                "status": status,
                "quality": quality,
                "signal_ids": present_signals,
                "source_families": families,
                "evidence_count": evidence_count,
            }

        return [
            _entry(
                "motivation_patterns",
                required_signal_ids={
                    "motivation_type",
                    "achievement_motivation_response",
                    "achievement_reward_sensitivity",
                    "achievement_pace_style",
                },
                source_families=["motivation", "achievement"],
            ),
            _entry(
                "anti_patterns",
                required_signal_ids={"anti_patterns"},
                auxiliary_count=len(list((state.temporal_patterns or {}).get("anti_patterns") or [])),
                source_families=["cognitive"],
            ),
            _entry(
                "cognitive_tendencies",
                required_signal_ids={"cognitive_tendencies"},
                auxiliary_count=len(list((state.temporal_patterns or {}).get("cognitive_tendencies") or [])),
                source_families=["cognitive"],
            ),
        ]
