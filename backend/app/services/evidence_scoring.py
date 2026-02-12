from __future__ import annotations

from collections.abc import Iterable
from typing import Any

PRIMARY_EVIDENCE_TYPES = {"event", "user_state", "error"}


def compute_score(evidence_refs: Iterable[Any], evidence_missing: bool = False) -> float:
    score = 0.2
    types = set()
    has_primary = False

    for ref in evidence_refs or []:
        ref_type = ref.get("type") if isinstance(ref, dict) else getattr(ref, "type", None)
        if not ref_type:
            continue
        types.add(ref_type)
        if ref_type in PRIMARY_EVIDENCE_TYPES:
            has_primary = True

    if has_primary:
        score += 0.3
    if len(types) >= 2:
        score += 0.2
    if evidence_missing:
        score -= 0.5

    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score
