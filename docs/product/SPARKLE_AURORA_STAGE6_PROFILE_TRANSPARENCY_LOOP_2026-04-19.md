# Sparkle Aurora Stage 6 Profile Transparency Loop (2026-04-19)

## Purpose

This note records the Stage 6 `WS-V1` hardening pass for the existing
profile-transparency and correction loop.

## What Was Already Real

Before `WS-V1`, the backend already contained:

- `GET /profile/context`
- `GET /profile/insights`
- `POST /profile/insights/control`
- `POST /profile/corrections`

The Stage 6 task is therefore **not** to invent a new transparency API.

## What `WS-V1` Proves

`WS-V1` hardens the backend loop by proving three things with tests:

1. the UI-facing read path can consume `user_insight_transparency` from
   `/profile/context`
2. control actions such as `exam_mode_only` persist scope overrides through the
   existing preference lane
3. correction submissions create `MemoryCorrection` rows and enqueue the
   expected system update

## Boundary

`WS-V1` stays backend-only in Stage 6.

It does **not**:

- add Flutter UI
- redesign transparency payload structure
- introduce new write lanes outside `Rule K`

The remaining frontend consumption work belongs to a later stage once the
backend correction loop is fully accepted as stable.
