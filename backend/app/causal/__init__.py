"""Phase-0 evaluation-grade episode logging.

Augments [app.signals.types.CausalTrace] with the fields required by the
P4 research-grade vision (context_signature, candidate_policies,
selection_reason, expected_outcome vs actual_outcome) without modifying
the foundational type, so existing spine code keeps working unchanged.

Each episode is keyed by [trace_id] and stored alongside the existing
CausalTrace, letting downstream analysis join the two.
"""
