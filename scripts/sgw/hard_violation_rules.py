from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


SHA1_HEX_RE = re.compile(r"^[a-f0-9]{40}$")
SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class HardViolation:
    code: str
    message: str
    context: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def check_inferred_record(record: dict[str, Any]) -> list[HardViolation]:
    violations: list[HardViolation] = []
    source_lane = _stringify(record.get("source_lane"))
    if source_lane != "inferred_extraction":
        violations.append(
            HardViolation(
                code="SGW-H001",
                message="inferred record must stay on inferred_extraction lane",
                context=source_lane or "<missing>",
            )
        )

    for field_name in ("confidence", "evidence_token", "decay_policy", "source_lane"):
        if record.get(field_name) in (None, ""):
            violations.append(
                HardViolation(
                    code="SGW-H002",
                    message=f"required Rule Y field missing: {field_name}",
                    context=_stringify(record.get("id")),
                )
            )

    confidence = record.get("confidence")
    if confidence is None or not (0.9 <= float(confidence) <= 1.0):
        violations.append(
            HardViolation(
                code="SGW-H003",
                message="confidence outside Stage 16 governed range",
                context=_stringify(confidence),
            )
        )

    mentioned_hash = _stringify(record.get("mentioned_entity_hash"))
    mentioned_name = _stringify(record.get("mentioned_entity_name"))
    if mentioned_name:
        violations.append(
            HardViolation(
                code="SGW-H004",
                message="mentioned entity raw name must not be stored",
                context=mentioned_name,
            )
        )
    if mentioned_hash and SHA1_HEX_RE.match(mentioned_hash):
        violations.append(
            HardViolation(
                code="SGW-H005",
                message="mentioned entity hash must not be global SHA-1",
                context=mentioned_hash,
            )
        )
    if mentioned_hash and not SHA256_HEX_RE.match(mentioned_hash):
        violations.append(
            HardViolation(
                code="SGW-H006",
                message="mentioned entity hash must be HMAC-SHA256 hex when present",
                context=mentioned_hash,
            )
        )

    community_context = record.get("community_context")
    if community_context:
        violations.append(
            HardViolation(
                code="SGW-H007",
                message="social payload leaked into community_context",
                context=_stringify(community_context),
            )
        )

    return violations
