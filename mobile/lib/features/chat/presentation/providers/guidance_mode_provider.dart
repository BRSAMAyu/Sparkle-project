import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';

/// Guidance mode determines how the AI interacts with the user.
///
/// This is purely a client-side interaction style toggle.
/// It adjusts the metadata sent with messages, allowing the backend
/// (if it respects the hint) to adjust its tone and proactivity.
/// It does NOT change the chat mode or routing logic.
enum GuidanceMode {
  /// AI actively guides, suggests corrections, and volunteers advice.
  aiGuide,

  /// AI is passive — answers questions but doesn't volunteer guidance.
  selfGuide,
}

/// Provider for the current guidance mode (persisted).
final guidanceModeProvider =
    StateNotifierProvider<GuidanceModeNotifier, GuidanceMode>(
  (ref) => GuidanceModeNotifier(),
);

class GuidanceModeNotifier extends PersistentNotifier<GuidanceMode> {
  GuidanceModeNotifier()
      : super(
          namespace: 'chat_guidance',
          key: 'mode',
          defaultValue: GuidanceMode.aiGuide,
          serializer: (mode) => mode.name,
          deserializer: (value) => value == 'selfGuide'
              ? GuidanceMode.selfGuide
              : GuidanceMode.aiGuide,
        );

  set mode(GuidanceMode mode) => state = mode;

  void toggle() => state =
      state == GuidanceMode.aiGuide ? GuidanceMode.selfGuide : GuidanceMode.aiGuide;
}
