# SPARKLE Aurora Stage 11 EVD2 Route Contract (2026-04-20)

> **Purpose**: freeze the allowed secondary routes for evidence drawer items before `WS-EVD2` code lands.

## Route Mapping

| Evidence type | Route target | Parameters | User affordance | Boundary note |
| --- | --- | --- | --- | --- |
| `concept` | `/galaxy/node/:id` | `id = payload.concept.id or evidence.id` | `去星图看` | read-only knowledge detail route |
| `error` | `/errors/:id` | `id = evidence.id` | `去错题本看` | existing error detail route |
| `event` with session marker | `/chat?session_id=:id` | `session_id = payload.event.session_id` | `打开相关对话` | read-only conversation hydration; no write side effect |
| unsupported / redacted | _none_ | _none_ | show non-routable status only | Rule U satisfied via explicit non-route state |

## Guardrails

1. route buttons may render only when the target id is present and non-empty
2. no new route may be invented outside existing router definitions
3. unsupported or missing ids must stay visibly non-clickable
4. widget tests must prove each supported route dispatch
