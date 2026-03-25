# BGM Scene Mapping 2026-03-24

## Current status

The audio playback chain is now using valid `AssetSource` paths, higher default gain, and iOS audio session activation.

This document records the current production-safe scene mapping after the Phase 2/3/4 audio upgrade:

- Phase 2: generated scene-specific BGM assets from bundled music + ambient sources
- Phase 3: route coverage extended to missing feature route groups
- Phase 4: adaptive mapping, fade tuning, preview support, and runtime fallback

## Bundled BGM assets

- `audio/bgm/relax_background1.ogg`
- `audio/bgm/calm_track_loop.ogg`
- `audio/bgm/loop_city.ogg`
- `audio/bgm/sunset_walk.ogg`
- `audio/bgm/oceanic_drift.ogg`
- `audio/bgm/classical_piano_loop.ogg`
- `audio/bgm/heavenly_loop.ogg`
- `audio/bgm/home_morning.ogg`
- `audio/bgm/chat_ambient.ogg`
- `audio/bgm/task_flow.ogg`
- `audio/bgm/focus_deep.ogg`
- `audio/bgm/focus_binaural.ogg`
- `audio/bgm/galaxy_space.ogg`
- `audio/bgm/achievement_warm.ogg`
- `audio/bgm/community_jazz.ogg`
- `audio/bgm/calendar_plan.ogg`
- `audio/bgm/insights_harp.ogg`
- `audio/bgm/seeds_nature.ogg`
- `audio/bgm/profile_reflect.ogg`

## Current adaptive mapping

- `dashboard` -> `home_morning.ogg`
- `chat` -> `chat_ambient.ogg`
- `community` -> `community_jazz.ogg`
- `task` -> `task_flow.ogg`
- `plan` -> `calendar_plan.ogg`
- `calendar` -> `calendar_plan.ogg`
- `achievement` -> `achievement_warm.ogg`
- `galaxy` -> `galaxy_space.ogg`
- `insights` -> `insights_harp.ogg`
- `seeds` -> `seeds_nature.ogg`
- `tools` -> `task_flow.ogg`
- `profile` -> `profile_reflect.ogg`
- `focusStart` -> `focus_deep.ogg`
- `focus` -> `focus_binaural.ogg`
- `focusDeep` -> `focus_deep.ogg`
- `thinking` -> `insights_harp.ogg`
- `celebration` -> `achievement_warm.ogg`
- `visualUnlock` -> `achievement_warm.ogg`

## Intent by scene

- `dashboard`: light, stable, welcoming
- `chat`: soft and neutral, should not distract from reading
- `community`: a little warmer and more social than chat
- `task/calendar/plan`: more structured and orderly than dashboard
- `focus/focusDeep`: ambient-first, low melody, high concentration
- `achievement/celebration/visualUnlock`: brighter, warmer lift
- `galaxy`: more exploratory and spatial than the rest
- `profile`: reflective and calm

## Runtime fallback rule

If a mapped asset is missing from the bundle, BGM now falls back to:

- `audio/bgm/calm_track_loop.ogg`

This prevents silent failure when a future scene-specific track is configured but not shipped.

## Route coverage added

- `seed-libraries` now uses `BgmTrack.seeds`
- `memory` routes now use `BgmTrack.insights`
- `error-book` routes now use `BgmTrack.task`
- settings screen now supports palette preview playback

## Acceptance notes

- The current mapping is now a **scene-first** audio design built from repository-local resources.
- Generated tracks are derivative mixes and loops built from bundled assets, not externally licensed downloads.
- Any future asset replacement should preserve the same scene intent and fallback behavior.
