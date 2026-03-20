# UI Audio Sources

Last updated: 2026-03-20

## Selected Asset Pack

- Source: OpenGameArt
- Pack: `UI Sounds`
- Author: `StumpyStrust`
- License: `CC0`
- Download URL used in implementation: `https://opengameart.org/sites/default/files/sounds_2.zip`
- Local asset target: `mobile/assets/audio/ui/`

## Imported Files

- `button1.ogg`
- `button2.ogg`
- `complete.ogg`
- `off.ogg`
- `on.ogg`

## Event Mapping

| App event | Asset | Notes |
|---|---|---|
| tap | `button1.ogg` | light press on cards and buttons |
| selection / toggle | `button2.ogg` | list selection, pills, mode switches |
| navigation / sheet open / dialog open | `on.ogg` | transition cue with low volume |
| confirm / success | `complete.ogg` | completion, submit, positive resolve |
| warning / error | `off.ogg` | caution, destructive, failed action |

## Design Direction

- Audio is intentionally quiet and short-lived.
- Sound should confirm state change, not compete with reading or motion.
- Haptics mirror the same semantic layers so sound-off mode still feels coherent.
- Any future custom branded sounds should preserve the same event semantics and volume hierarchy.
