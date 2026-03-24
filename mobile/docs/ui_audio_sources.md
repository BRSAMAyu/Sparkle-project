# UI Audio Spec

Last updated: 2026-03-21

## Current Strategy

- Primary source of truth: procedurally generated audio assets
- Generator script: `/Users/brsama/code/GitHub/Sparkle-project/scripts/generate_sensory_audio.py`
- Output folders:
  - `mobile/assets/audio/ui/`
  - `mobile/assets/audio/ambient/`
- Encoding target:
  - OGG container
  - 44.1kHz
  - stereo
  - nominal 128kbps export settings

## Why Procedural

- Keeps the app's sound language consistent and reproducible
- Makes it easy to tune duration, pitch, decay, and loudness without relicensing assets
- Fits the product's restrained, minimal interaction style

## UI Event Mapping

| Event | Asset | Target feel | Current duration |
|---|---|---|---|
| tap | `tap.ogg` | crisp, quiet tap | ~61ms |
| toggle | `toggle.ogg` | short double-state click | ~81ms |
| selection | `select.ogg` | slightly brighter than tap | ~91ms |
| navigation | `nav.ogg` | soft directional whoosh | ~181ms |
| sheet open | `sheet_open.ogg` | upward lift | ~221ms |
| dialog open | `dialog_open.ogg` | lighter modal pop | ~200ms |
| confirm | `confirm.ogg` | compact rising confirmation | ~181ms |
| success | `success.ogg` | brighter rising triad | ~321ms |
| warning | `warning.ogg` | lower and more cautious | ~261ms |
| error | `error.ogg` | descending broken resolve | ~261ms |
| achievement common | `achievement_common.ogg` | modest unlock | ~280ms |
| achievement rare | `achievement_rare.ogg` | longer and brighter | ~361ms |
| achievement epic | `achievement_epic.ogg` | richer cadence | ~480ms |
| achievement legendary | `achievement_legendary.ogg` | multi-note flourish with tail | ~681ms |
| star unlock | `star_unlock.ogg` | sparkling unlock cue | ~521ms |
| focus complete | `focus_complete.ogg` | calm completion bell | ~441ms |
| streak | `streak.ogg` | energetic milestone cue | ~401ms |
| checkin | `checkin.ogg` | compact positive ping | ~300ms |
| message send | `message_send.ogg` | tiny send tick | ~81ms |
| ai response start | `ai_start.ogg` | soft synthetic rise | ~161ms |
| card flip | `card_flip.ogg` | dry flip sweep | ~120ms |
| drag start | `drag_start.ogg` | soft pickup | ~91ms |
| drag drop | `drag_drop.ogg` | slightly weightier settle | ~110ms |

## Ambient Scenes

| Scene | Asset | Duration | Notes |
|---|---|---|---|
| Rain | `rain.ogg` | 32s | periodic noise bed + droplet texture |
| Ocean | `ocean_waves.ogg` | 96s | trimmed natural wave bed for calmer focus sessions |
| White noise | `white_noise.ogg` | 32s | balanced broadband mask |
| Cafe | `cafe.ogg` | 32s | warm room noise + sparse clink accents |
| Piano | `piano.ogg` | 32s | soft tonal loop over subtle pad |

## Looping Rules

- Ambient assets are generated with loop-safe smoothing at both ends
- Ambient scenes are normalized to avoid loudness jumps when switching
- UI sounds remain short and non-competing with speech, text, and motion

## Regeneration

```bash
python3 /Users/brsama/code/GitHub/Sparkle-project/scripts/generate_sensory_audio.py
```

Regenerate whenever we adjust:

- event taxonomy
- interaction durations
- achievement rarity hierarchy
- ambient texture or loudness targets
