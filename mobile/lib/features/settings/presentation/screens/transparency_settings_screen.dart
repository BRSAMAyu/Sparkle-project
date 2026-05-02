import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/user_preferences_service.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

part 'transparency_settings_screen.g.dart';

enum TransparencyDisplayMode {
  collapsedFloating,
  bottomSheet,
  detailOnly,
}

String _settingsCopy({required String zh, required String en}) =>
    I18nService.instance.isChinese ? zh : en;

/// Transparency Settings Screen
/// 透明模式设置屏幕
class TransparencySettingsScreen extends ConsumerWidget {
  const TransparencySettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preferences = ref.watch(transparencyPreferencesNotifierProvider);
    final pureModeEnabled = ref.watch(chatPureModeProvider);

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: Text(context.l10n.transparencySettingsTitle),
      ),
      child: preferences.when(
        data: (prefs) => ContentConstraint(
          child: ListView(
            padding: const EdgeInsets.all(DS.md),
            children: [
              // Global toggle
              GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: SwitchListTile(
                  title: Text(context.l10n.transparencyEnable),
                  subtitle: Text(
                    context.l10n.transparencyEnableDesc,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  value: prefs.enabled,
                  onChanged: (value) {
                    unawaited(
                      ref
                          .read(
                            transparencyPreferencesNotifierProvider.notifier,
                          )
                          .setEnabled(value),
                    );
                  },
                ),
              ),
              const SizedBox(height: DS.md),
              GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: SwitchListTile(
                  title: Text(context.l10n.settingsPureMode),
                  subtitle: Text(
                    '聊天中仅保留文字消息，隐藏消息下方的附加信息卡片、任务卡和反馈组件。',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  value: pureModeEnabled,
                  onChanged: (value) {
                    unawaited(
                      ref.read(chatPureModeProvider.notifier).setEnabled(value),
                    );
                  },
                ),
              ),
              const SizedBox(height: DS.md),

              // Detailed options
              if (prefs.enabled) ...[
                Text(
                  context.l10n.transparencyDisplayOptions,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: DS.sm),
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: Column(
                    children: [
                      ListTile(
                        title: Text(context.l10n.transparencyDisplayOptions),
                        subtitle: Text(
                          '选择主对话里的透明模式展示方式',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        trailing: DropdownButton<TransparencyDisplayMode>(
                          value: prefs.displayMode,
                          onChanged: (value) {
                            if (value == null) return;
                            unawaited(
                              ref
                                  .read(
                                    transparencyPreferencesNotifierProvider
                                        .notifier,
                                  )
                                  .setDisplayMode(value),
                            );
                          },
                          items: [
                            DropdownMenuItem(
                              value: TransparencyDisplayMode.collapsedFloating,
                              child:
                                  Text(context.l10n.settingsCollapseFloating),
                            ),
                            DropdownMenuItem(
                              value: TransparencyDisplayMode.bottomSheet,
                              child: Text(context.l10n.settingsBottomDrawer),
                            ),
                            DropdownMenuItem(
                              value: TransparencyDisplayMode.detailOnly,
                              child: Text(context.l10n.settingsDetailOnly),
                            ),
                          ],
                        ),
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: Text(context.l10n.settingsAutoCollapse),
                        subtitle: Text(
                          '回答完成后，将透明模式收起成轻量摘要',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        value: prefs.autoCollapseOnComplete,
                        onChanged: (value) {
                          unawaited(
                            ref
                                .read(
                                  transparencyPreferencesNotifierProvider
                                      .notifier,
                                )
                                .setAutoCollapseOnComplete(value),
                          );
                        },
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: Text(context.l10n.settingsAllowSingleClose),
                        subtitle: Text(
                          '本轮生成时可手动关闭透明模式，不影响回答继续生成',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        value: prefs.allowPerTurnDismiss,
                        onChanged: (value) {
                          unawaited(
                            ref
                                .read(
                                  transparencyPreferencesNotifierProvider
                                      .notifier,
                                )
                                .setAllowPerTurnDismiss(value),
                          );
                        },
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: Text(context.l10n.transparencyTokenUsage),
                        subtitle: Text(
                          context.l10n.transparencyTokenUsageDesc,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        value: prefs.showTokenUsage,
                        onChanged: (value) {
                          unawaited(
                            ref
                                .read(
                                  transparencyPreferencesNotifierProvider
                                      .notifier,
                                )
                                .setShowTokenUsage(value),
                          );
                        },
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: Text(context.l10n.transparencyAgentSwitching),
                        subtitle: Text(
                          context.l10n.transparencyAgentSwitchingDesc,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        value: prefs.showAgentSwitching,
                        onChanged: (value) {
                          unawaited(
                            ref
                                .read(
                                  transparencyPreferencesNotifierProvider
                                      .notifier,
                                )
                                .setShowAgentSwitching(value),
                          );
                        },
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: Text(context.l10n.transparencyReasoningSteps),
                        subtitle: Text(
                          context.l10n.transparencyReasoningStepsDesc,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        value: prefs.showReasoningSteps,
                        onChanged: (value) {
                          unawaited(
                            ref
                                .read(
                                  transparencyPreferencesNotifierProvider
                                      .notifier,
                                )
                                .setShowReasoningSteps(value),
                          );
                        },
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: Text(
                          _settingsCopy(
                            zh: 'Aurora 体验回执',
                            en: 'Aurora experience receipts',
                          ),
                        ),
                        subtitle: Text(
                          _settingsCopy(
                            zh: '显示 Aurora 为什么改变语气、状态或深度校准入口。',
                            en: 'Show why Aurora changed tone, state, or deep calibration entry.',
                          ),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        value: prefs.showAuroraExperienceReceipts,
                        onChanged: (value) {
                          unawaited(
                            ref
                                .read(
                                  transparencyPreferencesNotifierProvider
                                      .notifier,
                                )
                                .setShowAuroraExperienceReceipts(value),
                          );
                        },
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: Text(
                          _settingsCopy(
                            zh: '记忆引用回执',
                            en: 'Memory reference receipts',
                          ),
                        ),
                        subtitle: Text(
                          _settingsCopy(
                            zh: '显示 Aurora 引用了哪些相关记忆，并允许纠正。',
                            en: 'Show which memories Aurora used and allow corrections.',
                          ),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        value: prefs.showMemoryReferenceReceipts,
                        onChanged: (value) {
                          unawaited(
                            ref
                                .read(
                                  transparencyPreferencesNotifierProvider
                                      .notifier,
                                )
                                .setShowMemoryReferenceReceipts(value),
                          );
                        },
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: Text(
                          _settingsCopy(
                            zh: '资料与工具回执',
                            en: 'Source and tool receipts',
                          ),
                        ),
                        subtitle: Text(
                          _settingsCopy(
                            zh: '显示 Aurora 参考了哪些资料、工具或社群上下文。',
                            en: 'Show which materials, tools, or social context Aurora used.',
                          ),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        value: prefs.showSourceContextReceipts,
                        onChanged: (value) {
                          unawaited(
                            ref
                                .read(
                                  transparencyPreferencesNotifierProvider
                                      .notifier,
                                )
                                .setShowSourceContextReceipts(value),
                          );
                        },
                      ),
                      const Divider(height: 1),
                      SwitchListTile(
                        title: Text(
                          _settingsCopy(
                            zh: '下一步变更回执',
                            en: 'Next-action change receipts',
                          ),
                        ),
                        subtitle: Text(
                          _settingsCopy(
                            zh: '显示计划或任务被 Aurora 调整的原因。',
                            en: 'Show why Aurora changed a plan or task.',
                          ),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        value: prefs.showNextActionChangedReceipts,
                        onChanged: (value) {
                          unawaited(
                            ref
                                .read(
                                  transparencyPreferencesNotifierProvider
                                      .notifier,
                                )
                                .setShowNextActionChangedReceipts(value),
                          );
                        },
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: DS.lg),

                // Performance warning
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.accent,
                  child: Padding(
                    padding: const EdgeInsets.all(DS.md),
                    child: Row(
                      children: [
                        Icon(
                          Icons.info_outline,
                          color: DS.warning,
                        ),
                        const SizedBox(width: DS.spacing12),
                        Expanded(
                          child: Text(
                            context.l10n.transparencyWarning,
                            style: Theme.of(context)
                                .textTheme
                                .bodyMedium
                                ?.copyWith(
                                  color: DS.warning,
                                ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 64, color: DS.error),
              const SizedBox(height: DS.md),
              Text(
                context.l10n.transparencyLoadFailed,
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: DS.sm),
              Text(
                error.toString(),
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Safely parse [TransparencyDisplayMode] from a stored string.
/// Returns [TransparencyDisplayMode.collapsedFloating] for unknown values.
TransparencyDisplayMode _safeDisplayMode(String name) =>
    TransparencyDisplayMode.values.firstWhere(
      (e) => e.name == name,
      orElse: () => TransparencyDisplayMode.collapsedFloating,
    );

/// Transparency preferences model
class TransparencyPreferences {
  const TransparencyPreferences({
    required this.enabled,
    required this.showTokenUsage,
    required this.showAgentSwitching,
    required this.showReasoningSteps,
    required this.displayMode,
    required this.autoCollapseOnComplete,
    required this.allowPerTurnDismiss,
    this.showAuroraExperienceReceipts = true,
    this.showMemoryReferenceReceipts = true,
    this.showSourceContextReceipts = true,
    this.showNextActionChangedReceipts = true,
  });

  factory TransparencyPreferences.fromJson(Map<String, dynamic> json) =>
      TransparencyPreferences(
        enabled: json['enabled'] as bool? ?? false,
        showTokenUsage: json['showTokenUsage'] as bool? ?? true,
        showAgentSwitching: json['showAgentSwitching'] as bool? ?? true,
        showReasoningSteps: json['showReasoningSteps'] as bool? ?? true,
        displayMode: _safeDisplayMode(
          json['displayMode'] as String? ?? 'collapsedFloating',
        ),
        autoCollapseOnComplete: json['autoCollapseOnComplete'] as bool? ?? true,
        allowPerTurnDismiss: json['allowPerTurnDismiss'] as bool? ?? true,
        showAuroraExperienceReceipts:
            json['showAuroraExperienceReceipts'] as bool? ?? true,
        showMemoryReferenceReceipts:
            json['showMemoryReferenceReceipts'] as bool? ?? true,
        showSourceContextReceipts:
            json['showSourceContextReceipts'] as bool? ?? true,
        showNextActionChangedReceipts:
            json['showNextActionChangedReceipts'] as bool? ?? true,
      );

  final bool enabled;
  final bool showTokenUsage;
  final bool showAgentSwitching;
  final bool showReasoningSteps;
  final TransparencyDisplayMode displayMode;
  final bool autoCollapseOnComplete;
  final bool allowPerTurnDismiss;
  final bool showAuroraExperienceReceipts;
  final bool showMemoryReferenceReceipts;
  final bool showSourceContextReceipts;
  final bool showNextActionChangedReceipts;

  Set<String> get enabledReceiptTypes => {
        if (showAuroraExperienceReceipts) 'aurora_experience_receipt',
        if (showMemoryReferenceReceipts) 'memory_reference_receipt',
        if (showSourceContextReceipts) 'source_context_receipt',
        if (showNextActionChangedReceipts) 'next_action_changed_by_aurora',
      };

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'showTokenUsage': showTokenUsage,
        'showAgentSwitching': showAgentSwitching,
        'showReasoningSteps': showReasoningSteps,
        'displayMode': displayMode.name,
        'autoCollapseOnComplete': autoCollapseOnComplete,
        'allowPerTurnDismiss': allowPerTurnDismiss,
        'showAuroraExperienceReceipts': showAuroraExperienceReceipts,
        'showMemoryReferenceReceipts': showMemoryReferenceReceipts,
        'showSourceContextReceipts': showSourceContextReceipts,
        'showNextActionChangedReceipts': showNextActionChangedReceipts,
      };

  TransparencyPreferences copyWith({
    bool? enabled,
    bool? showTokenUsage,
    bool? showAgentSwitching,
    bool? showReasoningSteps,
    TransparencyDisplayMode? displayMode,
    bool? autoCollapseOnComplete,
    bool? allowPerTurnDismiss,
    bool? showAuroraExperienceReceipts,
    bool? showMemoryReferenceReceipts,
    bool? showSourceContextReceipts,
    bool? showNextActionChangedReceipts,
  }) =>
      TransparencyPreferences(
        enabled: enabled ?? this.enabled,
        showTokenUsage: showTokenUsage ?? this.showTokenUsage,
        showAgentSwitching: showAgentSwitching ?? this.showAgentSwitching,
        showReasoningSteps: showReasoningSteps ?? this.showReasoningSteps,
        displayMode: displayMode ?? this.displayMode,
        autoCollapseOnComplete:
            autoCollapseOnComplete ?? this.autoCollapseOnComplete,
        allowPerTurnDismiss: allowPerTurnDismiss ?? this.allowPerTurnDismiss,
        showAuroraExperienceReceipts:
            showAuroraExperienceReceipts ?? this.showAuroraExperienceReceipts,
        showMemoryReferenceReceipts:
            showMemoryReferenceReceipts ?? this.showMemoryReferenceReceipts,
        showSourceContextReceipts:
            showSourceContextReceipts ?? this.showSourceContextReceipts,
        showNextActionChangedReceipts:
            showNextActionChangedReceipts ?? this.showNextActionChangedReceipts,
      );
}

/// Provider for transparency preferences
@riverpod
Future<TransparencyPreferences> transparencyPreferences(Ref ref) async {
  final service = ref.watch(userPreferencesServiceProvider);
  final prefs = await service.getPreferences();

  final transparencyPrefs = prefs['transparency'] as Map<String, dynamic>?;

  if (transparencyPrefs != null) {
    return TransparencyPreferences.fromJson(transparencyPrefs);
  }

  // Default preferences
  return const TransparencyPreferences(
    enabled: true,
    showTokenUsage: true,
    showAgentSwitching: true,
    showReasoningSteps: true,
    displayMode: TransparencyDisplayMode.collapsedFloating,
    autoCollapseOnComplete: true,
    allowPerTurnDismiss: true,
  );
}

/// Notifier for transparency preferences
@riverpod
class TransparencyPreferencesNotifier
    extends _$TransparencyPreferencesNotifier {
  Future<void> _updatePreferences(TransparencyPreferences prefs) async {
    state = AsyncValue.data(prefs);

    final service = ref.read(userPreferencesServiceProvider);
    await service.updatePreferences({
      'transparency': prefs.toJson(),
    });
  }

  Future<void> setEnabled(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(current.copyWith(enabled: value));
  }

  Future<void> setShowTokenUsage(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(current.copyWith(showTokenUsage: value));
  }

  Future<void> setShowAgentSwitching(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(current.copyWith(showAgentSwitching: value));
  }

  Future<void> setShowReasoningSteps(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(current.copyWith(showReasoningSteps: value));
  }

  Future<void> setShowAuroraExperienceReceipts(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(
      current.copyWith(showAuroraExperienceReceipts: value),
    );
  }

  Future<void> setShowMemoryReferenceReceipts(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(
      current.copyWith(showMemoryReferenceReceipts: value),
    );
  }

  Future<void> setShowSourceContextReceipts(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(
      current.copyWith(showSourceContextReceipts: value),
    );
  }

  Future<void> setShowNextActionChangedReceipts(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(
      current.copyWith(showNextActionChangedReceipts: value),
    );
  }

  Future<void> setDisplayMode(TransparencyDisplayMode value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(current.copyWith(displayMode: value));
  }

  Future<void> setAutoCollapseOnComplete(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(current.copyWith(autoCollapseOnComplete: value));
  }

  Future<void> setAllowPerTurnDismiss(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: true,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
          displayMode: TransparencyDisplayMode.collapsedFloating,
          autoCollapseOnComplete: true,
          allowPerTurnDismiss: true,
        );
    await _updatePreferences(current.copyWith(allowPerTurnDismiss: value));
  }

  @override
  Future<TransparencyPreferences> build() async {
    try {
      final service = ref.watch(userPreferencesServiceProvider);
      final prefs = await service.getPreferences();

      final transparencyPrefs = prefs['transparency'] as Map<String, dynamic>?;

      if (transparencyPrefs != null) {
        return TransparencyPreferences.fromJson(transparencyPrefs);
      }

      return const TransparencyPreferences(
        enabled: true,
        showTokenUsage: true,
        showAgentSwitching: true,
        showReasoningSteps: true,
        displayMode: TransparencyDisplayMode.collapsedFloating,
        autoCollapseOnComplete: true,
        allowPerTurnDismiss: true,
      );
    } catch (error, stackTrace) {
      Error.throwWithStackTrace(error, stackTrace);
    }
  }
}
