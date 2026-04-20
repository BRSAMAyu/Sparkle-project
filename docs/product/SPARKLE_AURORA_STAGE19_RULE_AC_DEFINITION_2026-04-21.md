# SPARKLE Aurora Rule AC Definition (2026-04-21)

> Rule AC: Working Memory is a session-scoped transient layer. Cross-session persistence is forbidden. Every LLM-generated inferred extraction candidate must pass the same Rule Y four-element validation used by Stage 16 before it can enter Working Memory or consolidate into L1.

## 1. Mandatory constraints

1. Working Memory entries expire no later than session end + 10 minutes.
2. Idle namespaces older than 4 hours expire automatically.
3. Every LLM output must construct a valid `InferredEpisodicCandidate`; any missing element causes discard.
4. Consolidation may happen only when one of these gates is met:
   - same `semantic_key` appears at least 3 times over at least 60 seconds
   - the user gives an explicit anchored remember-this confirmation
   - the item is a commitment with explicit `due_at`
5. LLM extraction budget is capped at 200 tokens per call and 2000 tokens per session.
6. Startup must run orphan cleanup for namespaces not linked to an active chat session.

## 2. Forbidden scenarios

1. Working Memory may not be implemented as an L1 cache.
2. LLM extractor output may not bypass schema validation or Rule Y.
3. Emotion, mood, or intention-strength statements may not consolidate.
4. Consolidation may not happen within 60 seconds of first extraction unless the commitment-with-`due_at` path applies.
5. Working Memory namespaces may not share cross-user prefixes.
6. Consolidation may not skip Stage 16 conflict detection.
7. L1 writes must stop if the Rule AC guard fails.
8. `evidence_token` must point to a real chat turn, never to model output.
9. Generic, unanchored confirmation words such as isolated `是的` or `对` may not trigger consolidation.

## 3. CI guard

`scripts/check_rule_ac_working_memory.py` scans `backend/app/working_memory/` for forbidden persistence usage:

1. SQLAlchemy model imports
2. Alembic references
3. `.save(...)`
4. `.update(...)`
5. `INSERT`
6. `UPDATE`

## 4. Operational intent

Rule AC exists to make Stage 19 safe:

1. Working Memory stays ephemeral.
2. LLM extraction stays bounded.
3. Consolidation stays stricter than extraction.
4. Rollback can rely on Redis TTL even if a crash interrupts cleanup.
