import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart' as cm;

/// Chat Mode Provider
///
/// Simple state provider for the current chat mode.
/// Defaults to standard mode.
final chatModeProvider = StateProvider<ChatMode>((ref) => ChatMode.standard);

/// Chat Mode Notifier Provider
///
/// StateNotifier provider for more complex chat mode state management.
/// Use this for mode changes with additional side effects.
final chatModeNotifierProvider =
    StateNotifierProvider<ChatModeNotifier, ChatMode>(ChatModeNotifier.new);

/// Chat Mode Notifier
///
/// Manages the current chat mode with persistence support.
class ChatModeNotifier extends StateNotifier<ChatMode> {
  ChatModeNotifier() : super(ChatMode.standard);

  /// Set the chat mode
  void setMode(ChatMode mode) {
    state = mode;
  }

  /// Reset to standard mode
  void resetToStandard() {
    state = ChatMode.standard;
  }

  /// Toggle between standard and the last multi-agent mode
  void toggleMode(ChatMode? preferredMode) {
    if (state == ChatMode.standard && preferredMode != null) {
      state = preferredMode;
    } else {
      state = ChatMode.standard;
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
    StateProvider<ChatMode?>((ref) => cm.ChatMode.deepAnalysis);
