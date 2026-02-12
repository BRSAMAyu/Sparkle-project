# ADR-0003: Proto v2 Migration and v1 Sunset

## Status
Accepted and Completed

## Context
Sparkle migrated legacy protocol fields (int64 timestamps and string error code) to canonical v2 fields:

- `google.protobuf.Timestamp`
- enum `ErrorCode`

## Decision
1. v2 is the only supported runtime protocol for new reads/writes.
2. Removed v1 fields are permanently reserved (number + name).
3. All proto changes must pass unified toolchain checks (`lint`, `breaking`, `check-generated`, deprecation-window checks).
4. Every proto-affecting change must include an ADR and migration note.

## Consequences
- Lower runtime complexity and less branching in Go/Python/Flutter.
- Stronger long-term wire compatibility governance.
- Future compatibility changes must follow explicit staged migration, then full removal with `reserved`.
