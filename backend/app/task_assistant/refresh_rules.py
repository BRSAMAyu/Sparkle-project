"""Strong-signal refresh rules for dormant injection cache.

Only refresh when one of the five approved signals fires.
All other changes reuse the cached sidecar.
"""

from __future__ import annotations

# The canonical set of strong-signal triggers that justify a dormant injection refresh.
STRONG_SIGNAL_TRIGGERS: frozenset[str] = frozenset({
    "focus_contract_version_bump",
    "task_guidance_content_change",
    "new_transition_decision_record",
    "insight_claim_status_change",
    "probe_outcome_significant_adjustment",
})


def is_strong_signal(trigger: str) -> bool:
    """Return True only for approved strong-signal triggers."""
    return trigger in STRONG_SIGNAL_TRIGGERS
