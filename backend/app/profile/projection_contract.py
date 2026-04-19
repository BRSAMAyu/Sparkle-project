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
    signal_count: int = 0
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
    contract_version: str = "ws-m1b.2026-04-19.v1"
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
    ) -> "UserProjectionContract":
        from app.services.user_insight_transparency_service import UserInsightTransparencyService

        merged_preferences = merged_preferences or {}
        source_families = sorted(
            {
                str(item.family).strip()
                for item in (state.signal_evidence or [])
                if str(getattr(item, "family", "")).strip()
            }
        )
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

        return cls(
            m1_sources=M1SourceModule(
                source_families=source_families,
                signal_count=len(state.signal_evidence or []),
                coverage_notes=[
                    "Canonical projection remains cache-only and does not mutate L0 raw evidence.",
                    "Source-family inventory is derived from signal_evidence families at compile time.",
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
