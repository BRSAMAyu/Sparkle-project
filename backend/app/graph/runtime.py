"""Graph execution runtime for Aurora TDR consumption."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.aurora.schemas import (
    Commitment,
    FocusContract,
    SignalSnapshot,
    ScenarioPackManifest,
    TransitionDecisionRecord,
    WindowState,
)
from app.graph.backbone import BackbonePathResolver
from app.graph.commitment_engine import CommitmentLifecycleManager
from app.graph.focus_contract_manager import FocusContractLifecycleManager
from app.graph.transitions import TransitionEvaluation, TransitionPolicyEngine


@dataclass(slots=True)
class GraphRuntimeState:
    """Mutable runtime state for one user."""

    focus_contract_id: UUID
    window_state: WindowState | None = None
    note: str = "bootstrap"


@dataclass(frozen=True, slots=True)
class GraphExecutionResult:
    """Outcome of a single graph runtime execution step."""

    user_id: UUID
    previous_node_id: str
    current_node_id: str
    transition_evaluation: TransitionEvaluation
    focus_contract: FocusContract
    window_state: WindowState | None
    active_commitment_ids: tuple[UUID, ...]
    rollback_applied: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class GraphRuntime:
    """In-memory execution boundary between TDR decisions and graph state."""

    def __init__(
        self,
        manifest: ScenarioPackManifest,
        *,
        rollback_enabled: bool = False,
        transition_engine: TransitionPolicyEngine | None = None,
    ) -> None:
        self._resolver = BackbonePathResolver(manifest)
        self.focus_contracts = FocusContractLifecycleManager()
        self.commitments = CommitmentLifecycleManager()
        self._transition_engine = transition_engine or TransitionPolicyEngine()
        self._rollback_enabled = rollback_enabled
        self._state_by_user_id: dict[UUID, GraphRuntimeState] = {}

    @property
    def resolver(self) -> BackbonePathResolver:
        return self._resolver

    def bootstrap(
        self,
        *,
        focus_contract: FocusContract,
        commitments: list[Commitment] | None = None,
        window_state: WindowState | None = None,
    ) -> None:
        self.focus_contracts.register(focus_contract)
        for commitment in commitments or []:
            self.commitments.register(commitment)
        if window_state is not None:
            self.commitments.register_window_state(window_state)
        self._state_by_user_id[focus_contract.user_id] = GraphRuntimeState(
            focus_contract_id=focus_contract.id,
            window_state=window_state,
        )

    def current_focus_contract(self, user_id: UUID) -> FocusContract:
        return self.focus_contracts.lookup_current(user_id)

    def apply_decision(
        self,
        decision: TransitionDecisionRecord,
        *,
        snapshot: SignalSnapshot | None = None,
    ) -> GraphExecutionResult:
        current_focus = self.current_focus_contract(decision.user_id)
        previous_node_id = current_focus.active_node

        if decision.decision_type.lower() == "rollback":
            return self._apply_rollback(decision, previous_node_id=previous_node_id)

        evaluation = self._transition_engine.evaluate(
            decision,
            current_node_id=previous_node_id,
            resolver=self._resolver,
        )

        if evaluation.allow and evaluation.target_node_id != previous_node_id:
            current_focus = self.focus_contracts.create_version(
                current_focus,
                active_node=evaluation.target_node_id,
                trigger_decision_ref=decision.id,
                evidence_refs=[*current_focus.evidence_refs, *decision.evidence_refs],
            )
            self._state_by_user_id[decision.user_id].focus_contract_id = current_focus.id

        return GraphExecutionResult(
            user_id=decision.user_id,
            previous_node_id=previous_node_id,
            current_node_id=current_focus.active_node,
            transition_evaluation=evaluation,
            focus_contract=current_focus,
            window_state=self.commitments.current_window_state(decision.user_id),
            active_commitment_ids=tuple(self.commitments.active_commitment_ids(decision.user_id)),
            metadata={
                "snapshot_hash": snapshot.snapshot_hash if snapshot is not None else None,
                "policy_version": decision.policy_version,
            },
        )

    def _apply_rollback(self, decision: TransitionDecisionRecord, *, previous_node_id: str) -> GraphExecutionResult:
        if not self._rollback_enabled:
            raise RuntimeError("Rollback support is disabled")

        anchor = decision.rollback_anchor
        prev_focus_version = int(anchor["prev_focus_contract_version"])
        active_commitment_ids = [UUID(commitment_id) for commitment_id in anchor.get("prev_active_commitment_ids", [])]

        current_focus = self.current_focus_contract(decision.user_id)
        restored_focus = self.focus_contracts.rewind_to_version(current_focus.id, prev_focus_version)
        self.commitments.restore_active_commitment_ids(decision.user_id, active_commitment_ids)
        self._state_by_user_id[decision.user_id].focus_contract_id = restored_focus.id

        return GraphExecutionResult(
            user_id=decision.user_id,
            previous_node_id=previous_node_id,
            current_node_id=restored_focus.active_node,
            transition_evaluation=TransitionEvaluation(
                allow=True,
                target_node_id=restored_focus.active_node,
                is_backbone_transition=True,
                reason="rollback_applied",
            ),
            focus_contract=restored_focus,
            window_state=self.commitments.current_window_state(decision.user_id),
            active_commitment_ids=tuple(self.commitments.active_commitment_ids(decision.user_id)),
            rollback_applied=True,
            metadata={"rollback_anchor": anchor},
        )
