# Stage 35 Backend-Only Fields

This document records Stage 35 fields that are intentionally not rendered on the profile surface.

## Backend-Only Registry

| field | status | reason |
| --- | --- | --- |
| `commitment_summary` | `backend-only` | Commitment follow-up remains an accountability/messaging concern and should not duplicate into profile cards. |
| `recent_person_mentions` | `backend-only` | Raw mention summaries are socially sensitive and stay in scoped social surfaces. |
| `learning_state` | `backend-only` | The payload is still backend guidance JSON without a stable mobile presentation. |
| `task_sufficiency_summary` | `backend-only` | This field is a backend clarification/routing aid, not a user-facing artifact. |
| `context_sufficiency_summary` | `backend-only` | This field only supports backend prompt caveats and routing fallbacks. |
| `calendar_context` | `backend-only` | Calendar surfacing is deferred to Stage 36 and must not ship half-rendered in Stage 35. |

## Declared Exceptions

Only entries in this section count as Rule AU `declared`.

| field | reason |
| --- | --- |
| `social_signals_summary` | Social learning summary still needs a dedicated mobile information architecture and remains intentionally hidden in Stage 35. |
| `emotion_hint` | Reserved field; no live payload contract or mobile rendering path is allowed yet. |
