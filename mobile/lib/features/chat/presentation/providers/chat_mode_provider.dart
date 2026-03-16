import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';

/// Chat Mode Provider (persisted)
///
/// Alias for chatModeNotifierProvider for convenience.
/// This provider persists the last selected mode.
final chatModeProvider = chatModeNotifierProvider;

/// Chat Mode Notifier Provider
///
/// StateNotifier provider for more complex chat mode state management.
/// This provider persists the last selected mode.
final chatModeNotifierProvider =
    StateNotifierProvider<ChatModeNotifier, ChatMode>((ref) => ChatModeNotifier());

/// Chat Mode Notifier
///
/// Manages the current chat mode with persistence support.
class ChatModeNotifier extends PersistentNotifier<ChatMode> {
  ChatModeNotifier()
      : super(
          namespace: 'chat_mode',
          key: 'current_mode',
          defaultValue: standard,
          serializer: (mode) => mode.apiValue,
          deserializer: (value) =>
              value != null ? ChatMode.fromApiValue(value) : standard,
        );

  /// Set the chat mode
  void setMode(ChatMode mode) {
    state = mode;
  }

  /// Set mode with visual feedback
  void setModeWithFeedback(ChatMode mode, BuildContext context) {
    final previousMode = state;
    state = mode;

    // Show elegant mode switch feedback
    if (context.mounted) {
      AppFeedback.success(
        context,
        I18nService.instance.l10n.chatModeActivated(mode.label),
      );
    }
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
/// Now persisted to storage.
final lastMultiAgentModeProvider =
    StateNotifierProvider<LastMultiAgentModeNotifier, ChatMode?>(
  (ref) => LastMultiAgentModeNotifier(),
);

/// Last multi-agent mode notifier with persistence
class LastMultiAgentModeNotifier extends PersistentNotifier<ChatMode?> {
  LastMultiAgentModeNotifier()
      : super(
          namespace: 'chat_mode',
          key: 'last_multi_agent_mode',
          defaultValue: null,
          serializer: (mode) => mode?.apiValue ?? '',
          deserializer: (value) {
            if (value == null || value.isEmpty) return null;
            final mode = ChatMode.fromApiValue(value);
            // Only return multi-agent modes (not standard)
            return mode.isMultiAgent ? mode : null;
          },
        );

  /// Set the last multi-agent mode
  void setMode(ChatMode mode) {
    if (mode.isMultiAgent) {
      state = mode;
    }
  }

  /// Clear the stored mode
  void clear() {
    state = null;
  }
}
