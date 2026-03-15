import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/core/utils/chaos/chaos_control_dialog.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/capsule/capsule_generation_preview.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/widgets/learning_mode_control.dart';
import 'package:sparkle/features/user/presentation/widgets/preference_controller_2d.dart';
import 'package:sparkle/features/user/presentation/widgets/weekly_agenda_grid.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class UnifiedSettingsScreen extends ConsumerStatefulWidget {
  const UnifiedSettingsScreen({super.key});

  @override
  ConsumerState<UnifiedSettingsScreen> createState() =>
      _UnifiedSettingsScreenState();
}

class _UnifiedSettingsScreenState extends ConsumerState<UnifiedSettingsScreen> {
  bool _isGenerating = false;
  bool _weeklyAgendaExpanded = false;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final enterToSend = ref.watch(enterToSendProvider);
    final transparentMode = ref.watch(transparentModeProvider);
    final transparencyLevel = ref.watch(transparencyLevelProvider);
    final systemUpdateLevel = ref.watch(systemUpdateLevelProvider);
    final learningPrefs = ref.watch(learningPreferencesProvider);
    final pushPrefs = ref.watch(pushPreferencesProvider);
    final weeklyAgenda = ref.watch(weeklyAgendaProvider);

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(l10n.schedulePreferences),
        actions: [
          SparkleButton.ghost(
            label: l10n.confirm,
            onPressed: () {
              if (context.mounted) {
                context.pop();
              }
            },
          ),
        ],
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSectionHeader(Icons.psychology, l10n.learningMode),
                    const SizedBox(height: DS.spacing16),
                    Text(
                      l10n.dragToAdjust,
                      style: TextStyle(
                        color: DS.brandPrimaryConst,
                        fontSize: DS.fontSizeSm,
                      ),
                    ),
                    const SizedBox(height: DS.spacing16),
                    LearningModeControl(
                      depth: learningPrefs.depth,
                      curiosity: learningPrefs.curiosity,
                      onChanged: (d, c) {
                        ref
                            .read(learningPreferencesProvider.notifier)
                            .updatePreferences(
                              depth: d,
                              curiosity: c,
                            );
                      },
                    ),
                    const SizedBox(height: DS.spacing32),
                    _buildSectionHeader(
                      Icons.auto_awesome,
                      l10n.capsuleGeneration,
                    ),
                    const SizedBox(height: DS.spacing16),
                    Text(
                      l10n.adjustAndGenerate,
                      style: TextStyle(
                        color: DS.brandPrimaryConst,
                        fontSize: DS.fontSizeSm,
                      ),
                    ),
                    const SizedBox(height: DS.spacing16),
                    PreferenceController2D(
                      initialDepth: learningPrefs.depth,
                      initialCuriosity: learningPrefs.curiosity,
                      onPreferenceChanged: (offset) {
                        ref
                            .read(learningPreferencesProvider.notifier)
                            .updatePreferences(
                              depth: offset.dy,
                              curiosity: offset.dx,
                            );
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    CapsuleGenerationPreview(
                      depthPreference: learningPrefs.depth,
                      curiosityPreference: learningPrefs.curiosity,
                    ),
                    const SizedBox(height: DS.spacing16),
                    SparkleButton(
                      expand: true,
                      label: _isGenerating ? l10n.generating : l10n.generateNow,
                      icon:
                          _isGenerating ? null : const Icon(Icons.auto_awesome),
                      onPressed: _isGenerating
                          ? null
                          : () {
                              unawaited(
                                _requestCapsuleGeneration(context, l10n),
                              );
                            },
                      loading: _isGenerating,
                    ),
                    const SizedBox(height: DS.spacing32),
                    _buildSectionHeader(Icons.schedule, l10n.weeklyAgenda),
                    const SizedBox(height: DS.spacing16),
                    _buildWeeklyAgendaSection(
                      context,
                      l10n,
                      weeklyAgenda,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              GraphiteCardSurface(
                child: Column(
                  children: [
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.brightness_6_outlined),
                      title: Text(l10n.theme),
                      subtitle: Text('${l10n.lightMode}/${l10n.darkMode}'),
                      trailing: DropdownButton<AppThemeMode>(
                        value: ref.watch(appThemeModeProvider),
                        underline: const SizedBox.shrink(),
                        onChanged: (AppThemeMode? newValue) {
                          if (newValue != null) {
                            ref
                                .read(themeManagerProvider)
                                .setAppThemeMode(newValue);
                          }
                        },
                        items: [
                          DropdownMenuItem(
                            value: AppThemeMode.system,
                            child: Text(l10n.followSystem),
                          ),
                          DropdownMenuItem(
                            value: AppThemeMode.light,
                            child: Text(l10n.lightMode),
                          ),
                          DropdownMenuItem(
                            value: AppThemeMode.dark,
                            child: Text(l10n.darkMode),
                          ),
                        ],
                      ),
                    ),
                    const Divider(height: DS.spacing24),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l10n.enterToSend),
                      subtitle: Text(l10n.enterToSendDescription),
                      value: enterToSend,
                      onChanged: (v) =>
                          ref.read(enterToSendProvider.notifier).setEnabled(v),
                      activeThumbColor: DS.primaryBase,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              GraphiteCardSurface(
                child: Column(
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l10n.enableNotifications),
                      subtitle: Text(l10n.notificationReceiveSmartPush),
                      value: pushPrefs.enableCuriosity,
                      onChanged: (v) {
                        ref
                            .read(pushPreferencesProvider.notifier)
                            .toggleEnableCuriosity();
                      },
                      activeThumbColor: DS.primaryBase,
                    ),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l10n.smartReminders),
                      subtitle: Text(l10n.pushMicroTasks),
                      value: pushPrefs.dailyCap > 0,
                      onChanged: (v) {
                        ref
                            .read(pushPreferencesProvider.notifier)
                            .updatePreferences(
                              dailyCap: v ? 5 : 0,
                            );
                      },
                      activeThumbColor: DS.primaryBase,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              GraphiteCardSurface(
                child: Column(
                  children: [
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l10n.enableTransparentMode),
                      subtitle: Text(l10n.showStatusOverview),
                      value: transparentMode,
                      onChanged: (v) => ref
                          .read(transparencyLevelProvider.notifier)
                          .setLevel(v ? 2 : 0),
                      activeThumbColor: DS.primaryBase,
                    ),
                    if (transparentMode) ...[
                      const SizedBox(height: DS.spacing8),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(l10n.transparencyLevel),
                        subtitle: Text(
                          '${l10n.basic}/${l10n.standard}/${l10n.advanced}',
                        ),
                        trailing: DropdownButton<int>(
                          value: transparencyLevel,
                          underline: const SizedBox.shrink(),
                          onChanged: (level) {
                            if (level != null) {
                              ref
                                  .read(transparencyLevelProvider.notifier)
                                  .setLevel(level);
                            }
                          },
                          items: [
                            DropdownMenuItem(
                              value: 0,
                              child: Text(l10n.cancel),
                            ),
                            DropdownMenuItem(
                              value: 1,
                              child: Text(l10n.basic),
                            ),
                            DropdownMenuItem(
                              value: 2,
                              child: Text(l10n.standard),
                            ),
                            DropdownMenuItem(
                              value: 3,
                              child: Text(l10n.advanced),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const Divider(height: DS.spacing24),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l10n.systemFeedback),
                      subtitle: Text(l10n.controlUpdateDetails),
                      trailing: DropdownButton<int>(
                        value: systemUpdateLevel,
                        underline: const SizedBox.shrink(),
                        onChanged: (level) {
                          if (level != null) {
                            ref
                                .read(systemUpdateLevelProvider.notifier)
                                .setLevel(level);
                          }
                        },
                        items: [
                          DropdownMenuItem(value: 0, child: Text(l10n.silent)),
                          DropdownMenuItem(
                            value: 1,
                            child: Text(l10n.summary),
                          ),
                          DropdownMenuItem(
                            value: 2,
                            child: Text(l10n.detailed),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              GraphiteCardSurface(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.sync),
                  title: Text(l10n.syncCenter),
                  subtitle: Text(l10n.viewOfflineQueue),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push(UserRoutes.syncCenter),
                ),
              ),
              const SizedBox(height: DS.spacing64),
              Center(
                child: GestureDetector(
                  onLongPress: () {
                    showDialog<void>(
                      context: context,
                      builder: (context) => const ChaosControlDialog(),
                    );
                  },
                  child: Text(
                    l10n.version,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontSize: DS.fontSizeXs,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing32),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _requestCapsuleGeneration(
    BuildContext context,
    AppLocalizations l10n,
  ) async {
    setState(() => _isGenerating = true);

    try {
      final notifier = ref.read(generationJobsProvider.notifier);
      final learningPrefs = ref.read(learningPreferencesProvider);

      // 根据好奇心偏好计算生成数量
      final requestedCount = learningPrefs.curiosity < 0.3
          ? 1
          : learningPrefs.curiosity < 0.7
              ? 2
              : 3;

      final taskId = await notifier.requestBatchGeneration(
        depthPreference: learningPrefs.depth,
        curiosityPreference: learningPrefs.curiosity,
        requestedCount: requestedCount,
      );

      if (mounted) {
        if (taskId != null) {
          AppFeedback.success(context, l10n.capsuleTaskCreated);
        } else {
          AppFeedback.error(context, l10n.generationFailed);
        }
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
            context, l10n.generationFailedWithDetail(e.toString()),);
      }
    } finally {
      if (mounted) {
        setState(() => _isGenerating = false);
      }
    }
  }

  Widget _buildSectionHeader(IconData icon, String title) => Row(
        children: [
          Icon(icon, color: DS.primaryBase, size: DS.iconSizeBase),
          const SizedBox(width: DS.spacing8),
          Text(
            title,
            style: const TextStyle(
              fontSize: DS.fontSizeLg,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ],
      );

  Widget _buildWeeklyAgendaSection(
    BuildContext context,
    AppLocalizations l10n,
    Map<String, dynamic>? weeklyAgenda,
  ) {
    final summary = _buildWeeklyAgendaSummary(l10n, weeklyAgenda);
    return AnimatedContainer(
      duration: const Duration(milliseconds: 220),
      curve: Curves.easeOutCubic,
      decoration: BoxDecoration(
        color: DS.surfaceTertiary.withValues(alpha: 0.28),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: () {
              setState(() {
                _weeklyAgendaExpanded = !_weeklyAgendaExpanded;
              });
            },
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          l10n.selectTimeSlots,
                          style: DS.labelLarge.copyWith(
                            color: DS.textPrimary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: DS.xs),
                        Text(
                          summary,
                          style: DS.bodySmall.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  AnimatedRotation(
                    turns: _weeklyAgendaExpanded ? 0.5 : 0,
                    duration: const Duration(milliseconds: 220),
                    child: Icon(
                      Icons.keyboard_arrow_down_rounded,
                      color: DS.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ),
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 220),
            firstChild: const SizedBox.shrink(),
            secondChild: Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing16,
                0,
                DS.spacing16,
                DS.spacing16,
              ),
              child: WeeklyAgendaGrid(
                initialData: weeklyAgenda,
                onChanged: (data) {
                  ref.read(weeklyAgendaProvider.notifier).updateAgenda(data);
                },
              ),
            ),
            crossFadeState: _weeklyAgendaExpanded
                ? CrossFadeState.showSecond
                : CrossFadeState.showFirst,
          ),
        ],
      ),
    );
  }

  String _buildWeeklyAgendaSummary(
    AppLocalizations l10n,
    Map<String, dynamic>? weeklyAgenda,
  ) {
    final rawGrid = weeklyAgenda?['grid'];
    if (rawGrid is! List || rawGrid.isEmpty) {
      return l10n.weeklyAgendaCollapsedHint;
    }

    final busyCount = rawGrid.where((slot) => slot == 'busy').length;
    final fragmentedCount =
        rawGrid.where((slot) => slot == 'fragmented').length;
    final activeCount = busyCount + fragmentedCount;
    if (activeCount == 0) {
      return l10n.weeklyAgendaEmptyHint;
    }
    return l10n.weeklyAgendaSummary(activeCount, busyCount, fragmentedCount);
  }
}
