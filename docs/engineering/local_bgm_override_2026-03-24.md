# Local BGM Override

This machine now supports a local-only BGM override layer for development and simulator verification.

## Behavior

- Enabled only in `debug` builds.
- Enabled only when `BgmPalette.adaptive` is selected.
- Prefers local file clips under:
  - `/Users/brsama/code/GitHub/Sparkle-project/mobile/local_audio_overrides/bgm`
- Falls back to bundled app assets when a local clip is missing.
- The local override directory is ignored by git and is not part of release assets.

## Current Track Mapping

- `dashboard` -> `home_morning.ogg`
- `chat` -> `chat_ambient.ogg`
- `task` -> `task_flow.ogg`
- `calendar` -> `calendar_plan.ogg`
- `plan` -> `calendar_plan.ogg`
- `focusStart` -> `focus_deep.ogg`
- `focus` -> `focus_binaural.ogg`
- `focusDeep` -> `focus_deep.ogg`
- `galaxy` -> `galaxy_space.ogg`
- `insights` -> `insights_harp.ogg`
- `seeds` -> `seeds_nature.ogg`
- `community` -> `community_jazz.ogg`
- `achievement` -> `achievement_warm.ogg`
- `celebration` -> `achievement_warm.ogg`
- `visualUnlock` -> `achievement_warm.ogg`
- `profile` -> `profile_reflect.ogg`
- `thinking` -> `insights_harp.ogg`
- `tools` -> `task_flow.ogg`

## Current Source Families

- Joe Hisaishi:
  - `home_morning`
  - `achievement_warm`
  - `community_jazz`
- Chopin nocturnes:
  - `chat_ambient`
  - `focus_binaural`
  - `insights_harp`
  - `profile_reflect`
- Mozart solo piano:
  - `focus_deep`
  - `calendar_plan`
  - `seeds_nature`
  - `task_flow`
- String quartet:
  - `galaxy_space`

## Notes

- This setup is intentionally local-only because the source recordings are private/commercial library files.
- For release builds, keep using the bundled BGM assets unless a separately licensed soundtrack pack is prepared.
