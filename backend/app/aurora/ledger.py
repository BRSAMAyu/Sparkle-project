from __future__ import annotations

import argparse
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID, uuid4

from app.aurora.schemas import ClaimLifecycle, ClaimSource, InsightClaim, ProbeOutcome, ProjectionPolicy


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _json_safe(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RollbackResult:
    decision_id: str
    rollback_event_id: str
    rollback_anchor: dict[str, Any]


class AppendOnlyLedgerStore:
    """Append-only in-memory or file-backed Aurora ledger."""

    def __init__(self, *, storage_path: str | Path | None = None, records: Iterable[dict[str, Any]] | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else None
        self._records: list[dict[str, Any]] = [dict(item) for item in (records or [])]

    @classmethod
    def load(cls, storage_path: str | Path) -> "AppendOnlyLedgerStore":
        path = Path(storage_path)
        if not path.exists():
            return cls(storage_path=path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records") if isinstance(payload, dict) else []
        return cls(storage_path=path, records=records if isinstance(records, list) else [])

    def dump(self) -> dict[str, Any]:
        return {"records": [dict(record) for record in self._records]}

    def persist(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.dump(), ensure_ascii=False, indent=2, sort_keys=True)
        temp_path = self.storage_path.with_suffix(f"{self.storage_path.suffix}.tmp")
        temp_path.write_text(payload, encoding="utf-8")
        temp_path.replace(self.storage_path)

    def append_record(
        self,
        *,
        record_type: str,
        user_id: UUID | str,
        payload: dict[str, Any],
        occurred_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        source_record_id: str | None = None,
        parent_record_id: str | None = None,
    ) -> dict[str, Any]:
        entry = {
            "record_id": str(uuid4()),
            "record_type": str(record_type),
            "user_id": str(user_id),
            "occurred_at": (occurred_at or _utcnow()).isoformat(),
            "created_at": _utcnow().isoformat(),
            "payload": _json_safe(payload),
            "metadata": _json_safe(metadata or {}),
            "source_record_id": source_record_id,
            "parent_record_id": parent_record_id,
        }
        entry["entry_hash"] = _hash_payload(entry)
        self._records.append(entry)
        self.persist()
        return dict(entry)

    def record_focus_contract(self, *, user_id: UUID | str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self.append_record(record_type="focus_contract", user_id=user_id, payload=payload, **kwargs)

    def record_commitment(self, *, user_id: UUID | str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self.append_record(record_type="commitment", user_id=user_id, payload=payload, **kwargs)

    def record_transition_decision(self, *, user_id: UUID | str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self.append_record(record_type="transition_decision", user_id=user_id, payload=payload, **kwargs)

    def record_claim(self, *, user_id: UUID | str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self.append_record(record_type="insight_claim", user_id=user_id, payload=payload, **kwargs)

    def record_probe_outcome(self, *, user_id: UUID | str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self.append_record(record_type="probe_outcome", user_id=user_id, payload=payload, **kwargs)

    def record_rollback_event(self, *, user_id: UUID | str, payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self.append_record(record_type="rollback_event", user_id=user_id, payload=payload, **kwargs)

    def list_records(
        self,
        *,
        user_id: UUID | str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        record_types: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        record_type_set = {str(item) for item in record_types or []}
        user_id_str = str(user_id) if user_id is not None else None
        selected: list[dict[str, Any]] = []
        for record in self._records:
            if user_id_str and record.get("user_id") != user_id_str:
                continue
            if record_type_set and record.get("record_type") not in record_type_set:
                continue
            occurred_at = self._parse_dt(record.get("occurred_at"))
            if start and occurred_at and occurred_at < start:
                continue
            if end and occurred_at and occurred_at > end:
                continue
            selected.append(dict(record))
        selected.sort(key=lambda item: item.get("occurred_at") or "")
        return selected

    def list_decisions(self, *, user_id: UUID | str | None = None) -> list[dict[str, Any]]:
        return self.list_records(user_id=user_id, record_types={"transition_decision"})

    def find_decision(self, decision_id: UUID | str, *, user_id: UUID | str | None = None) -> dict[str, Any] | None:
        decision_id_str = str(decision_id)
        for record in reversed(self.list_decisions(user_id=user_id)):
            payload = record.get("payload") if isinstance(record, dict) else {}
            if str((payload or {}).get("id") or record.get("record_id")) == decision_id_str:
                return dict(record)
        return None

    def latest_by_type(self, record_type: str, *, user_id: UUID | str | None = None) -> dict[str, Any] | None:
        records = self.list_records(user_id=user_id, record_types={record_type})
        return records[-1] if records else None

    @staticmethod
    def _parse_dt(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed


class ClaimLifecycleManager:
    """Append-only lifecycle helper for InsightClaim versions."""

    def __init__(self, ledger: AppendOnlyLedgerStore) -> None:
        self.ledger = ledger
        self._latest_claims: dict[UUID, InsightClaim] = {}

    def open_claim(
        self,
        claim: InsightClaim | dict[str, Any],
        *,
        source: ClaimSource | None = None,
        evidence_refs: list[str] | None = None,
        record_event: bool = True,
    ) -> InsightClaim:
        claim_model = self._coerce_claim(claim)
        if source is not None and claim_model.source != source:
            claim_model = claim_model.model_copy(update={"source": source})
        if evidence_refs is not None:
            claim_model = claim_model.model_copy(update={"evidence_refs": list(evidence_refs)})
        if record_event:
            self._append_claim_version(claim_model, event_type="claim_opened")
        self._latest_claims[claim_model.id] = claim_model
        return claim_model

    def create_claim(self, claim: InsightClaim | dict[str, Any], **kwargs: Any) -> InsightClaim:
        return self.open_claim(claim, **kwargs)

    def register_probe_outcome(self, outcome: ProbeOutcome | dict[str, Any], *, record_event: bool = True) -> InsightClaim:
        outcome_model = self._coerce_probe_outcome(outcome)
        existing = self._latest_claims.get(outcome_model.claim_id)
        if existing is None:
            raise KeyError(f"Unknown claim id: {outcome_model.claim_id}")
        if record_event:
            self.ledger.record_probe_outcome(
                user_id=existing.user_id,
                payload=outcome_model,
                source_record_id=str(outcome_model.id),
                parent_record_id=str(existing.id),
            )
        updated_claim = existing.model_copy(
            update={
                "updated_at": outcome_model.created_at,
                "status": ClaimLifecycle.PROBED,
                "probed_at": outcome_model.created_at,
                "probe_outcome_ids": [*existing.probe_outcome_ids, outcome_model.id],
            }
        )
        self._latest_claims[outcome_model.claim_id] = updated_claim
        if record_event:
            self._append_claim_version(updated_claim, event_type="claim_probed", parent_record_id=str(existing.id))
        return updated_claim

    def probe_claim(self, outcome: ProbeOutcome | dict[str, Any], **kwargs: Any) -> InsightClaim:
        return self.register_probe_outcome(outcome, **kwargs)

    def set_status(
        self,
        claim_id: UUID,
        *,
        status: ClaimLifecycle,
        reason: str | None = None,
        evidence_refs: list[str] | None = None,
        record_event: bool = True,
    ) -> InsightClaim:
        existing = self._latest_claims.get(claim_id)
        if existing is None:
            raise KeyError(f"Unknown claim id: {claim_id}")
        payload = {
            "status": status.value,
            "reason": reason,
            "evidence_refs": evidence_refs,
        }
        updated_claim = existing.model_copy(
            update={
                "updated_at": _utcnow(),
                "status": status,
                "evidence_refs": list(evidence_refs) if evidence_refs is not None else existing.evidence_refs,
            }
        )
        if record_event:
            self._append_claim_version(updated_claim, event_type="claim_status_changed", payload=payload, parent_record_id=str(existing.id))
        self._latest_claims[claim_id] = updated_claim
        return updated_claim

    def contextualize(
        self,
        claim_id: UUID,
        *,
        context_note: str,
        evidence_refs: list[str] | None = None,
        record_event: bool = True,
    ) -> InsightClaim:
        existing = self._latest_claims.get(claim_id)
        if existing is None:
            raise KeyError(f"Unknown claim id: {claim_id}")
        updated_claim = existing.model_copy(
            update={
                "updated_at": _utcnow(),
                "status": ClaimLifecycle.CONTEXTUALIZED,
                "evidence_refs": list(evidence_refs) if evidence_refs is not None else existing.evidence_refs,
            }
        )
        payload = {"context_note": context_note, "evidence_refs": evidence_refs or []}
        if record_event:
            self._append_claim_version(updated_claim, event_type="claim_contextualized", payload=payload, parent_record_id=str(existing.id))
        self._latest_claims[claim_id] = updated_claim
        return updated_claim

    def contextualize_claim(self, claim_id: UUID, **kwargs: Any) -> InsightClaim:
        return self.contextualize(claim_id, **kwargs)

    def expire(self, claim_id: UUID, *, reason: str | None = None) -> InsightClaim:
        return self.set_status(claim_id, status=ClaimLifecycle.EXPIRED, reason=reason)

    def get_current_claim(self, claim_id: UUID) -> InsightClaim | None:
        return self._latest_claims.get(claim_id)

    def get_claim_history(self, claim_id: UUID) -> list[dict[str, Any]]:
        claim_id_str = str(claim_id)
        return [
            record
            for record in self.ledger.list_records(record_types={"insight_claim", "probe_outcome"})
            if str((record.get("payload") or {}).get("id") or (record.get("payload") or {}).get("claim_id")) == claim_id_str
        ]

    def _append_claim_version(
        self,
        claim: InsightClaim,
        *,
        event_type: str,
        payload: dict[str, Any] | None = None,
        parent_record_id: str | None = None,
    ) -> dict[str, Any]:
        payload_dict = payload or claim.model_dump(mode="json")
        record = self.ledger.record_claim(
            user_id=claim.user_id,
            payload=payload_dict,
            source_record_id=str(claim.id),
            parent_record_id=parent_record_id,
        )
        self._latest_claims[claim.id] = claim
        return record

    def _coerce_claim(self, claim: InsightClaim | dict[str, Any]) -> InsightClaim:
        if isinstance(claim, InsightClaim):
            return claim
        payload = dict(claim)
        payload.setdefault("status", ClaimLifecycle.OPEN)
        payload.setdefault("updated_at", payload.get("created_at") or _utcnow())
        payload.setdefault("source", ClaimSource.AURORA_INFERENCE)
        payload.setdefault("projection_policy", ProjectionPolicy.INTERNAL)
        return InsightClaim(**payload)

    def _coerce_probe_outcome(self, outcome: ProbeOutcome | dict[str, Any]) -> ProbeOutcome:
        if isinstance(outcome, ProbeOutcome):
            return outcome
        return ProbeOutcome(**dict(outcome))


def build_rollback_anchor_from_records(records: list[dict[str, Any]], decision_record: dict[str, Any]) -> dict[str, Any]:
    claim_statuses: dict[str, str] = {}
    for record in records:
        if record.get("record_type") != "insight_claim":
            continue
        payload = record.get("payload") or {}
        claim_id = str(payload.get("id") or "")
        status = str(payload.get("status") or "")
        if claim_id:
            claim_statuses[claim_id] = status
    decision_payload = decision_record.get("payload") or {}
    return {
        "prev_focus_contract_version": decision_payload.get("rollback_anchor", {}).get("prev_focus_contract_version"),
        "prev_active_commitment_ids": decision_payload.get("rollback_anchor", {}).get("prev_active_commitment_ids", []),
        "prev_claim_statuses": claim_statuses,
        "policy_version_at_decision": decision_payload.get("policy_version"),
    }


def _build_store(path: str | None) -> AppendOnlyLedgerStore:
    return AppendOnlyLedgerStore.load(path) if path else AppendOnlyLedgerStore()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aurora append-only ledger helper")
    parser.add_argument("--store", help="Path to a JSON ledger file", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-decisions", help="List recorded transition decisions")
    list_parser.add_argument("--user-id", default=None)

    rollback_parser = subparsers.add_parser("rollback", help="Append a rollback event for a decision")
    rollback_parser.add_argument("--decision-id", required=True)
    rollback_parser.add_argument("--user-id", default=None)

    show_parser = subparsers.add_parser("show", help="Show ledger records")
    show_parser.add_argument("--user-id", default=None)
    show_parser.add_argument("--record-type", default=None)

    args = parser.parse_args(argv)
    store = _build_store(args.store)

    if args.command == "list-decisions":
        records = store.list_decisions(user_id=args.user_id)
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return 0

    if args.command == "show":
        record_types = {args.record_type} if args.record_type else None
        records = store.list_records(user_id=args.user_id, record_types=record_types)
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return 0

    if args.command == "rollback":
        decision = store.find_decision(args.decision_id, user_id=args.user_id)
        if decision is None:
            raise SystemExit(f"Decision not found: {args.decision_id}")
        anchor = build_rollback_anchor_from_records(store.list_records(user_id=args.user_id), decision)
        user_id = decision.get("user_id") or args.user_id
        result = store.record_rollback_event(
            user_id=user_id or "unknown",
            payload={
                "decision_id": str(args.decision_id),
                "rollback_anchor": anchor,
                "decision_record_id": decision.get("record_id"),
            },
            source_record_id=decision.get("record_id"),
        )
        print(json.dumps({"rollback_event": result, "rollback_anchor": anchor}, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
