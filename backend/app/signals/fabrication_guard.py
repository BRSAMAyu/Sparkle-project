"""
Core: execution
Phase: adapt
Stage: GOV-017 Misleading Prevention

FabricationGuard -- Source validation pipeline that prevents the system from
presenting unverifiable claims as facts.

Rules:
- Fact/scope claims without a cited source are flagged "unverifiable".
- Effectiveness claims above 0.9 confidence without outcome data get "needs_disclaimer".
- Claims referencing a source_id are cross-checked against the user's SourceTray in Redis.
- Free-text responses are scanned for common fabrication indicators.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from loguru import logger


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIABLE = "unverifiable"
    NEEDS_DISCLAIMER = "needs_disclaimer"
    SOURCE_NOT_FOUND = "source_not_found"


@dataclass
class VerifiedClaim:
    claim_text: str
    is_verified: bool
    verification_status: VerificationStatus
    source_id: str | None = None
    note: str = ""


# ── Fabrication pattern detectors ────────────────────────────────────────

_FABRICATION_PATTERNS: list[tuple[str, str]] = [
    (
        r"(?i)studies?\s+(?:have\s+)?(?:shown|found|proven|demonstrated)\s+that\s+\w+\s+(?:is|are|can|will|reduces?|improves?|increases?)\s+\d{1,3}%",
        "vague study with specific percentage",
    ),
    (
        r"(?i)research\s+from\s+(?:19|20)\d{2}\s+(?:found|shows?|suggests?)\s+that",
        "research-from-year vague citation",
    ),
    (
        r"https?://(?:www\.)?(?!example\.com|localhost|127\.0\.0\.1|docs\.)[a-z0-9-]+\.(com|org|net|edu|io)/[^\s]*?(?:study|paper|research|meta.analysis)",
        "URL pretending to link a study",
    ),
    (
        r"(?i)(?:according\s+to|based\s+on)\s+(?:a\s+)?(?:Harvard|Stanford|MIT|Yale|Oxford|Cambridge)\s+(?:study|research|paper|report)",
        "prestige-institution namedrop without real reference",
    ),
    (
        r"(?i)(?:improved|increased|reduced|boosted)\s+(?:by|to)\s+\d{1,3}(?:\.\d+)?%?(?:\s+(?:points?|percent))?",
        "specific numeric claim without source",
    ),
    (
        r"(?i)(?:meta-analysis|systematic\s+review|randomized\s+controlled\s+trial)\s+(?:of|on|found)",
        "study type namedrop without DOI/link",
    ),
]


async def verify_claims(
    claims: list[dict[str, Any]],
    user_id: str,
    redis: Any,
) -> list[VerifiedClaim]:
    """Verify a batch of claims against the user's SourceTray in Redis."""
    results: list[VerifiedClaim] = []
    source_tray_key = f"spine:source_tray:{user_id}"

    # Fetch known source ids once
    try:
        tray_members = await redis.smembers(source_tray_key)  # type: ignore[union-attr]
        known_ids: set[str] = {m.decode() if isinstance(m, bytes) else str(m) for m in (tray_members or set())}
    except Exception:
        logger.warning("FabricationGuard: could not read source tray for user={}", user_id)
        known_ids = set()

    for claim in claims:
        text: str = claim.get("claim_text", "")
        cited: str | None = claim.get("cited_source_id")
        ctype: str = claim.get("claim_type", "fact")
        confidence: float = float(claim.get("confidence", 0.5))

        # 1. Source-backed verification
        if cited:
            if cited in known_ids:
                results.append(VerifiedClaim(
                    claim_text=text,
                    is_verified=True,
                    verification_status=VerificationStatus.VERIFIED,
                    source_id=cited,
                    note="source found in user tray",
                ))
            else:
                results.append(VerifiedClaim(
                    claim_text=text,
                    is_verified=False,
                    verification_status=VerificationStatus.SOURCE_NOT_FOUND,
                    source_id=cited,
                    note=f"source_id {cited} not in tray",
                ))
            continue

        # 2. Fact / scope without source → unverifiable
        if ctype in ("fact", "scope"):
            results.append(VerifiedClaim(
                claim_text=text,
                is_verified=False,
                verification_status=VerificationStatus.UNVERIFIABLE,
                note=f"{ctype} claim without cited source",
            ))
            continue

        # 3. Effectiveness claims at high confidence need disclaimer
        if ctype == "effectiveness" and confidence > 0.9:
            results.append(VerifiedClaim(
                claim_text=text,
                is_verified=False,
                verification_status=VerificationStatus.NEEDS_DISCLAIMER,
                note="high-confidence effectiveness claim without outcome data",
            ))
            continue

        # 4. Recommendations pass through as verified (opinion, not fact)
        results.append(VerifiedClaim(
            claim_text=text,
            is_verified=True,
            verification_status=VerificationStatus.VERIFIED,
            note="recommendation-type claim; no source required",
        ))

    logger.debug(
        "FabricationGuard: verified {} claims for user={} (statuses={})",
        len(results),
        user_id,
        [r.verification_status.value for r in results],
    )
    return results


def check_response_for_fabrication(response_text: str) -> list[str]:
    """Scan free-text response for common fabrication indicator patterns."""
    flagged: list[str] = []
    for pattern, description in _FABRICATION_PATTERNS:
        if re.search(pattern, response_text):
            flagged.append(description)
    if flagged:
        logger.warning("FabricationGuard: flagged {} pattern(s) in response", len(flagged))
    return flagged
