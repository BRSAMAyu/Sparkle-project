"""
Core: governance
Phase: act
Stage: Signal-to-Action Spine GOV-010 High-Impact Confirmation Framework

Ruling: Any directive that modifies persistent state, adjusts plans, or carries
high/critical risk MUST be confirmed by the user before execution. This framework
determines which directives require confirmation and manages the confirmation
lifecycle (request → user action → outcome).

No-action signal is noise; no-audit directive is hallucination.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

# Directive types that are inherently high-impact when paired with low confidence
_HIGH_IMPACT_TYPES = {"model_write", "plan_adjustment"}

# Risk levels that always trigger confirmation regardless of other factors
_HIGH_RISK_LEVELS = {"critical", "high"}

# Default timeout for confirmation requests (seconds)
_DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes


@dataclass
class ConfirmationRequest:
    """Structured confirmation request sent to the user."""

    request_id: str
    directive_id: str
    user_id: str
    reason: str
    options: list[dict[str, Any]]
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS


class HighImpactConfirmationFramework:
    """GOV-010: Determines high-impact directives and manages confirmation flow."""

    def __init__(self) -> None:
        # In-memory pending requests; production should use Redis with TTL
        self._pending: dict[str, ConfirmationRequest] = {}

    @staticmethod
    def is_high_impact(
        directive_type: str,
        risk_level: str,
        user_correction_count: int,
        claim_confidence: float,
    ) -> bool:
        """Determine whether a directive requires user confirmation.

        A directive is high-impact if ANY of the following hold:
        1. risk_level is "critical" or "high"
        2. directive_type is "model_write" or "plan_adjustment" AND claim_confidence < 0.8
        3. user_correction_count >= 2 (user has corrected the system twice recently)

        Args:
            directive_type: One of the 9 directive type strings.
            risk_level: "critical" | "high" | "medium" | "low".
            user_correction_count: Number of recent user corrections (rolling window).
            claim_confidence: Model confidence in the directive's claim [0.0, 1.0].

        Returns:
            True if the directive requires user confirmation before execution.
        """
        # Rule 1: absolute risk gate
        if risk_level in _HIGH_RISK_LEVELS:
            return True

        # Rule 2: high-impact type with insufficient confidence
        if directive_type in _HIGH_IMPACT_TYPES and claim_confidence < 0.8:
            return True

        # Rule 3: user has corrected the system multiple times recently
        if user_correction_count >= 2:
            return True

        return False

    def build_confirmation_request(
        self,
        user_id: str,
        directive: dict[str, Any],
        reason: str,
        timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
    ) -> ConfirmationRequest:
        """Build a ConfirmationRequest for user presentation.

        Args:
            user_id: The user who must confirm.
            directive: The original directive dict (must contain "directive_id").
            reason: Human-readable explanation of why confirmation is needed.
            timeout_seconds: Seconds before the request auto-expires.

        Returns:
            A ConfirmationRequest ready for delivery to the client.
        """
        request_id = f"confirm_{uuid.uuid4().hex[:12]}"
        directive_id = directive.get("directive_id", "unknown")

        options = [
            {"label": "confirm", "value": "confirmed"},
            {"label": "correct", "value": "corrected"},
            {"label": "reject", "value": "corrected"},
        ]

        req = ConfirmationRequest(
            request_id=request_id,
            directive_id=directive_id,
            user_id=user_id,
            reason=reason,
            options=options,
            timeout_seconds=timeout_seconds,
        )

        self._pending[request_id] = req
        logger.info(
            "GOV-010: confirmation request created id={} directive={} user={}",
            request_id, directive_id, user_id,
        )
        return req

    def process_confirmation(
        self,
        request_id: str,
        user_action: str,
    ) -> str:
        """Process the user's response to a confirmation request.

        Args:
            request_id: The confirmation request identifier.
            user_action: One of "confirmed", "corrected", or "timeout".

        Returns:
            The resolved action: "confirmed", "corrected", or "timeout".
        """
        req = self._pending.pop(request_id, None)
        if req is None:
            logger.warning(
                "GOV-010: unknown or expired confirmation request id={}", request_id,
            )
            return "timeout"

        if user_action not in {"confirmed", "corrected", "timeout"}:
            logger.warning(
                "GOV-010: invalid user_action={} for request={}, defaulting to corrected",
                user_action, request_id,
            )
            return "corrected"

        logger.info(
            "GOV-010: confirmation resolved id={} action={} directive={}",
            request_id, user_action, req.directive_id,
        )
        return user_action
