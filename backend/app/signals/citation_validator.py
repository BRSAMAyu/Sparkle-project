"""
Core: execution
Phase: reflect
Stage: P1-16 Citation + Exam Scope Validation

Post-generation validation that LLM citations reference real retrieved sources
and exam-scope answers don't cite unauthorized syllabus chapters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

# Patterns that suggest fabricated citations
_FABRICATION_PATTERNS = [
    r"\([^)]*\d{4}[^)]*\)",       # (Author, 2023) style
    r"\[\d+(?:,\s*\d+)*\]",        # [1], [2,3] numeric citations
    r"according to (?:a|the) study by",  # vague attribution
    r"research (?:shows|indicates|suggests|confirms) that",
]

_CITATION_PATTERN = re.compile(
    r"\[(\d+(?:,\s*\d+)*)\]|\(([^)]*\d{4}[^)]*)\)",
    re.IGNORECASE,
)


@dataclass
class CitationCheckResult:
    passed: bool
    total_citations: int = 0
    verified_count: int = 0
    unverifiable: list[str] = field(default_factory=list)
    fabrication_flags: list[str] = field(default_factory=list)
    exam_scope_violations: list[str] = field(default_factory=list)


class CitationValidator:
    """Validates LLM-generated citations against retrieved source chunks.

    P1-16: Detects fabricated citations and exam scope violations
    before responses reach the user.
    """

    def __init__(self, redis_client: Any = None):
        self.redis = redis_client
        self._cached_source_ids: set[str] = set()

    def validate_response(
        self,
        response_text: str,
        *,
        retrieved_source_ids: set[str] | None = None,
        exam_syllabus_node_ids: set[str] | None = None,
        is_exam_context: bool = False,
    ) -> CitationCheckResult:
        """Check a response for citation quality.

        Args:
            response_text: The LLM-generated response text
            retrieved_source_ids: IDs of sources actually retrieved for this query
            exam_syllabus_node_ids: Allowed knowledge node IDs for exam context
            is_exam_context: Whether this is an exam preparation context
        """
        result = CitationCheckResult(passed=True)
        known_ids = retrieved_source_ids or set()

        # Detect citation-like patterns
        matches = _CITATION_PATTERN.findall(response_text)
        result.total_citations = len(matches)

        if result.total_citations == 0 and not is_exam_context:
            return result  # No citations to verify

        # Check for patterns that suggest fabrication
        for pattern in _FABRICATION_PATTERNS:
            hits = re.findall(pattern, response_text, re.IGNORECASE)
            if hits:
                result.fabrication_flags.extend(hits)

        # If we have source IDs to verify against, check each citation
        if known_ids:
            for match in matches:
                numeric, author_year = match
                if numeric:
                    refs = [n.strip() for n in numeric.split(",")]
                    for ref in refs:
                        if ref not in known_ids:
                            result.unverifiable.append(f"[{ref}]")
                elif author_year:
                    if not any(aid in author_year for aid in known_ids):
                        result.unverifiable.append(author_year)

        # Exam scope validation
        if is_exam_context and exam_syllabus_node_ids:
            for match in matches:
                _, author_year = match
                if author_year:
                    if not any(nid in author_year for nid in exam_syllabus_node_ids):
                        result.exam_scope_violations.append(author_year)

        # Determine pass/fail
        if result.unverifiable:
            result.passed = False
            logger.warning(
                "CitationValidator: {} unverifiable citations found",
                len(result.unverifiable),
            )
        if result.exam_scope_violations:
            result.passed = False
            logger.warning(
                "CitationValidator: {} exam scope violations",
                len(result.exam_scope_violations),
            )
        if len(result.fabrication_flags) > 3:
            result.passed = False

        return result

    def get_verification_note(self, result: CitationCheckResult) -> str | None:
        """Generate a user-visible note about citation quality."""
        if result.passed:
            return None
        parts = []
        if result.unverifiable:
            parts.append(
                f"{len(result.unverifiable)} source reference(s) could not be verified "
                f"against retrieved documents"
            )
        if result.exam_scope_violations:
            parts.append(
                f"{len(result.exam_scope_violations)} reference(s) outside exam syllabus"
            )
        return "; ".join(parts) if parts else None
