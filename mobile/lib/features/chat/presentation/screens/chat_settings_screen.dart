import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/seed_library/presentation/providers/seed_library_provider.dart';
import 'package:sparkle/features/settings/presentation/providers/transparency_preferences.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

const _defaultAiSystemPreferences = TransparencyPreferences(
  enabled: true,
  showTokenUsage: true,
  showAgentSwitching: true,
  showReasoningSteps: true,
  displayMode: TransparencyDisplayMode.collapsedFloating,
  autoCollapseOnComplete: true,
  allowPerTurnDismiss: true,
);

class ChatSettingsScreen extends ConsumerWidget {
  const ChatSettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preferences =
        ref.watch(transparencyPreferencesNotifierProvider).valueOrNull ??
            _defaultAiSystemPreferences;
    final notifier = ref.read(transparencyPreferencesNotifierProvider.notifier);
    final showChatContextToggle = ref.watch(showChatContextToggleProvider);
    final showChatPredictionDock = ref.watch(showChatPredictionDockProvider);
    final showChatTransparencyCapsule =
        ref.watch(showChatTransparencyCapsuleProvider);
    final chatPureMode = ref.watch(chatPureModeProvider);
    final seedLibraryEnabled = ref.watch(chatSeedLibraryEnabledProvider);
    final subscriptionState = ref.watch(subscriptionsProvider);

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: Text(context.l10n.chatSettingsTitle),
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.md),
          children: [
            GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              child: Padding(
                padding: const EdgeInsets.all(DS.md),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(DS.spacing10),
                      decoration: BoxDecoration(
                        color: DS.surfaceOverlay,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: DS.borderSubtle),
                      ),
                      child: Icon(
                        Icons.tune_rounded,
                        color: DS.primaryBase,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.l10n.chatSettingsExperience,
                            style: DS.titleLarge.copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightBold,
                            ),
                          ),
                          const SizedBox(height: DS.spacing4),
                          Text(
                            context.l10n.chatSettingsExperienceDesc,
                            style: DS.bodySmall.copyWith(
                              color: DS.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.md),
            Text(
              context.l10n.chatSettingsSeedLibrary,
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.sm),
            GraphiteCardSurface(
              surfaceRole: SparkleSurfaceRole.card,
              child: Column(
                children: [
                  SwitchListTile(
                    title: Text(context.l10n.chatSettingsEnableSeedEnhancement),
                    subtitle: Text(context.l10n.chatSettingsEnableSeedDesc),
                    value: seedLibraryEnabled,
                    onChanged: (value) {
                      unawaited(
                        ref
                            .read(chatSeedLibraryEnabledProvider.notifier)
                            .setEnabled(value),
                      );
                    },
                  ),
                  // U-07：种子库浏览入口摘除（/seed-libraries 属 LABS，
                  // hidden by default）；种子增强开关保留为能力配置。
                  if (subscriptionState.error != null) ...[
                    const Divider(height: 1),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(
                        DS.md,
                        DS.sm,
                        DS.md,
                        DS.md,
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.error_outline_rounded,
                            size: 18,
                            color: DS.error,
                          ),
                          const SizedBox(width: DS.spacing8),
                          Expanded(
                            child: Text(
                              uiErrorMessage(context.l10n, subscriptionState.error!),
                              style: DS.bodySmall.copyWith(color: DS.error),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: DS.lg),
            Text(
              context.l10n.chatSettingsUiCapabilities,
              style: DS.titleMedium.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: context.l10n.chatSettingsShowAiPanel,
              subtitle: context.l10n.chatSettingsShowAiPanelDesc,
              value: preferences.enabled,
              onChanged: notifier.setEnabled,
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: context.l10n.chatSettingsPureMode,
              subtitle: context.l10n.chatSettingsPureModeDesc,
              value: chatPureMode,
              onChanged: (value) =>
                  ref.read(chatPureModeProvider.notifier).setEnabled(value),
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: context.l10n.chatSettingsShowTopBar,
              subtitle: context.l10n.chatSettingsShowTopBarDesc,
              value: showChatContextToggle,
              onChanged: (value) => ref
                  .read(showChatContextToggleProvider.notifier)
                  .setEnabled(value),
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: context.l10n.chatSettingsShowPrediction,
              subtitle: context.l10n.chatSettingsShowPredictionDesc,
              value: showChatPredictionDock,
              onChanged: (value) => ref
                  .read(showChatPredictionDockProvider.notifier)
                  .setEnabled(value),
            ),
            const SizedBox(height: DS.sm),
            _SettingsToggleCard(
              title: context.l10n.chatSettingsShowTransparencyCapsule,
              subtitle: context.l10n.chatSettingsShowTransparencyDesc,
              value: showChatTransparencyCapsule,
              onChanged: (value) => ref
                  .read(showChatTransparencyCapsuleProvider.notifier)
                  .setEnabled(value),
            ),
            if (preferences.enabled) ...[
              const SizedBox(height: DS.lg),
              Text(
                context.l10n.chatSettingsTransparencyDetails,
                style: DS.titleMedium.copyWith(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.sm),
              _SettingsToggleCard(
                title: context.l10n.chatSettingsShowTokenCost,
                subtitle: context.l10n.chatSettingsShowTokenCostDesc,
                value: preferences.showTokenUsage,
                onChanged: notifier.setShowTokenUsage,
              ),
              const SizedBox(height: DS.sm),
              _SettingsToggleCard(
                title: context.l10n.chatSettingsShowAgentCollab,
                subtitle: context.l10n.chatSettingsShowAgentCollabDesc,
                value: preferences.showAgentSwitching,
                onChanged: notifier.setShowAgentSwitching,
              ),
              const SizedBox(height: DS.sm),
              _SettingsToggleCard(
                title: context.l10n.chatSettingsShowReasoningTimeline,
                subtitle: context.l10n.chatSettingsShowReasoningDesc,
                value: preferences.showReasoningSteps,
                onChanged: notifier.setShowReasoningSteps,
              ),
            ],
              // NAV-IA P-1：原「打开高级设置」入口（push 未注册的透明度设置
              // 路由）已移除——点击必落 404 errorBuilder。半成品入口不为主干
              // 背书；l10n arb 键（chatSettingsOpenAdvanced*）保留以防产品
              // 确认后恢复入口时回滚。
          ],
        ),
      ),
    );
  }
}

class _SettingsToggleCard extends StatelessWidget {
  const _SettingsToggleCard({
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: SwitchListTile(
          title: Text(title),
          subtitle: Text(subtitle),
          value: value,
          onChanged: onChanged,
        ),
      );
}
