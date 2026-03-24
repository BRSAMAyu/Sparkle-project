# BGM Sources

Last updated: 2026-03-21

## Downloaded Tracks

All tracks below were downloaded from OpenGameArt and are marked `CC0` on their source pages.

| Local asset | Source page | Direct asset used | Intended use |
|---|---|---|---|
| `audio/bgm/relax_background1.ogg` | [relaxbackground1](https://opengameart.org/content/relaxbackground1) | `https://opengameart.org/sites/default/files/relax_background1.ogg` | dashboard, insights |
| `audio/bgm/sunset_walk.ogg` | [Sunset Walk / Ambient / Quiet / Sweet / Loop](https://opengameart.org/content/sunset-walk-ambient-quiet-sweet-loop) | `https://opengameart.org/sites/default/files/SunsetWalk.ogg` | plan, profile |
| `audio/bgm/calm_track_loop.ogg` | [Calm Track](https://opengameart.org/content/calm-track) | `https://opengameart.org/sites/default/files/calm_track-loop.ogg` | chat, task, tools |
| `audio/bgm/heavenly_loop.ogg` | [Heavenly Loop](https://opengameart.org/content/heavenly-loop) | `https://opengameart.org/sites/default/files/Heavenly%20Loop.ogg` | calendar, achievement, galaxy |
| `audio/bgm/loop_city.ogg` | [Loop Town](https://opengameart.org/content/loop-town) | `https://opengameart.org/sites/default/files/loopcity.ogg` | community |
| `audio/bgm/classical_piano_loop.ogg` | [Short Piano Song Loop](https://opengameart.org/content/short-piano-song-loop) | `https://opengameart.org/sites/default/files/pianosong.ogg` | profile, settings, piano palette |
| `audio/bgm/oceanic_drift.ogg` | [Underwater Theme II](https://opengameart.org/node/87701) | `https://opengameart.org/sites/default/files/underwater_theme_ii.zip` → extracted and normalized `Underwater Theme II.ogg` | airy palette, calendar, dashboard, galaxy |
| `audio/ambient/ocean_waves.ogg` | [Sea and River Wave Sounds](https://opengameart.org/content/sea-and-river-wave-sounds) | `https://opengameart.org/sites/default/files/VistulaShort.mp3` → trimmed and normalized | focus ambient ocean scene |

## Mapping Principle

- Home / Insights: warm, low-pressure, reflective
- Chat / Task / Tools: calm but focused, less melodic distraction
- Community: lighter and more social
- Calendar / Achievement / Galaxy: airy, more spacious and uplifting
- Profile / Plan: personal, soft, restorative
- Focus: route-level BGM falls back to the generated ambient piano scene
- Piano palette: more clearly classical, lighter melodic accompaniment
- Airy palette: more oceanic and atmospheric, with wider spatial feel

## Infrastructure Entry Points

- Player + registration stack: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/services/bgm_service.dart`
- Route/component scope wrapper: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/widgets/bgm_scope.dart`
