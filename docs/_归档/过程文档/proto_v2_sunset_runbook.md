# Proto v2 Sunset Runbook (Completed)

This runbook is retained as an execution record for the v1 -> v2 sunset.

## Completed Actions

1. Removed deprecated v1 fields from proto definitions.
2. Added `reserved` number/name for each removed field.
3. Regenerated Go/Python/Flutter bindings.
4. Removed legacy read/write branches in runtime code.
5. Updated migration guide to v2-only.

## Verification Checklist

- [x] `agent_service.proto` legacy fields removed and reserved
- [x] `websocket.proto` legacy fields removed and reserved
- [x] `galaxy_service.proto` legacy fields removed and reserved
- [x] Runtime code no longer reads/writes legacy timestamp/code fields
- [x] Generated code updated
- [x] Compatibility and unit tests pass

## Ongoing Guardrails

- Keep `buf breaking` and generated-code checks mandatory in CI.
- Require ADR + migration note for every proto-impacting PR.
- Reject any attempt to reintroduce free-form string error codes.
