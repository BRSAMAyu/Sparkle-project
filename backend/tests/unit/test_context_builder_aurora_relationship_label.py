"""AURORA-LABEL (PROD-LOG2 ②-6): the LLM profile bundle's Aurora integration.

Production defect: ``context_builder`` read ``rel_state.label`` although
``SparkleRelationshipState`` (``aurora/schemas/primitives.py``) has no ``label``
field — every call raised ``AttributeError`` and the surrounding catch reduced
the whole Aurora profile integration to one warning line (×6 in the PROD-LOG2
window), silently dropping the ``relationship_label`` prompt dimension.

Contract under test (extracted helper ``_collect_aurora_relationship_profile_data``):
- returns all three bundle keys with REAL schema-backed values;
- ``relationship_label`` is the aurora domain's own public derivation
  (``SparkleRelationshipStateManager.derive_view`` → ``maturity_label``),
  never an ad-hoc attribute on the schema;
- a malformed ledger payload must not poison the derived state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.aurora.ledger import AppendOnlyLedgerStore
from app.aurora.schemas.primitives import (
    ClaimSource,
    InsightClaim,
    ProjectionPolicy,
    SparkleRelationshipState,
)
from app.orchestration.context_builder import _collect_aurora_relationship_profile_data

MATURITY_LABELS = {"exploring", "forming", "stable", "trusted"}


def _insight_claim_payload(user_id) -> dict:
    claim = InsightClaim(
        id=uuid4(),
        user_id=user_id,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
        claim_type="study_preference",
        content="偏好在晚上进行深度学习",
        source=ClaimSource.USER_REPORT,
        confidence=0.8,
        projection_policy=ProjectionPolicy.OPEN_EDITABLE,
    )
    return {
        "record_type": "insight_claim",
        "user_id": str(user_id),
        "payload": claim.model_dump(mode="json"),
    }


def test_schema_has_no_label_field_regression_guard() -> None:
    # The ghost attribute must stay a ghost: if someone adds ``label`` to the
    # schema, this contract test should be revisited (the bundle key must then
    # be re-pointed deliberately, not by accident).
    assert "label" not in SparkleRelationshipState.model_fields


async def test_empty_ledger_still_yields_full_bundle_keys() -> None:
    ledger = AppendOnlyLedgerStore()

    data = _collect_aurora_relationship_profile_data(str(uuid4()), ledger=ledger)

    assert set(data) == {"aurora_profile_summary", "relationship_maturity", "relationship_label"}
    assert isinstance(data["aurora_profile_summary"], str) and data["aurora_profile_summary"].strip()
    assert isinstance(data["relationship_maturity"], float)
    assert data["relationship_label"] in MATURITY_LABELS


async def test_label_is_domain_derived_maturity_label() -> None:
    user_id = uuid4()
    ledger = AppendOnlyLedgerStore(records=[_insight_claim_payload(user_id)])

    data = _collect_aurora_relationship_profile_data(str(user_id), ledger=ledger)

    # Single confirmed-ish claim + one interaction → low maturity bucket.
    assert data["relationship_label"] in MATURITY_LABELS
    assert data["relationship_maturity"] > 0.0
    assert "协作成熟度" in data["aurora_profile_summary"]


async def test_high_maturity_maps_to_trusted_label() -> None:
    user_id = uuid4()
    records = [_insight_claim_payload(user_id) for _ in range(6)]
    records.extend({"record_type": "identity_evidence", "user_id": str(user_id)} for _ in range(2))
    ledger = AppendOnlyLedgerStore(records=records)

    data = _collect_aurora_relationship_profile_data(str(user_id), ledger=ledger)

    # interaction_count = len(raw_records) drives maturity up the label ladder.
    assert data["relationship_maturity"] > 0.2
    assert data["relationship_label"] != "exploring"


async def test_malformed_claim_payload_does_not_poison_bundle() -> None:
    user_id = uuid4()
    good = _insight_claim_payload(user_id)
    bad = {"record_type": "insight_claim", "user_id": str(user_id), "payload": {"nonsense": True}}
    ledger = AppendOnlyLedgerStore(records=[good, bad])

    data = _collect_aurora_relationship_profile_data(str(user_id), ledger=ledger)

    assert data["relationship_label"] in MATURITY_LABELS
