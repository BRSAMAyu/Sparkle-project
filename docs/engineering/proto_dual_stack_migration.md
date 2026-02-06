# Proto Dual-Stack Migration Guide

This guide defines the compatibility contract for timestamp/error-code standardization and the deprecation lifecycle.

## Scope

Files:
- `proto/agent_service.proto`
- `proto/websocket.proto`
- `proto/galaxy_service.proto`

## Added Fields (Non-Breaking)

### Timestamp Migration

- `agent.v1.ChatResponse.event_time` (`google.protobuf.Timestamp`, field `19`)
- `sparkle.ws.WebSocketMessage.event_time` (`google.protobuf.Timestamp`, field `7`)
- `sparkle.ws.UpdateNodeMasteryRequest.event_time` (`google.protobuf.Timestamp`, field `6`)
- `galaxy.v1.CollaborativeGalaxyUpdate.event_time` (`google.protobuf.Timestamp`, field `5`)

Legacy `int64 timestamp` fields remain for compatibility during migration.

### Error Code Migration

- Added `agent.v1.ErrorCode` enum.
- Added `agent.v1.Error.error_code` (field `5`).
- Legacy `agent.v1.Error.code` string is retained.

## Read/Write Rules

Compatibility rule:
1. Writers populate both legacy and new fields while `PROTO_WRITE_DUAL=true`.
2. Readers prefer new fields while `PROTO_READ_NEW_FIRST=true`.
3. Readers fallback to legacy fields if new fields are absent.
4. During rollback, `PROTO_READ_NEW_FIRST=false` allows preferring legacy fields.

## Runtime Feature Flags

- `PROTO_READ_NEW_FIRST` (default: `true`)
  - `true`: read new fields first.
  - `false`: read legacy fields first.
- `PROTO_WRITE_DUAL` (default: `true`)
  - `true`: write both new and legacy fields.
  - `false`: write only new fields.

Flags are consumed by Go gateway and Python gRPC service; mobile side keeps read-fallback compatibility.

## Deprecation Window Policy

Every `[deprecated = true]` proto field must include a nearby comment with `remove_after: Mx`.

Example:

```proto
// Deprecated (remove_after: M3): legacy milliseconds timestamp
int64 timestamp = 6 [deprecated = true];
```

CI enforces this via `scripts/check_proto_deprecated_windows.py`.

## Removal Workflow

1. Add new field (non-breaking), mark old field deprecated with milestone.
2. Dual-write + new-first-read for at least 2 milestones.
3. Observe old-field reads drop to zero.
4. Remove old field and add `reserved <number>;` + `reserved "<name>";`.
5. Update this migration guide in the same PR.

## Operational Note

Code generation strategy in this repo:
1. `make proto-tools-build` builds pinned toolchain image.
2. `make proto-gen` runs generation inside the toolchain container.
3. `make proto-check-generated` verifies generated code is committed.
4. `make proto-breaking` checks compatibility against `main`.
