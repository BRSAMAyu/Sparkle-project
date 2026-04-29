"""
Core: execution / cognitive
Phase: clarify → plan → execute
Stage: Aurora Runtime v1 — User Communication Preferences

User-facing Aurora communication preferences stored in UserPreferencesCenter.explicit JSONB.
Four dimensions control how Aurora interacts: analysis depth, directness, explanation, pressure style.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preferences import UserPreferencesCenter

_VALID_VALUES: dict[str, set[str]] = {
    "aurora_analysis_depth": {"light", "deep"},
    "aurora_directness": {"direct", "guided"},
    "aurora_explanation_level": {"detailed", "brief"},
    "aurora_pressure_style": {"gentle", "motivating"},
}

_DEFAULTS: dict[str, str] = {
    "aurora_analysis_depth": "deep",
    "aurora_directness": "guided",
    "aurora_explanation_level": "detailed",
    "aurora_pressure_style": "motivating",
}

_PREF_KEYS = frozenset(_DEFAULTS)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AuroraUserPreferencesService:
    """Read/write Aurora communication preferences stored in UserPreferencesCenter.explicit."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, user_id: str | UUID) -> dict[str, str]:
        """Return all 4 Aurora preferences with defaults for unset values."""
        try:
            result = await self.db.execute(
                select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return dict(_DEFAULTS)
            explicit = row.explicit or {}
            return {
                key: explicit.get(key, _DEFAULTS[key])
                for key in _PREF_KEYS
            }
        except Exception:
            logger.warning("AuroraUserPreferences: get failed for user={}, returning defaults", user_id)
            return dict(_DEFAULTS)

    async def update(self, user_id: str | UUID, preferences: dict[str, str]) -> dict[str, str]:
        """Validate and persist Aurora preferences. Only recognized keys are stored."""
        cleaned: dict[str, str] = {}
        for key, value in preferences.items():
            if key not in _PREF_KEYS:
                continue
            valid_set = _VALID_VALUES.get(key, set())
            if valid_set and value not in valid_set:
                continue
            cleaned[key] = value

        if not cleaned:
            return await self.get(user_id)

        try:
            result = await self.db.execute(
                select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)
            )
            row = result.scalar_one_or_none()

            if row is None:
                row = UserPreferencesCenter(
                    user_id=user_id,
                    explicit={**dict(_DEFAULTS), **cleaned},
                    last_explicit_update=_utcnow(),
                )
                self.db.add(row)
            else:
                existing = dict(row.explicit or {})
                existing.update(cleaned)
                row.explicit = existing
                row.last_explicit_update = _utcnow()
                row.increment_version()

            await self.db.commit()
            logger.info("AuroraUserPreferences: updated user={} keys={}", user_id, list(cleaned))
        except Exception:
            await self.db.rollback()
            logger.warning("AuroraUserPreferences: update failed for user={}", user_id)
            return await self.get(user_id)

        return await self.get(user_id)

    @staticmethod
    def apply_to_response_directive(
        prefs: dict[str, str],
        *,
        tone: str | None = None,
        verbosity: str | None = None,
        pressure: str | None = None,
    ) -> dict[str, str]:
        """Compute directive modulation from preferences.

        Returns a dict with modulated tone, verbosity, and pressure hints.
        Does not mutate inputs — callers use the returned values.
        """
        result: dict[str, str] = {}
        analysis = prefs.get("aurora_analysis_depth", "deep")
        directness = prefs.get("aurora_directness", "guided")
        explanation = prefs.get("aurora_explanation_level", "detailed")
        pressure_style = prefs.get("aurora_pressure_style", "motivating")

        result["analysis_depth"] = analysis
        result["directness"] = directness

        # Modulate tone
        if tone:
            result["tone"] = tone

        # Verbosity modulation
        if explanation == "brief":
            result["verbosity"] = "concise"
        elif explanation == "detailed":
            result["verbosity"] = "supportive"
        if verbosity:
            result["verbosity"] = verbosity

        # Pressure modulation
        if pressure_style == "gentle":
            result["pressure"] = "low_pressure"
        elif pressure_style == "motivating":
            result["pressure"] = "moderate"
        if pressure:
            result["pressure"] = pressure

        # Directness affects intervention style
        if directness == "direct":
            result["intervention_style"] = "action_oriented"
        else:
            result["intervention_style"] = "reflective"

        return result
