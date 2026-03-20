import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/providers/locale_provider.dart';
import 'package:sparkle/core/providers/theme_provider.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/utils/chaos/chaos_control_dialog.dart';
import 'package:sparkle/features/cognitive/presentation/providers/capsule_provider.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/capsule/capsule_generation_preview.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/widgets/learning_mode_control.dart';
import 'package:sparkle/features/user/presentation/widgets/preference_controller_2d.dart';
import 'package:sparkle/features/user/presentation/widgets/weekly_agenda_grid.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/features/visual_elements/visual_elements_routes.dart';
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
  Timer? _learningPrefsDebounce;

  @override
  void dispose() {
    _learningPrefsDebounce?.cancel();
    super.dispose();
  }

  void _scheduleLearningPreferenceUpdate({
    required double depth,
    required double curiosity,
  }) {
    final notifier = ref.read(learningPreferencesProvider.notifier);
    notifier.previewPreferences(depth: depth, curiosity: curiosity);
    _learningPrefsDebounce?.cancel();
    _learningPrefsDebounce = Timer(const Duration(milliseconds: 220), () {
      notifier.updatePreferences(depth: depth, curiosity: curiosity);
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final enterToSend = ref.watch(enterToSendProvider);
    final transparentMode = ref.watch(transparentModeProvider);
    final transparencyLevel = ref.watch(transparencyLevelProvider);
    final systemUpdateLevel = ref.watch(systemUpdateLevelProvider);
    final aiReasoningMode = ref.watch(aiReasoningModeProvider);
    final aiUsageSummary = ref.watch(aiUsageSummaryProvider);
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
                        _scheduleLearningPreferenceUpdate(
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
                        _scheduleLearningPreferenceUpdate(
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
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.palette_outlined),
                  title: Text(l10n.visualElementsTitle),
                  subtitle: Text(l10n.visualElementsEntrySubtitle),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push(VisualElementsRoutes.basePath),
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
                    const Divider(height: DS.spacing24),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.tune),
                      title: const Text('AI 档位'),
                      subtitle: const Text('敏捷更快，均衡推荐，深思更强分析'),
                    ),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: [
                          ChoiceChip(
                            label: const Text('敏捷'),
                            selected: aiReasoningMode == 'fast',
                            onSelected: (_) => ref
                                .read(aiReasoningModeProvider.notifier)
                                .setMode('fast'),
                          ),
                          ChoiceChip(
                            label: const Text('均衡'),
                            selected: aiReasoningMode == 'balanced',
                            onSelected: (_) => ref
                                .read(aiReasoningModeProvider.notifier)
                                .setMode('balanced'),
                          ),
                          ChoiceChip(
                            label: const Text('深思'),
                            selected: aiReasoningMode == 'deep',
                            onSelected: (_) => ref
                                .read(aiReasoningModeProvider.notifier)
                                .setMode('deep'),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    aiUsageSummary.when(
                      data: (summary) => _buildAiUsageSummary(summary),
                      loading: () =>
                          const LinearProgressIndicator(minHeight: 3),
                      error: (_, __) => Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: DS.surfaceSecondary,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Text(
                          '额度面板暂时不可用，但档位切换仍可正常生效。',
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              // Notification permission status card
              _buildNotificationPermissionCard(context, l10n),
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
              const SizedBox(height: DS.spacing20),
              _buildSectionHeader(Icons.language_rounded, l10n.language),
              const SizedBox(height: DS.spacing12),
              GraphiteCardSurface(
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.language_rounded),
                  title: Text(l10n.language),
                  subtitle: Text(
                    ref.watch(localeProvider).languageCode == 'zh'
                        ? l10n.languageChinese
                        : l10n.languageEnglish,
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => _showLanguageDialog(context, ref, l10n),
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
          context,
          l10n.generationFailedWithDetail(e.toString()),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isGenerating = false);
      }
    }
  }

  void _showLanguageDialog(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
  ) {
    final currentLocale = ref.read(localeProvider);

    showDialog<void>(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: GraphiteModalSurface(
          title: l10n.language,
          showHandle: false,
          borderRadius: BorderRadius.circular(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                title: Text(l10n.languageChinese),
                trailing: currentLocale.languageCode == 'zh'
                    ? Icon(Icons.check, color: DS.primaryBase)
                    : null,
                onTap: () {
                  ref
                      .read(localeProvider.notifier)
                      .setLocale(const Locale('zh'));
                  Navigator.pop(context);
                },
              ),
              ListTile(
                title: Text(l10n.languageEnglish),
                trailing: currentLocale.languageCode == 'en'
                    ? Icon(Icons.check, color: DS.primaryBase)
                    : null,
                onTap: () {
                  ref
                      .read(localeProvider.notifier)
                      .setLocale(const Locale('en'));
                  Navigator.pop(context);
                },
              ),
            ],
          ),
        ),
      ),
    );
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

  Widget _buildNotificationPermissionCard(
    BuildContext context,
    AppLocalizations l10n,
  ) {
    final permissionStatus = ref.watch(notificationPermissionStatusProvider);

    return permissionStatus.when(
      loading: () => GraphiteCardSurface(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const SizedBox(
            width: 24,
            height: 24,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          title: const Text('通知权限状态'),
          subtitle: const Text('...'),
        ),
      ),
      error: (error, stack) => GraphiteCardSurface(
        child: ListTile(
          contentPadding: EdgeInsets.zero,
          leading: Icon(Icons.error_outline, color: DS.error),
          title: const Text('通知权限状态'),
          subtitle: Text('未授权: $error'),
        ),
      ),
      data: (status) {
        final hasPermission = status.hasPermission;
        final isPartial = status.hasPermission &&
            (status.alertEnabled == false ||
                status.badgeEnabled == false ||
                status.soundEnabled == false);

        Color statusColor;
        IconData statusIcon;
        String? hintText;

        if (!hasPermission) {
          statusColor = DS.error;
          statusIcon = Icons.notifications_off_outlined;
          hintText = '通知权限被拒绝，请在系统设置中开启';
        } else if (isPartial) {
          statusColor = DS.warning;
          statusIcon = Icons.notifications_active_outlined;
          hintText = '部分通知功能受限，建议开启完整权限';
        } else {
          statusColor = DS.success;
          statusIcon = Icons.notifications_active;
        }

        return GraphiteCardSurface(
          child: Column(
            children: [
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(statusIcon, color: statusColor),
                title: const Text('通知权限状态'),
                subtitle: hintText != null
                    ? Text(hintText, style: TextStyle(color: statusColor))
                    : null,
                trailing: hasPermission && !isPartial
                    ? Icon(Icons.check_circle, color: statusColor)
                    : TextButton(
                        onPressed: () async {
                          if (!hasPermission) {
                            // Try to request permission first
                            final granted = await ref
                                .read(notificationPermissionStatusProvider
                                    .notifier)
                                .requestPermission();
                            if (!granted && context.mounted) {
                              // Permission denied, show dialog to open settings
                              _showOpenSettingsDialog(context);
                            }
                          } else {
                            // Partial permission, open settings
                            _showOpenSettingsDialog(context);
                          }
                        },
                        child: Text(!hasPermission ? '请求权限' : '打开设置'),
                      ),
              ),
              if (isPartial) ...[
                const Divider(height: DS.spacing8),
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing16,
                    vertical: DS.spacing8,
                  ),
                  child: Row(
                    children: [
                      _buildPermissionChip(
                        'Alert',
                        status.alertEnabled ?? false,
                      ),
                      const SizedBox(width: DS.spacing8),
                      _buildPermissionChip(
                        'Badge',
                        status.badgeEnabled ?? false,
                      ),
                      const SizedBox(width: DS.spacing8),
                      _buildPermissionChip(
                        'Sound',
                        status.soundEnabled ?? false,
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildPermissionChip(String label, bool enabled) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: enabled
            ? DS.success.withValues(alpha: 0.1)
            : DS.surfaceTertiary.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(DS.radius8),
        border: Border.all(
          color: enabled ? DS.success : DS.borderSubtle,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            enabled ? Icons.check : Icons.close,
            size: 14,
            color: enabled ? DS.success : DS.textSecondary,
          ),
          const SizedBox(width: DS.spacing4),
          Text(
            label,
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: enabled ? DS.success : DS.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  void _showOpenSettingsDialog(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('通知权限状态'),
        content: const Text('通知权限被拒绝，请在系统设置中开启'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              // Open app settings
              unawaited(
                ref
                    .read(notificationPermissionStatusProvider.notifier)
                    .requestPermission(),
              );
            },
            child: const Text('打开设置'),
          ),
        ],
      ),
    );
  }

  Widget _buildAiUsageSummary(Map<String, dynamic> summary) {
    final theme = Theme.of(context);
    final items = (summary['items'] as List<dynamic>? ?? const <dynamic>[])
        .whereType<Map<String, dynamic>>()
        .toList();
    if (items.isEmpty) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Text('今日额度统计准备中。'),
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '今日 AI 额度与消耗',
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          ...items.map((item) {
            final label =
                item['label']?.toString() ?? item['mode']?.toString() ?? '';
            final used = item['requests_used'] ?? 0;
            final limit = item['requests_limit'] ?? 0;
            final tokens = item['total_tokens'] ?? 0;
            final cost = (item['total_cost_usd'] as num?)?.toDouble() ?? 0.0;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 44,
                    child: Text(
                      label,
                      style: theme.textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  Expanded(
                    child: Text(
                      '$used/$limit 次 · $tokens tokens · \$${cost.toStringAsFixed(4)}',
                      style: theme.textTheme.bodySmall,
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
