# Proto v2 Compatibility Guide (v2-only)

This document is the post-migration contract for Sparkle protocol evolution.

## Scope

- `proto/agent_service.proto`
- `proto/websocket.proto`
- `proto/galaxy_service.proto`

## Canonical Fields

- Time fields use `google.protobuf.Timestamp`.
- Errors use `agent.v1.Error.error_code` (`enum ErrorCode`).

## v1 Sunset Status

The following legacy fields have been removed and reserved:

- `agent.v1.ChatResponse.timestamp` (field `13`)
- `agent.v1.Error.code` (field `1`)
- `sparkle.ws.WebSocketMessage.timestamp` (field `6`)
- `sparkle.ws.UpdateNodeMasteryRequest.timestamp` (field `3`)
- `galaxy.v1.CollaborativeGalaxyUpdate.timestamp` (field `4`)
- `galaxy.v1.UpdateNodeMasteryRequest.version` (field `4`)

## Runtime Rules

1. Readers and writers use v2 fields only.
2. New fields must be added as non-breaking, with explicit migration notes.
3. Removed fields must always be followed by `reserved <number>` and `reserved "<name>"`.

## CI Gates

- `make proto-lint`
- `make proto-breaking`
- `make proto-check-generated`
- `make proto-deprecation-check`
- Proto-changing PRs must update this document and include an ADR.

## Observability Baseline

Keep monitoring:

- `ws_proto_field_read_total`
- `ws_proto_error_code_fallback_total`
- `sparkle_proto_field_read_total`
- `sparkle_proto_error_code_fallback_total`

Expected steady-state:

- no legacy-field read events
- no fallback spikes caused by legacy string code

## Change Workflow (v2-only)

1. Add new canonical field(s) in proto.
2. Regenerate Go/Python/Dart code via unified toolchain.
3. Update runtime mappings and tests across all stacks.
4. Merge only when CI gates and compatibility tests are green.
