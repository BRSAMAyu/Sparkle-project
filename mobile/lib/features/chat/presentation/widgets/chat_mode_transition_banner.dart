import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';

/// Mode transition record for tracking changes within a conversation.
class ModeTransitionRecord {
  const ModeTransitionRecord({
    required this.fromMode,
    required this.toMode,
    required this.timestamp,
    this.reason,
  });

  final ChatMode fromMode;
  final ChatMode toMode;
  final DateTime timestamp;
  final String? reason;

  /// Whether this transition is from direct→workflow or vice versa.
  bool get isDirectToWorkflow =>
      !fromMode.isMultiAgent && toMode.isMultiAgent;

  bool get isWorkflowToDirect =>
      fromMode.isMultiAgent && !toMode.isMultiAgent;
}

/// Provider that tracks mode transitions within the current chat session.
final modeTransitionHistoryProvider =
    StateNotifierProvider<ModeTransitionHistoryNotifier, List<ModeTransitionRecord>>(
  ModeTransitionHistoryNotifier.new,
);

class ModeTransitionHistoryNotifier
    extends StateNotifier<List<ModeTransitionRecord>> {
  ModeTransitionHistoryNotifier(this._ref) : super([]) {
    _ref.listen<ChatMode>(
      chatModeProvider,
      (previous, next) {
        if (previous != null && previous != next) {
          state = [
            ...state,
            ModeTransitionRecord(
              fromMode: previous,
              toMode: next,
              timestamp: DateTime.now(),
            ),
          ];
        }
      },
    );
  }

  final Ref _ref;

  void clear() => state = [];
}

/// Inline banner shown in the chat stream when the mode transitions.
///
/// Shows a subtle indicator of the mode change with the from/to modes.
/// Auto-dismisses after a short duration.
class ChatModeTransitionBanner extends ConsumerStatefulWidget {
  const ChatModeTransitionBanner({
    required this.transition,
    super.key,
  });

  final ModeTransitionRecord transition;

  @override
  ConsumerState<ChatModeTransitionBanner> createState() =>
      _ChatModeTransitionBannerState();
}

class _ChatModeTransitionBannerState
    extends ConsumerState<ChatModeTransitionBanner>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _opacity = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    );
    unawaited(_controller.forward());

    // Auto-dismiss after 5 seconds
    unawaited(_dismissAfterDelay());
  }

  Future<void> _dismissAfterDelay() async {
    await Future<void>.delayed(const Duration(seconds: 5));
    if (mounted) {
      await _controller.reverse();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.transition;
    final l10n = I18nService.instance.l10n;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final isUpgrade = t.isDirectToWorkflow;
    final accentColor = isUpgrade ? t.toMode.color : DS.textSecondary;

    return FadeTransition(
      opacity: _opacity,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing4,
        ),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: accentColor.withValues(alpha: isDark ? 0.12 : 0.08),
            borderRadius: DS.borderRadius12,
            border: Border.all(
              color: accentColor.withValues(alpha: 0.2),
            ),
          ),
          child: Row(
            children: [
              Icon(
                isUpgrade ? Icons.trending_up_rounded : Icons.chat_bubble_outline,
                size: DS.iconSizeSm,
                color: accentColor,
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  isUpgrade
                      ? l10n.chatModeTransitionToWorkflow(t.toMode.label)
                      : t.isWorkflowToDirect
                          ? l10n.chatModeTransitionToDirect
                          : l10n.chatModeTransitionSwitched(t.toMode.label),
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: accentColor,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
