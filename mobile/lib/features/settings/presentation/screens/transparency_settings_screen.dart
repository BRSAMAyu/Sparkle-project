import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/user_preferences_service.dart';

part 'transparency_settings_screen.g.dart';

/// Transparency Settings Screen
/// 透明模式设置屏幕
class TransparencySettingsScreen extends ConsumerWidget {
  const TransparencySettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preferences = ref.watch(transparencyPreferencesProvider);

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

              // Detailed options
              if (prefs.enabled) ...[
                Text(
                  context.l10n.transparencyDisplayOptions,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: DS.sm),
                GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: Column(
                    children: [
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

/// Transparency preferences model
class TransparencyPreferences {
  const TransparencyPreferences({
    required this.enabled,
    required this.showTokenUsage,
    required this.showAgentSwitching,
    required this.showReasoningSteps,
  });

  factory TransparencyPreferences.fromJson(Map<String, dynamic> json) =>
      TransparencyPreferences(
        enabled: json['enabled'] as bool? ?? false,
        showTokenUsage: json['showTokenUsage'] as bool? ?? true,
        showAgentSwitching: json['showAgentSwitching'] as bool? ?? true,
        showReasoningSteps: json['showReasoningSteps'] as bool? ?? true,
      );

  final bool enabled;
  final bool showTokenUsage;
  final bool showAgentSwitching;
  final bool showReasoningSteps;

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'showTokenUsage': showTokenUsage,
        'showAgentSwitching': showAgentSwitching,
        'showReasoningSteps': showReasoningSteps,
      };

  TransparencyPreferences copyWith({
    bool? enabled,
    bool? showTokenUsage,
    bool? showAgentSwitching,
    bool? showReasoningSteps,
  }) =>
      TransparencyPreferences(
        enabled: enabled ?? this.enabled,
        showTokenUsage: showTokenUsage ?? this.showTokenUsage,
        showAgentSwitching: showAgentSwitching ?? this.showAgentSwitching,
        showReasoningSteps: showReasoningSteps ?? this.showReasoningSteps,
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
        );
    await _updatePreferences(current.copyWith(showReasoningSteps: value));
  }

  @override
  Future<TransparencyPreferences> build() async {
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
    );
  }
}
