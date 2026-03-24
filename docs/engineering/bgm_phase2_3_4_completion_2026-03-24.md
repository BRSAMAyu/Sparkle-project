# BGM Phase 2/3/4 Completion 2026-03-24

## Scope

This round completes the post-fix audio work after Phase 1 restored audible playback:

- Phase 2: scene-specific music asset expansion
- Phase 3: route coverage completion
- Phase 4: playback polish, preview UX, and graceful fallback

## Phase 2 completed

New generated BGM assets were created from bundled repository audio sources with local `ffmpeg` processing:

- `home_morning.ogg`
- `chat_ambient.ogg`
- `task_flow.ogg`
- `focus_deep.ogg`
- `focus_binaural.ogg`
- `galaxy_space.ogg`
- `achievement_warm.ogg`
- `community_jazz.ogg`
- `calendar_plan.ogg`
- `insights_harp.ogg`
- `seeds_nature.ogg`
- `profile_reflect.ogg`

These assets now live in:

- `mobile/assets/audio/bgm/`

### Size snapshot

- `home_morning.ogg` — 375109 bytes
- `chat_ambient.ogg` — 383379 bytes
- `task_flow.ogg` — 515919 bytes
- `focus_deep.ogg` — 471873 bytes
- `focus_binaural.ogg` — 578118 bytes
- `galaxy_space.ogg` — 593082 bytes
- `achievement_warm.ogg` — 305286 bytes
- `community_jazz.ogg` — 567080 bytes
- `calendar_plan.ogg` — 418348 bytes
- `insights_harp.ogg` — 401679 bytes
- `seeds_nature.ogg` — 390151 bytes
- `profile_reflect.ogg` — 428831 bytes

## Phase 3 completed

Scene audio route coverage was expanded for route groups that were still missing `SceneAudioScope`:

- `seed_library_routes.dart` -> `BgmTrack.seeds`
- `memory_routes.dart` -> `BgmTrack.insights`
- `error_book_routes.dart` -> `BgmTrack.task`

Knowledge detail was already covered via `galaxy_routes.dart`.

## Phase 4 completed

### Adaptive scene mapping

`BgmService` adaptive mode now points to dedicated scene-first assets instead of reusing the same few legacy tracks:

- dashboard -> `home_morning`
- chat -> `chat_ambient`
- task -> `task_flow`
- plan/calendar -> `calendar_plan`
- community -> `community_jazz`
- achievement/celebration/visualUnlock -> `achievement_warm`
- galaxy -> `galaxy_space`
- insights/thinking -> `insights_harp`
- seeds -> `seeds_nature`
- profile -> `profile_reflect`
- focus -> `focus_binaural`
- focusStart/focusDeep -> `focus_deep`

### Fade tuning

- component transitions -> `200ms`
- stage transitions -> `300ms`
- route transitions -> `500ms`
- focus tracks -> `800ms`

### Preview UX

Settings now supports per-palette preview playback without interrupting the main route BGM player.

### Runtime fallback

If a configured scene asset is missing, playback falls back to:

- `audio/bgm/calm_track_loop.ogg`

## Validation

- `flutter analyze lib/core/services/bgm_service.dart ...` -> no new error/warning from this audio work; remaining output in settings screen is existing info-level lint
- `flutter test test/app/router_smoke_test.dart -r compact` -> passed

## Key files changed

- `mobile/lib/core/services/bgm_service.dart`
- `mobile/lib/features/seed_library/seed_library_routes.dart`
- `mobile/lib/features/memory/memory_routes.dart`
- `mobile/lib/features/error_book/error_book_routes.dart`
- `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart`
- `docs/engineering/bgm_scene_mapping_2026-03-24.md`

## Notes

- These tracks are locally generated derivatives from bundled repository audio, not externally downloaded licensed music.
- This completes the engineering integration for Phase 2/3/4, but final artistic tuning can still continue later with dedicated composer-grade assets.
