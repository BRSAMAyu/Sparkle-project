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
EXECUTION_TEMPLATE_SELECTED = "execution.template_selected"
EXECUTION_NODE_SELECTED = "execution.node_selected"
EXECUTION_QUALITY_RECORDED = "execution.quality_recorded"
TOOL_EXECUTION_STARTED = "tool.execution.started"
TOOL_EXECUTION_COMPLETED = "tool.execution.completed"
TOOL_EXECUTION_FAILED = "tool.execution.failed"
TOOL_EXECUTION_TIMED_OUT = "tool.execution.timed_out"

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
    "EXECUTION_TEMPLATE_SELECTED",
    "EXECUTION_NODE_SELECTED",
    "EXECUTION_QUALITY_RECORDED",
    "TOOL_EXECUTION_STARTED",
    "TOOL_EXECUTION_COMPLETED",
    "TOOL_EXECUTION_FAILED",
    "TOOL_EXECUTION_TIMED_OUT",
]
