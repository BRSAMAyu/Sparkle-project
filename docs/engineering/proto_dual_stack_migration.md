# Proto Dual-Stack Migration Guide

This guide documents the dual-stack protocol strategy for timestamp and error-code standardization.

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

Migration rule (target behavior):
1. Writers should populate both legacy and new fields.
2. Readers should prefer new fields, then fallback to legacy fields.

## Operational Note

Code generation strategy in this repo:
1. Preferred: `make proto-gen` (tries Buf first).
2. Fallback: if Buf plugin resolution fails, `make proto-gen-legacy` generates Go/Python and attempts Dart generation when `protoc-gen-dart` is available.

M3 requires regenerated bindings to be committed together with runtime dual-stack logic.

### Dart Tooling Compatibility

If generated Dart protobuf code is incompatible with the pinned `protobuf` runtime version, keep runtime behavior backward-compatible by:
1. Keeping legacy `timestamp` writes on mobile.
2. Reading `error_code` if present, otherwise falling back to `code`.
3. Scheduling protobuf runtime + protoc plugin version alignment as a dedicated upgrade change.
