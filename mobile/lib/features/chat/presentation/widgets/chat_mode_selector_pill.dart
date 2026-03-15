import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
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
    HapticFeedback.lightImpact();
    unawaited(
      showModalBottomSheet<ChatMode>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        isScrollControlled: true,
        builder: (context) => const ChatModeSelectorSheet(),
      ).then((selectedMode) {
        if (selectedMode != null) {
          ref.read(chatModeNotifierProvider.notifier).setMode(selectedMode);
          // Also update last multi-agent mode if not standard
          if (selectedMode.apiValue != 'standard') {
            ref.read(lastMultiAgentModeProvider.notifier).state = selectedMode;
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
                '选择模式',
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
    if (mode.apiValue.startsWith(expertChatModePrefix)) {
      return '专家直达';
    }
    return mode.label;
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final foregroundColor = isDark ? const Color(0xFFF1E7DA) : DS.textPrimary;
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
                  maxWidth:
                      mode.apiValue.startsWith(expertChatModePrefix) ? 84 : 120,
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
