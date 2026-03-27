"""
Event type constants for the cognitive feedback loop.
"""

CAPSULE_FEEDBACK_SUBMITTED = "capsule.feedback.submitted"
PROFILE_COGNITIVE_UPDATED = "profile.cognitive.updated"
CAPSULE_REGENERATE_REQUESTED = "capsule.regenerate.requested"
EXECUTION_DELEGATED = "execution.delegated"
EXECUTION_STATUS_CHANGED = "execution.status_changed"
EXECUTION_WAITING_APPROVAL = "execution.waiting_approval"
EXECUTION_APPROVAL_DECISION = "execution.approval_decision"
EXECUTION_RESULT_INGESTED = "execution.result_ingested"
EXECUTION_HANDED_BACK = "execution.handed_back"

__all__ = [
    "CAPSULE_FEEDBACK_SUBMITTED",
    "PROFILE_COGNITIVE_UPDATED",
    "CAPSULE_REGENERATE_REQUESTED",
    "EXECUTION_DELEGATED",
    "EXECUTION_STATUS_CHANGED",
    "EXECUTION_WAITING_APPROVAL",
    "EXECUTION_APPROVAL_DECISION",
    "EXECUTION_RESULT_INGESTED",
    "EXECUTION_HANDED_BACK",
]
