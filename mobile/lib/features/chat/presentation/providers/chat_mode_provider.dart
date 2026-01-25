import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';

/// Chat Mode Provider
///
/// Simple state provider for the current chat mode.
/// Defaults to standard mode.
final chatModeProvider = StateProvider<ChatMode>((ref) => standard);

/// Chat Mode Notifier Provider
///
/// StateNotifier provider for more complex chat mode state management.
/// Use this for mode changes with additional side effects.
final chatModeNotifierProvider =
    StateNotifierProvider<ChatModeNotifier, ChatMode>((ref) => ChatModeNotifier());

/// Chat Mode Notifier
///
/// Manages the current chat mode with persistence support.
class ChatModeNotifier extends StateNotifier<ChatMode> {
  ChatModeNotifier() : super(standard);

  /// Set the chat mode
  void setMode(ChatMode mode) {
    state = mode;
  }

  /// Reset to standard mode
  void resetToStandard() {
    state = standard;
  }

  /// Toggle between standard and the last multi-agent mode
  void toggleMode(ChatMode? preferredMode) {
    if (state.apiValue == 'standard' && preferredMode != null) {
      state = preferredMode;
    } else {
      state = standard;
    }
  }

  /// Set mode from API value
  void setFromApiValue(String value) {
    state = ChatMode.fromApiValue(value);
  }
}

/// Last used multi-agent mode provider
///
/// Remembers the last multi-agent mode the user selected.
final lastMultiAgentModeProvider =
    StateProvider<ChatMode?>((ref) => null);
