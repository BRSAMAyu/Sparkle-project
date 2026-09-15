from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value)
    raise ValueError(f"Invalid datetime payload: {value!r}")


@dataclass(frozen=True)
class AttractorState:
    dim: str
    baseline: float
    variability: float
    recovery_rate: float
    confidence: float
    updated_at: datetime

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AttractorState:
        return cls(
            dim=str(payload.get("dim") or ""),
            baseline=float(payload.get("baseline") or 0.0),
            variability=float(payload.get("variability") or 0.0),
            recovery_rate=float(payload.get("recovery_rate") or 0.0),
            confidence=float(payload.get("confidence") or 0.0),
            updated_at=_parse_datetime(payload.get("updated_at")),
        )


@dataclass(frozen=True)
class Deviation:
    dim: str
    current_value: float
    baseline: float
    z_score: float
    direction: str
    projected_3d: float
    confidence: float

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Deviation:
        return cls(
            dim=str(payload.get("dim") or ""),
            current_value=float(payload.get("current_value") or 0.0),
            baseline=float(payload.get("baseline") or 0.0),
            z_score=float(payload.get("z_score") or 0.0),
            direction=str(payload.get("direction") or "below"),
            projected_3d=float(payload.get("projected_3d") or 0.0),
            confidence=float(payload.get("confidence") or 0.0),
        )


@dataclass(frozen=True)
class ForesightHint:
    hint_id: str
    dim: str
    message: str
    z_score: float
    confidence: float
    generated_at: datetime
    template_id: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ForesightHint:
        return cls(
            hint_id=str(payload.get("hint_id") or ""),
            dim=str(payload.get("dim") or ""),
            message=str(payload.get("message") or ""),
            z_score=float(payload.get("z_score") or 0.0),
            confidence=float(payload.get("confidence") or 0.0),
            generated_at=_parse_datetime(payload.get("generated_at")),
            template_id=str(payload.get("template_id") or ""),
        )


@dataclass(frozen=True)
class ForesightSnapshot:
    existing_predictions: dict[str, Any]
    attractors: dict[str, AttractorState]
    deviations: tuple[Deviation, ...]
    hints: tuple[ForesightHint, ...]
    generated_at: datetime
    user_id: str
    version: str = "v1"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ForesightSnapshot:
        attractors = {
            str(dim): AttractorState.from_dict(state)
            for dim, state in dict(payload.get("attractors") or {}).items()
            if isinstance(state, dict)
        }
        deviations = tuple(
            Deviation.from_dict(item)
            for item in list(payload.get("deviations") or [])
            if isinstance(item, dict)
        )
        hints = tuple(
            ForesightHint.from_dict(item)
            for item in list(payload.get("hints") or [])
            if isinstance(item, dict)
        )
        return cls(
            existing_predictions=dict(payload.get("existing_predictions") or {}),
            attractors=attractors,
            deviations=deviations,
            hints=hints,
            generated_at=_parse_datetime(payload.get("generated_at")),
            user_id=str(payload.get("user_id") or ""),
            version=str(payload.get("version") or "v1"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "existing_predictions": self.existing_predictions,
            "attractors": {
                dim: {
                    "dim": state.dim,
                    "baseline": state.baseline,
                    "variability": state.variability,
                    "recovery_rate": state.recovery_rate,
                    "confidence": state.confidence,
                    "updated_at": state.updated_at.isoformat(),
                }
                for dim, state in self.attractors.items()
            },
            "deviations": [
                {
                    "dim": item.dim,
                    "current_value": item.current_value,
                    "baseline": item.baseline,
                    "z_score": item.z_score,
                    "direction": item.direction,
                    "projected_3d": item.projected_3d,
                    "confidence": item.confidence,
                }
                for item in self.deviations
            ],
            "hints": [
                {
                    "hint_id": item.hint_id,
                    "dim": item.dim,
                    "message": item.message,
                    "z_score": item.z_score,
                    "confidence": item.confidence,
                    "generated_at": item.generated_at.isoformat(),
                    "template_id": item.template_id,
                }
                for item in self.hints
            ],
            "generated_at": self.generated_at.isoformat(),
            "user_id": self.user_id,
            "version": self.version,
        }
