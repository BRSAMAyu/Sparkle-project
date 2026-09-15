# Rule AU Exceptions

| date | stage | field | classification | reason |
| --- | --- | --- | --- | --- |
| 2026-04-22 | Stage 35 | `commitment_summary` | `backend-only` | Profile cards should not duplicate commitment follow-up logic already owned elsewhere. |
| 2026-04-22 | Stage 35 | `recent_person_mentions` | `backend-only` | Raw social mention summaries stay in scoped social UX only. |
| 2026-04-22 | Stage 35 | `learning_state` | `backend-only` | The payload is backend guidance JSON without stable user-facing copy. |
| 2026-04-22 | Stage 35 | `task_sufficiency_summary` | `backend-only` | Used only for backend clarification/routing decisions. |
| 2026-04-22 | Stage 35 | `context_sufficiency_summary` | `backend-only` | Used only for backend prompt caveats and routing. |
| 2026-04-22 | Stage 35 | `calendar_context` | `backend-only` | Calendar UX remains deferred to Stage 36. |
