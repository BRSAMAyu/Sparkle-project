import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_team_sheet.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_mode_selector_sheet.dart';

/// Chat Mode Selector Pill Widget
///
/// A tappable pill widget that shows the current chat mode
/// and allows changing it via a bottom sheet.
///
/// States:
/// - Standard mode: Shows mode selector trigger with default style
/// - Multi-agent mode: Shows selected mode with its color and icon
class ChatModeSelectorPill extends ConsumerWidget {
  const ChatModeSelectorPill({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentMode = ref.watch(chatModeProvider);

    if (currentMode.apiValue == 'standard') {
      return AnimatedSwitcher(
        duration: AnimationSystem.normal,
        switchInCurve: AnimationSystem.smooth,
        switchOutCurve: AnimationSystem.smooth,
        child: _UnselectedPill(
          key: const ValueKey('mode-pill-unselected'),
          onTap: () => _showModeSelector(context, ref),
        ),
      );
    }

    return AnimatedSwitcher(
      duration: AnimationSystem.normal,
      switchInCurve: AnimationSystem.smooth,
      switchOutCurve: AnimationSystem.smooth,
      child: _SelectedPill(
        key: ValueKey('mode-pill-${currentMode.apiValue}'),
        mode: currentMode,
        onTap: () => _showModeSelector(context, ref),
      ),
    );
  }

  void _showModeSelector(BuildContext context, WidgetRef ref) {
    unawaited(HapticFeedback.lightImpact());
    unawaited(
      showSensoryModalBottomSheet<Object>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        isScrollControlled: true,
        builder: (context) => const ChatModeSelectorSheet(),
      ).then((result) {
        if (!context.mounted) return;
        if (result == openTeamBuilderSentinel) {
          unawaited(
            showSensoryModalBottomSheet<void>(
              context: context,
              backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
              isScrollControlled: true,
              builder: (_) => const AgentTeamSheet(),
            ),
          );
          return;
        }
        if (result is ChatMode) {
          // Use setModeWithFeedback for visual feedback
          ref
              .read(chatModeNotifierProvider.notifier)
              .setModeWithFeedback(result, context);
          if (result.apiValue != 'standard') {
            ref.read(lastMultiAgentModeProvider.notifier).state = result;
          }
        }
      }),
    );
  }
}

class _UnselectedPill extends StatelessWidget {
  const _UnselectedPill({
    required this.onTap,
    super.key,
  });

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        child: GestureDetector(
          onTap: onTap,
          child: MaterialStyler(
            material: AppMaterials.ceramic.copyWith(
              // Use surfaceTertiary for consistent theming with Dashboard
              backgroundColor: DS.surfaceTertiary,
            ),
            borderRadius: DS.borderRadius20,
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing8,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.auto_awesome,
                  size: DS.iconSizeSm,
                  color: DS.textSecondary,
                ),
                const SizedBox(width: DS.spacing6),
                Text(
                  context.l10n.chatModeSelect,
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
                const SizedBox(width: DS.spacing4),
                Icon(
                  Icons.keyboard_arrow_down_rounded,
                  size: DS.iconSizeSm,
                  color: DS.textSecondary,
                ),
              ],
            ),
          ),
        ),
      );
}

class _SelectedPill extends StatelessWidget {
  const _SelectedPill({
    required this.mode,
    required this.onTap,
    super.key,
  });

  final ChatMode mode;
  final VoidCallback onTap;

  String get _displayLabel {
    final l10n = I18nService.instance.l10n;
    if (mode.apiValue.startsWith(expertChatModePrefix)) {
      return l10n.chatModeExpertDirect;
    }
    if (mode is ChatModeTeam) {
      final team = mode as ChatModeTeam;
      final modeLabel = _formatTeamMode(team.collaborationMode);
      return l10n.chatModeTeamSummary(team.selectedAgents.length, modeLabel);
    }
    return mode.label;
  }

  String _formatTeamMode(String mode) {
    final l10n = I18nService.instance.l10n;
    switch (mode) {
      case 'parallel':
        return l10n.chatCollabParallelShort;
      case 'debate':
        return l10n.chatCollabDebateShort;
      case 'delegation':
        return l10n.chatCollabDelegationShort;
      case 'sequential':
        return l10n.chatCollabSequentialShort;
      default:
        return l10n.chatCollabAuto;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final colors = context.colorExtensions;
    final foregroundColor = colors.adaptiveTextPrimary;
    final chevronColor =
        isDark ? foregroundColor.withValues(alpha: 0.72) : DS.textSecondary;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: GestureDetector(
        onTap: onTap,
        child: MaterialStyler(
          material: AppMaterials.neoGlass.copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                mode.color.withValues(alpha: 0.18),
                mode.color.withValues(alpha: 0.08),
              ],
            ),
            borderColor: mode.color.withValues(alpha: 0.35),
          ),
          borderRadius: DS.borderRadius20,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                mode.icon,
                size: DS.iconSizeSm,
                color: foregroundColor,
              ),
              const SizedBox(width: DS.spacing6),
              ConstrainedBox(
                constraints: BoxConstraints(
                  maxWidth: mode is ChatModeTeam
                      ? 140
                      : (mode.apiValue.startsWith(expertChatModePrefix)
                          ? 84
                          : 120),
                ),
                child: Text(
                  _displayLabel,
                  style: TextStyle(
                    color: foregroundColor,
                    fontSize: DS.fontSizeSm,
                    fontWeight: DS.fontWeightMedium,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: DS.spacing4),
              Icon(
                Icons.keyboard_arrow_down_rounded,
                size: DS.iconSizeSm,
                color: chevronColor,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
