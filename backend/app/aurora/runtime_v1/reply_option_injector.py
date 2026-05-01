"""
Core: execution
Phase: clarify→adapt
Stage: T3.3.1 Predicted Reply Option Injector — attaches predicted reply options
to chat response metadata so Flutter can render them below each AI reply.

Follows the established metadata injection pattern (ux_envelope, spine_receipt).
"""
from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.aurora.predicted_reply_engine import PredictedReplyOptionEngine
from app.signals.predicted_reply_options import SpineReplyOptionEngine
from app.signals.types import ActionableSignal


class ReplyOptionInjector:
    """T3.3.1: Generates predicted reply options from live Aurora state and injects
    them into ChatResponse.metadata as a JSON-serialized payload.

    Two generation paths:
    1. Aurora engine — for general chat, driven by band_status + tensions
    2. Spine engine — for signal-driven questions (template-based)
    """

    def __init__(self):
        self._aurora_engine = PredictedReplyOptionEngine()
        self._spine_engine = SpineReplyOptionEngine()

    def generate(
        self,
        *,
        band_status: str = "sensing",
        facets: list[dict[str, Any]] | None = None,
        tensions: list[dict[str, Any]] | None = None,
        energy_level: str = "L1",
        wake_eligibility: dict[str, Any] | None = None,
        user_model_meta: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate predicted reply option groups from Aurora state.

        Returns a list of serialized PredictedReplyGroup dicts suitable for
        JSON injection into ChatResponse.metadata.
        """
        try:
            groups = self._aurora_engine.generate(
                band_status=band_status,
                facets=facets or [],
                informational_tensions=tensions or [],
                energy_level=energy_level,
                wake_eligibility=wake_eligibility or {},
                user_model_meta=user_model_meta or {},
            )
            return groups
        except Exception:
            logger.debug("ReplyOptionInjector: generation failed", exc_info=True)
            return []

    def generate_from_signal(self, signal: ActionableSignal) -> dict[str, Any] | None:
        """Generate a predicted reply question from a Spine signal."""
        try:
            question = self._spine_engine.generate_options(signal)
            if question is None:
                return None
            return question.to_dict()
        except Exception:
            logger.debug("ReplyOptionInjector: signal generation failed", exc_info=True)
            return None

    def inject_into_metadata(
        self,
        metadata: dict[str, Any],
        groups: list[dict[str, Any]],
        band_status: str = "sensing",
    ) -> None:
        """Inject predicted reply options into the response metadata dict.

        Serialized as a JSON string under the key 'predicted_reply_options'.
        """
        payload = {
            "groups": groups,
            "band_status": band_status,
            "version": "1.0",
        }
        metadata["predicted_reply_options"] = json.dumps(payload, ensure_ascii=False)
        logger.debug(
            "ReplyOptionInjector: injected {} groups for band_status={}",
            len(groups), band_status,
        )
