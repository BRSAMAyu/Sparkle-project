"""Commitment lifecycle and window state management."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from app.aurora.schemas import Commitment, CommitmentStatus, WindowMode, WindowState

_MISSING = object()


class CommitmentLifecycleManager:
    """Append-only lifecycle manager for commitments and window state."""

    def __init__(self) -> None:
        self._current_by_commitment_id: dict[UUID, Commitment] = {}
        self._history_by_commitment_id: dict[UUID, list[Commitment]] = {}
        self._current_window_state_by_user_id: dict[UUID, WindowState] = {}
        self._window_history_by_user_id: dict[UUID, list[WindowState]] = {}

    def register(self, commitment: Commitment) -> Commitment:
        history = self._history_by_commitment_id.setdefault(commitment.id, [])
        history.append(commitment)
        self._current_by_commitment_id[commitment.id] = commitment
        return commitment

    def current(self, commitment_id: UUID) -> Commitment:
        return self._current_by_commitment_id[commitment_id]

    def history(self, commitment_id: UUID) -> tuple[Commitment, ...]:
        return tuple(self._history_by_commitment_id.get(commitment_id, []))

    def create(self, commitment: Commitment) -> Commitment:
        return self.register(commitment)

    def transition_status(
        self,
        commitment_id: UUID,
        status: CommitmentStatus,
        *,
        activated_at: datetime | object = _MISSING,
        resolved_at: datetime | object = _MISSING,
        resolution: str | None | object = _MISSING,
        window_override: WindowMode | None | object = _MISSING,
        evidence_refs: list[str] | object = _MISSING,
    ) -> Commitment:
        current = self.current(commitment_id)
        updates: dict[str, Any] = {"status": status}
        if activated_at is not _MISSING:
            updates["activated_at"] = activated_at
        if resolved_at is not _MISSING:
            updates["resolved_at"] = resolved_at
        if resolution is not _MISSING:
            updates["resolution"] = resolution
        if window_override is not _MISSING:
            updates["window_override"] = window_override
        if evidence_refs is not _MISSING:
            updates["evidence_refs"] = list(evidence_refs)
        new_commitment = current.model_copy(update=updates)
        return self.register(new_commitment)

    def activate_commitment(self, commitment_id: UUID, *, activated_at: datetime | None = None) -> Commitment:
        return self.transition_status(
            commitment_id,
            CommitmentStatus.ACTIVE,
            activated_at=activated_at or datetime.utcnow(),
        )

    def fulfill_commitment(
        self,
        commitment_id: UUID,
        *,
        resolution: str | None = None,
        resolved_at: datetime | None = None,
    ) -> Commitment:
        return self.transition_status(
            commitment_id,
            CommitmentStatus.FULFILLED,
            resolved_at=resolved_at or datetime.utcnow(),
            resolution=resolution,
        )

    def violate_commitment(
        self,
        commitment_id: UUID,
        *,
        resolution: str | None = None,
        resolved_at: datetime | None = None,
    ) -> Commitment:
        return self.transition_status(
            commitment_id,
            CommitmentStatus.VIOLATED,
            resolved_at=resolved_at or datetime.utcnow(),
            resolution=resolution,
        )

    def renegotiate_commitment(self, commitment_id: UUID, *, resolution: str | None = None) -> Commitment:
        return self.transition_status(
            commitment_id,
            CommitmentStatus.RENEGOTIATED,
            resolution=resolution,
        )

    def active_commitment_ids(self, user_id: UUID) -> list[UUID]:
        return [commitment.id for commitment in self._current_by_commitment_id.values() if commitment.user_id == user_id and commitment.status == CommitmentStatus.ACTIVE]

    def register_window_state(self, window_state: WindowState) -> WindowState:
        history = self._window_history_by_user_id.setdefault(window_state.user_id, [])
        history.append(window_state)
        self._current_window_state_by_user_id[window_state.user_id] = window_state
        return window_state

    def get_window_state(self, user_id: UUID) -> WindowState:
        return self._current_window_state_by_user_id[user_id]

    def current_window_state(self, user_id: UUID) -> WindowState | None:
        return self._current_window_state_by_user_id.get(user_id)

    def update_window_state(
        self,
        user_id: UUID,
        *,
        global_mode: WindowMode | None = None,
        commitment_overrides: dict[str, WindowMode] | None = None,
        set_by: str | None = None,
        trigger_decision_ref: UUID | None = None,
        evidence_refs: list[str] | None = None,
    ) -> WindowState:
        previous = self._current_window_state_by_user_id.get(user_id)
        new_state = WindowState(
            id=uuid4(),
            user_id=user_id,
            created_at=datetime.utcnow(),
            global_mode=global_mode or (previous.global_mode if previous is not None else WindowMode.COMMITMENT),
            commitment_overrides=dict(commitment_overrides or (previous.commitment_overrides if previous is not None else {})),
            set_by=set_by or (previous.set_by if previous is not None else "aurora"),
            trigger_decision_ref=trigger_decision_ref if trigger_decision_ref is not None else (previous.trigger_decision_ref if previous is not None else None),
            evidence_refs=list(evidence_refs) if evidence_refs is not None else list(previous.evidence_refs if previous is not None else []),
        )
        return self.register_window_state(new_state)

    def resolve_effective_window_mode(self, user_id: UUID, commitment_id: UUID) -> WindowMode:
        commitment = self._current_by_commitment_id.get(commitment_id)
        if commitment is not None and commitment.window_override is not None:
            return commitment.window_override

        window_state = self._current_window_state_by_user_id.get(user_id)
        if window_state is None:
            return WindowMode.COMMITMENT

        override = window_state.commitment_overrides.get(str(commitment_id))
        if override is not None:
            return override
        return window_state.global_mode

    def set_commitment_window_override(self, commitment_id: UUID, window_mode: WindowMode) -> Commitment:
        return self.transition_status(commitment_id, self.current(commitment_id).status, window_override=window_mode)

    def restore_active_commitment_ids(self, user_id: UUID, active_commitment_ids: list[UUID]) -> None:
        desired_active = set(active_commitment_ids)
        current_commitments = [commitment for commitment in self._current_by_commitment_id.values() if commitment.user_id == user_id]
        for commitment in current_commitments:
            should_be_active = commitment.id in desired_active
            if should_be_active and commitment.status != CommitmentStatus.ACTIVE:
                self.activate_commitment(commitment.id)
            elif not should_be_active and commitment.status == CommitmentStatus.ACTIVE:
                self.transition_status(commitment.id, CommitmentStatus.PENDING)
