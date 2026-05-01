"""FocusContract lifecycle manager."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.aurora.schemas import FocusContract, ProjectionPolicy, WritePath

_MISSING = object()


class FocusContractLifecycleManager:
    """Append-only lifecycle manager with O(1) current lookup by user id."""

    def __init__(self) -> None:
        self._current_by_user_id: dict[UUID, FocusContract] = {}
        self._history_by_contract_id: dict[UUID, list[FocusContract]] = {}

    def register(self, contract: FocusContract) -> FocusContract:
        history = self._history_by_contract_id.setdefault(contract.id, [])
        history.append(contract)
        self._current_by_user_id[contract.user_id] = contract
        return contract

    def lookup_current(self, user_id: UUID) -> FocusContract:
        return self._current_by_user_id[user_id]

    def lookup_version(self, contract_id: UUID, version: int) -> FocusContract:
        for contract in self._history_by_contract_id.get(contract_id, []):
            if contract.version == version:
                return contract
        raise KeyError(f"Unknown focus contract version: {contract_id} v{version}")

    def version_chain(self, contract_id: UUID) -> tuple[FocusContract, ...]:
        return tuple(self._history_by_contract_id.get(contract_id, []))

    def create_version(
        self,
        contract: FocusContract,
        *,
        active_node: str | None = None,
        focus_description: str | None = None,
        desire_hypothesis: str | object = _MISSING,
        commitment_ids: list[UUID] | None = None,
        trigger_decision_ref: UUID | None = None,
        evidence_refs: list[str] | None = None,
        created_at: datetime | None = None,
        created_by: str | None = None,
        projection_policy: ProjectionPolicy | None = None,
        write_path: WritePath | None = None,
    ) -> FocusContract:
        updates: dict[str, Any] = {
            "version": contract.version + 1,
            "active_node": active_node or contract.active_node,
            "focus_description": focus_description if focus_description is not None else contract.focus_description,
            "commitment_ids": list(commitment_ids) if commitment_ids is not None else list(contract.commitment_ids),
            "created_at": created_at or datetime.utcnow(),
            "created_by": created_by or contract.created_by,
            "trigger_decision_ref": trigger_decision_ref,
            "evidence_refs": list(evidence_refs) if evidence_refs is not None else list(contract.evidence_refs),
            "projection_policy": projection_policy or contract.projection_policy,
            "write_path": write_path or contract.write_path,
        }
        if desire_hypothesis is not _MISSING:
            updates["desire_hypothesis"] = desire_hypothesis
        new_contract = contract.model_copy(update=updates)
        return self.register(new_contract)

    def rewind_to_version(self, contract_id: UUID, version: int) -> FocusContract:
        versioned_contract = self.lookup_version(contract_id, version)
        self._current_by_user_id[versioned_contract.user_id] = versioned_contract
        return versioned_contract
