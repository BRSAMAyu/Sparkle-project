import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class AiReasoningModePill extends ConsumerWidget {
  const AiReasoningModePill({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(aiReasoningModeProvider);
    final config = _ReasoningModeVisuals.fromMode(mode);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: Semantics(
        button: true,
        label: 'Chat ai reasoning mode pill control 1',
        child: GestureDetector(
          onTap: () => _showReasoningModeSheet(context, ref, mode),
          child: MaterialStyler(
            material: AppMaterials.neoGlass(context).copyWith(
              backgroundGradient: LinearGradient(
                colors: [
                  config.color.withValues(alpha: 0.18),
                  config.color.withValues(alpha: 0.08),
                ],
              ),
              borderColor: config.color.withValues(alpha: 0.35),
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
                  config.icon,
                  size: DS.iconSizeSm,
                  color: config.color,
                ),
                const SizedBox(width: DS.spacing6),
                Text(
                  config.label,
                  style: DS.bodySmall.copyWith(
                    color: DS.textPrimary,
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
      ),
    );
  }

  void _showReasoningModeSheet(
    BuildContext context,
    WidgetRef ref,
    String currentMode,
  ) {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        isScrollControlled: true,
        builder: (_) => _AiReasoningModeSheet(currentMode: currentMode),
      ),
    );
  }
}

class _AiReasoningModeSheet extends ConsumerWidget {
  const _AiReasoningModeSheet({required this.currentMode});

  final String currentMode;

  Future<void> _selectMode(
    BuildContext context,
    WidgetRef ref,
    String mode,
  ) async {
    await ref.read(aiReasoningModeProvider.notifier).setMode(mode);
    if (context.mounted) {
      Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    const modes = ['fast', 'balanced', 'deep'];

    return Container(
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: const BorderRadius.vertical(
          top: Radius.circular(28),
        ),
      ),
      padding: EdgeInsets.only(
        left: DS.spacing16,
        right: DS.spacing16,
        top: DS.spacing16,
        bottom: DS.spacing16 + MediaQuery.of(context).padding.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.chatModeAiGear,
            style: (Theme.of(context).textTheme.titleMedium ?? DS.bodyLarge)
                .copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            context.l10n.chatModeSwitchStrategy,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing16),
          ...modes.map(
            (mode) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing10),
              child: _ReasoningModeOption(
                config: _ReasoningModeVisuals.fromMode(mode),
                selected: currentMode == mode,
                onTap: () => unawaited(_selectMode(context, ref, mode)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ReasoningModeOption extends StatelessWidget {
  const _ReasoningModeOption({
    required this.config,
    required this.selected,
    required this.onTap,
  });

  final _ReasoningModeVisuals config;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Colors.transparent,
        child: Semantics(
          button: true,
          label: 'Chat ai reasoning mode pill control 2',
          child: InkWell(
            borderRadius: DS.borderRadius20,
            onTap: onTap,
            child: Ink(
              decoration: BoxDecoration(
                color: selected
                    ? config.color.withValues(alpha: 0.10)
                    : DS.surfaceSecondary,
                borderRadius: DS.borderRadius20,
                border: Border.all(
                  color: selected
                      ? config.color.withValues(alpha: 0.45)
                      : DS.borderSubtle,
                ),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing12,
                  vertical: DS.spacing12,
                ),
                child: Row(
                  children: [
                    Container(
                      width: 34,
                      height: 34,
                      decoration: BoxDecoration(
                        color: config.color.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(
                        config.icon,
                        size: DS.iconSizeSm,
                        color: config.color,
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            config.label,
                            style: DS.bodyMedium.copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightSemibold,
                            ),
                          ),
                          const SizedBox(height: DS.spacing2),
                          Text(
                            config.caption,
                            style: DS.bodySmall.copyWith(
                              color: DS.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    if (selected)
                      Icon(
                        Icons.check_circle_rounded,
                        size: DS.iconSizeBase,
                        color: config.color,
                      )
                    else
                      Icon(
                        Icons.radio_button_unchecked_rounded,
                        size: DS.iconSizeBase,
                        color: DS.textTertiary,
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}

class _ReasoningModeVisuals {
  const _ReasoningModeVisuals({
    required this.label,
    required this.caption,
    required this.icon,
    required this.color,
  });

  factory _ReasoningModeVisuals.fromMode(String mode) {
    switch (mode) {
      case 'fast':
        return _ReasoningModeVisuals(
          label: I18nService.instance.isChinese ? '敏捷' : 'Fast',
          caption: S.chatModeFastDesc,
          icon: Icons.flash_on_rounded,
          color: DS.warning,
        );
      case 'deep':
        return _ReasoningModeVisuals(
          label: I18nService.instance.isChinese ? '深思' : 'Deep',
          caption: S.chatModeStrongAnalysisDesc,
          icon: Icons.psychology_alt_rounded,
          color: DS.info,
        );
      case 'balanced':
      default:
        return _ReasoningModeVisuals(
          label: I18nService.instance.isChinese ? '均衡' : 'Balanced',
          caption: S.chatModeBalancedDesc,
          icon: Icons.tune_rounded,
          color: DS.success,
        );
    }
  }

  final String label;
  final String caption;
  final IconData icon;
  final Color color;
}
