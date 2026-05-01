from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from app.aurora.ledger import AppendOnlyLedgerStore, ClaimLifecycleManager
from app.aurora.schemas import InsightClaim, ProbeOutcome, TransitionDecisionRecord


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__"):
        return {str(key): _dump(item) for key, item in vars(value).items() if not str(key).startswith("_")}
    if isinstance(value, dict):
        return {str(key): _dump(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if isinstance(value, tuple):
        return [_dump(item) for item in value]
    return value


@dataclass(frozen=True)
class ProcessedWriteResult:
    write_type: str
    record_id: str | None
    payload: dict[str, Any]


class SignalProcessor:
    """Consumes Aurora outputs and appends downstream write events."""

    def __init__(
        self,
        ledger: AppendOnlyLedgerStore | None = None,
        *,
        downstream_writers: dict[str, Any] | None = None,
        claim_manager: ClaimLifecycleManager | None = None,
    ) -> None:
        self.ledger = ledger or AppendOnlyLedgerStore()
        self.downstream_writers = dict(downstream_writers or {})
        self.claim_manager = claim_manager or ClaimLifecycleManager(self.ledger)

    def process(self, output: Any, *, user_id: UUID | str | None = None) -> dict[str, Any]:
        bundle = self._coerce_bundle(output)
        if user_id is None:
            user_id = self._infer_user_id(bundle)
        if user_id is None:
            raise ValueError("user_id is required when processing Aurora output")

        results: list[ProcessedWriteResult] = []
        tdr = bundle.get("transition_decision_record") or bundle.get("tdr")
        if tdr is not None:
            results.append(self._record_tdr(user_id, tdr))

        for claim in bundle.get("claims") or []:
            results.append(self._record_claim(user_id, claim))

        for outcome in bundle.get("probe_outcomes") or []:
            results.append(self._record_probe_outcome(user_id, outcome))

        for write in bundle.get("write_operations") or bundle.get("writes") or []:
            results.append(self._apply_write(user_id, write))

        return {
            "user_id": str(user_id),
            "processed_writes": [result.__dict__ for result in results],
        }

    def consume_aurora_output(self, output: Any, *, user_id: UUID | str | None = None) -> dict[str, Any]:
        return self.process(output, user_id=user_id)

    def process_bundle(self, output: Any, *, user_id: UUID | str | None = None) -> dict[str, Any]:
        return self.process(output, user_id=user_id)

    def consume(self, output: Any, *, user_id: UUID | str | None = None) -> dict[str, Any]:
        return self.process(output, user_id=user_id)

    def _record_tdr(self, user_id: UUID | str, tdr: TransitionDecisionRecord | dict[str, Any]) -> ProcessedWriteResult:
        model = tdr if isinstance(tdr, TransitionDecisionRecord) else TransitionDecisionRecord(**dict(tdr))
        record = self.ledger.record_transition_decision(
            user_id=user_id,
            payload=model,
            source_record_id=str(model.id),
        )
        return ProcessedWriteResult("transition_decision_record", record.get("record_id"), _dump(model))

    def _record_claim(self, user_id: UUID | str, claim: InsightClaim | dict[str, Any]) -> ProcessedWriteResult:
        model = claim if isinstance(claim, InsightClaim) else InsightClaim(**dict(claim))
        record = self.ledger.record_claim(user_id=user_id, payload=model, source_record_id=str(model.id))
        self.claim_manager.open_claim(model, record_event=False)
        return ProcessedWriteResult("insight_claim", record.get("record_id"), _dump(model))

    def _record_probe_outcome(self, user_id: UUID | str, outcome: ProbeOutcome | dict[str, Any]) -> ProcessedWriteResult:
        model = outcome if isinstance(outcome, ProbeOutcome) else ProbeOutcome(**dict(outcome))
        record = self.ledger.record_probe_outcome(user_id=user_id, payload=model, source_record_id=str(model.id), parent_record_id=str(model.claim_id))
        claim = self.claim_manager.register_probe_outcome(model, record_event=False)
        return ProcessedWriteResult("probe_outcome", record.get("record_id"), _dump(claim))

    def _apply_write(self, user_id: UUID | str, write: dict[str, Any]) -> ProcessedWriteResult:
        kind = str(write.get("kind") or write.get("type") or "").strip().lower()
        payload = _dump(write.get("payload") or write)
        callback = self.downstream_writers.get(kind) or self.downstream_writers.get(f"write_{kind}")
        if callable(callback):
            callback_result = callback(user_id=user_id, payload=payload) if self._callback_accepts_user_id(callback) else callback(payload)
            record_id = None
            if isinstance(callback_result, dict):
                record_id = callback_result.get("record_id")
            else:
                record_id = getattr(callback_result, "record_id", None)
            return ProcessedWriteResult(kind or "write", record_id, payload)

        record = self.ledger.append_record(
            record_type=f"downstream_{kind or 'write'}",
            user_id=user_id,
            payload=payload,
            metadata={"applied_by": "signal_processor"},
            source_record_id=str(write.get("source_record_id") or ""),
        )
        return ProcessedWriteResult(kind or "write", record.get("record_id"), payload)

    def _coerce_bundle(self, output: Any) -> dict[str, Any]:
        if isinstance(output, tuple) and len(output) == 2:
            return {"transition_decision_record": output[0], "claims": output[1]}
        if isinstance(output, TransitionDecisionRecord):
            return {"transition_decision_record": output}
        if isinstance(output, dict):
            return dict(output)
        return {"transition_decision_record": output}

    def _infer_user_id(self, bundle: dict[str, Any]) -> UUID | str | None:
        for key in ("transition_decision_record", "tdr", "claims", "write_operations", "writes"):
            value = bundle.get(key)
            if isinstance(value, list) and value:
                first = value[0]
                candidate = getattr(first, "user_id", None) or (first.get("user_id") if isinstance(first, dict) else None)
                if candidate is not None:
                    return candidate
            if hasattr(value, "user_id"):
                return value.user_id
            if isinstance(value, dict) and value.get("user_id") is not None:
                return value["user_id"]
        return None

    @staticmethod
    def _callback_accepts_user_id(callback: Any) -> bool:
        try:
            from inspect import signature

            params = signature(callback).parameters
            return "user_id" in params
        except Exception:
            return False
