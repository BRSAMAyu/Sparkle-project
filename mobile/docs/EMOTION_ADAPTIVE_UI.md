# Emotion Adaptive UI

FV-12 adds a low-stimulus UI response for Aurora fatigue, stress, and cognitive-load signals.

## Inputs

The mobile WebSocket chat service listens for `aurora_state_band` messages. The payload may include:

- `emotion` or `emotion_state`
- `fatigue_level`
- `cognitive_load`
- `stress_signal`

Numeric values are normalized to `0.0..1.0`; text levels such as `low`, `medium`, `high`, and `critical` are also accepted.

## Modes

The setting **Emotion adaptive mode** supports:

- `auto`: use Aurora signals.
- `always_low`: always use low-stimulus UI.
- `always_normal`: keep the regular UI even when Aurora reports high load.

The mode is stored in SharedPreferences under `settings_emotion_adaptive_mode`.

## Low-Stimulus UI

When active, the app-level wrapper applies:

- Theme text styles increased by 1 px.
- Reduced motion through `MediaQuery.disableAnimations` and no page transitions.
- Simplified card hierarchy by suppressing heavy shared-card shadows.
- A subtle cooler/dimmer color filter.
- Hidden visual reward/challenge badges on the home achievement-progress card.

The wrapper is applied in `SparkleApp`, so the core home, chat, task, and plan pages inherit the same behavior through shared scaffold and design-system primitives.
