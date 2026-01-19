LTM Evidence Semantics

Purpose
Define the canonical meanings of evidence resolution statuses and the behavior when evidence is deleted, compacted, or missing.

Status Definitions
- ok: Evidence exists and is readable; memory item is considered supported.
- redacted: Evidence exists but is soft-deleted or otherwise unavailable for user display; memory item is marked missing and downgraded.
- not_found: Evidence id does not exist (hard delete or never created); memory item is marked missing and downgraded.
- invalid_id: Evidence id format is invalid; memory item is marked missing and downgraded.
- unsupported: Evidence type is not recognized by resolver; memory item is marked missing and downgraded.
- compacted: Evidence has been summarized/compacted and only a minimal snapshot is available.

Evidence Semantics Matrix
Legend: R = resolve status, M = evidence_missing, Action = system response

1) Soft delete (deleted_at set / is_deleted True)
R: redacted
M: True
Action: keep memory item, lower evidence_score, show "evidence missing" banner, prefer snapshot if available.

2) Compacted (future capability)
R: compacted
M: False
Action: keep memory item, keep evidence_score, link to compacted snapshot instead of original.

3) Hard delete / not found
R: not_found
M: True
Action: keep memory item, lower evidence_score, show "evidence missing" banner, prefer snapshot if available.

Resolver Behavior (Current)
- Event: redacted if deleted_at set.
- User state: redacted if deleted_at set.
- Error: redacted if is_deleted True.
- Concept: redacted if deleted_at set.
- Strategy: redacted if deleted_at set.
- Task: redacted if deleted_at set.
- Summary (nightly review): redacted if deleted_at set.

Health/Repair Behavior
- EvidenceHealthService treats any status != ok as missing and sets evidence_missing True.
- Evidence snapshotting only applies to episodic memories.
- Repair job clears evidence_missing when all refs resolve to ok.

Operational Notes
- If evidence is soft-deleted, prefer soft delete over hard delete to preserve redaction semantics.
- Hard delete should be rare and reserved for compliance/erasure requests.
- When compacted evidence is implemented, update EvidenceHealthService to return status "compacted" with minimal detail.
