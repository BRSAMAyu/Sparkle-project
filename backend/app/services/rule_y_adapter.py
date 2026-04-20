from __future__ import annotations

from app.services.memory_inferred_write_lane import InferredEpisodicCandidate


class RuleYAdapter:
    """Stage 19 adapter that enforces Stage 16's governed inferred-write contract."""

    ALLOWED_SUBJECT_TYPES = {"self", "person_mention", "relationship", "commitment"}

    @classmethod
    def validate(cls, candidate: InferredEpisodicCandidate | None) -> InferredEpisodicCandidate | None:
        if candidate is None:
            return None
        if not candidate.candidate_text.strip():
            return None
        if candidate.subject_type not in cls.ALLOWED_SUBJECT_TYPES:
            return None
        if not candidate.evidence_token or candidate.evidence_token.startswith("llm:"):
            return None
        if not candidate.evidence_refs:
            return None
        if not candidate.semantic_key.strip():
            return None
        if candidate.source_lane.strip() == "":
            return None
        if candidate.subject_type == "commitment" and candidate.due_at is None:
            return None
        if candidate.occurred_at is None:
            return None
        return candidate
