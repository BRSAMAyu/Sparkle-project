import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/scroll_edge_haptics.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/errors/failures.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/aurora_correction_payload.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_progress_card.dart';
import 'package:sparkle/features/aurora/data/services/aurora_telemetry_service.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_calibration_strip.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/chat_routes.dart';
import 'package:sparkle/features/chat/data/services/message_notification_service.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/experience/presentation/providers/experience_provider.dart';
import 'package:sparkle/features/experience/presentation/widgets/goal_detail_snapshot_card.dart';
import 'package:sparkle/features/experience/presentation/widgets/growth_quality_card.dart';
import 'package:sparkle/features/experience/presentation/widgets/understanding_snapshot_card.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_slot_config_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/providers/notification_provider.dart';
import 'package:sparkle/features/home/presentation/providers/spine_status_band_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/aurora_status_band.dart';
import 'package:sparkle/features/home/presentation/widgets/collapsible_slot.dart';
import 'package:sparkle/features/home/presentation/widgets/compact_status_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/daily_context_line.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_card_section.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_edit_sheet.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';
import 'package:sparkle/features/home/presentation/widgets/exam_sprint_dashboard_card.dart';
import 'package:sparkle/features/home/presentation/widgets/goal_switcher.dart';
import 'package:sparkle/features/home/presentation/widgets/home_notification_card.dart';
import 'package:sparkle/features/home/presentation/widgets/learning_heatmap_widget.dart';
import 'package:sparkle/features/home/presentation/widgets/metrics_row.dart';
import 'package:sparkle/features/home/presentation/widgets/multi_goal_dashboard_card.dart';
import 'package:sparkle/features/home/presentation/widgets/predicted_intent_card.dart';
import 'package:sparkle/features/home/presentation/widgets/recent_insights_card.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_board_card.dart';
import 'package:sparkle/features/home/presentation/widgets/understanding_panel.dart';
import 'package:sparkle/features/home/presentation/widgets/unified_omni_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_header.dart';
import 'package:sparkle/features/insights/presentation/widgets/return_case_file_card.dart';
import 'package:sparkle/features/insights/presentation/widgets/weekly_growth_narrative_card.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/reviews/presentation/widgets/nightly_review_panel.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Shows a text input dialog for freeform Aurora correction.
/// Returns trimmed text only when the user submits; cancel returns null.
Future<String?> showAuroraFreeformCorrectionInputDialog(BuildContext context) {
  final zh = I18nService.instance.isChinese;
  final controller = TextEditingController();
  final focusNode = FocusNode();

  return showDialog<String?>(
    context: context,
    builder: (ctx) {
      String? submittedText() {
        final text = controller.text.trim();
        return text.isEmpty ? null : text;
      }

      return AlertDialog(
        title: Text(
          zh ? '你想告诉 Sparkle 什么？' : 'What would you like to tell Sparkle?',
        ),
        content: TextField(
          controller: controller,
          focusNode: focusNode,
          autofocus: true,
          maxLines: 3,
          minLines: 2,
          decoration: InputDecoration(
            hintText: zh
                ? '哪里判断错了？说说你的想法…'
                : 'What did Aurora get wrong? Share your thoughts…',
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(DS.radius12),
            ),
            contentPadding: const EdgeInsets.all(DS.spacing12),
          ),
          textInputAction: TextInputAction.send,
          onSubmitted: (_) {
            final text = submittedText();
            if (text != null) {
              Navigator.of(ctx).pop(text);
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text(zh ? '取消' : 'Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(submittedText()),
            child: Text(zh ? '发送' : 'Send'),
          ),
        ],
      );
    },
  ).whenComplete(() {
    focusNode.dispose();
    controller.dispose();
  });
}

/// Records telemetry with the user's actual freeform text AFTER submission.
Future<void> _showFreeformCorrectionDialog(
  BuildContext context, {
  required String bandStatus,
  required String semanticValue,
  required bool isDisconfirming,
  AuroraTelemetryService? telemetry,
}) async {
  final text = await showAuroraFreeformCorrectionInputDialog(context);
  if (text == null || text.isEmpty) return;

  if (!context.mounted) return;
  if (telemetry != null) {
    unawaited(
      telemetry.recordStatusBandCorrection(
        label: text,
        semanticValue: semanticValue,
        isDisconfirming: isDisconfirming,
        bandStatus: bandStatus,
        isFreeform: true,
        freeformText: text,
      ),
    );
  }
  unawaited(
    context.push(
      ChatRoutes.chat,
      extra: {
        'initial_user_message': text,
        'aurora_correction': AuroraCorrectionPayload.freeform(
          surface: AuroraCorrectionSurface.dashboard,
          semanticValue: semanticValue,
          label: text,
          freeformText: text,
          isDisconfirming: isDisconfirming,
          bandStatus: bandStatus,
        ).toJson(),
      },
    ),
  );
}

/// Dashboard screen - extracted from HomeScreen
/// Displays the main project cockpit with bento grid layout
class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  static const double _minimumOmniBarViewportInset = 92;
  static const double _omniBarComfortSpacing = 28;
  static const double _bottomScrollTailHeight = 24;
  static const double _omniBarExpandedBuffer = 96;
  bool _isBriefingExpanded = false;
  bool _isUnderstandingExpanded = false;
  double? _omniBarHeight;

  Widget _staggeredSection({
    required int index,
    required Widget child,
  }) =>
      SparkleStaggerItem(
        index: index,
        child: child,
      );

  bool _shouldShowFirstGoalEmptyState(DashboardState state) {
    if (state.isLoading || state.error != null) {
      return false;
    }
    return state.nextActions.isEmpty &&
        state.sprint == null &&
        state.growth == null;
  }

  AuroraBandState _resolveAuroraState(DashboardState state) {
    final sprint = state.sprint;
    if (sprint != null) {
      if (sprint.daysLeft <= 2) return AuroraBandState.riskDetected;
      return AuroraBandState.strategyActive;
    }
    if (state.nextActions.isEmpty && state.growth == null) {
      return AuroraBandState.calibrated;
    }
    return AuroraBandState.calibrated;
  }

  String? _auroraBandLabel(DashboardState state) {
    final sprint = state.sprint;
    if (sprint != null) {
      if (sprint.daysLeft <= 2) return context.l10n.dashboardSprintPhase;
      return context.l10n.dashboardSprintDaysLeft(sprint.daysLeft);
    }
    return null;
  }

  void _handleOmniBarHeightChanged(double height) {
    if (_omniBarHeight != null && (_omniBarHeight! - height).abs() < 0.5) {
      return;
    }
    setState(() {
      _omniBarHeight = height;
    });
  }

  Future<void> _refreshHomeGrowthState() async {
    ref
      ..invalidate(homeActivePlanStatusProvider)
      ..invalidate(homeTodayTasksSnapshotProvider)
      ..invalidate(homeStreakProvider)
      ..invalidate(homePlanBottlenecksProvider)
      ..invalidate(homeDailyContextLineProvider)
      ..invalidate(homeGrowthDashboardSnapshotProvider)
      ..invalidate(homeGrowthStateProvider)
      ..invalidate(understandingSnapshotProvider)
      ..invalidate(experienceGrowthDashboardProvider)
      ..invalidate(currentGoalDetailSnapshotProvider)
      ..invalidate(examSprintDashboardProvider);

    try {
      await Future.wait([
        ref.read(homeGrowthStateProvider.future),
        ref.read(homeDailyContextLineProvider.future),
      ]);
    } catch (e, st) {
      // The card falls back to an empty-plan state if growth data is unavailable.
      debugPrint('Dashboard: growth state refresh failed: $e\n$st');
    }
  }

  Widget _buildAuroraStatusBandSlot(DashboardState dashboardState) => Builder(
        builder: (context) {
          final bandAsync = ref.watch(spineStatusBandProvider);
          return bandAsync.when(
            data: (band) => AuroraStatusBand(
              state: band != null
                  ? AuroraStatusBand.mapBandStatus(band.bandStatus)
                  : _resolveAuroraState(dashboardState),
              label: band?.bandSummary.isNotEmpty ?? false
                  ? band!.bandSummary
                  : _auroraBandLabel(dashboardState),
              correctionOptions: band?.correctionOptions ?? [],
              cooldownRemainingSeconds: band?.cooldownRemainingSeconds,
              cooldownCanOverride: band?.cooldownCanOverride ?? false,
              onTap: () => unawaited(context.push(ChatRoutes.chat)),
              onCorrectionTap: (opt) {
                if (opt.isFreeform) {
                  unawaited(
                    _showFreeformCorrectionDialog(
                      context,
                      bandStatus: band?.bandStatus.protocolValue ?? '',
                      semanticValue: opt.semanticValue,
                      isDisconfirming: opt.isDisconfirming,
                      telemetry: AuroraTelemetryService(
                        ref.read(apiClientProvider),
                      ),
                    ),
                  );
                } else {
                  final telemetry =
                      AuroraTelemetryService(ref.read(apiClientProvider));
                  unawaited(
                    telemetry.recordStatusBandCorrection(
                      label: opt.label,
                      semanticValue: opt.semanticValue,
                      isDisconfirming: opt.isDisconfirming,
                      bandStatus: band?.bandStatus.protocolValue ?? '',
                    ),
                  );
                  final payload = AuroraCorrectionPayload.chip(
                    surface: AuroraCorrectionSurface.dashboard,
                    semanticValue: opt.semanticValue,
                    label: opt.label,
                    isDisconfirming: opt.isDisconfirming,
                    bandStatus: band?.bandStatus.protocolValue ?? '',
                  );
                  unawaited(
                    context.push(
                      ChatRoutes.chat,
                      extra: {
                        'initial_user_message': opt.label,
                        'aurora_correction': payload.toJson(),
                      },
                    ),
                  );
                }
              },
              onCooldownOverride: () {
                final telemetry =
                    AuroraTelemetryService(ref.read(apiClientProvider));
                unawaited(
                  telemetry.recordStatusBandCorrection(
                    label: context.l10n.dashboardQuickCalibration,
                    semanticValue: 'quick_calibration',
                    isDisconfirming: false,
                    bandStatus: band?.bandStatus.protocolValue ?? '',
                  ),
                );
                final payload = AuroraCorrectionPayload.calibrationOverride(
                  surface: AuroraCorrectionSurface.dashboard,
                  semanticValue: 'quick_calibration',
                  label: context.l10n.dashboardQuickCalibration,
                  bandStatus: band?.bandStatus.protocolValue ?? '',
                );
                unawaited(
                  context.push(
                    ChatRoutes.chat,
                    extra: {
                      'initial_user_message':
                          context.l10n.dashboardQuickCalibration,
                      'aurora_correction': payload.toJson(),
                    },
                  ),
                );
              },
            ),
            loading: () => AuroraStatusBand(
              state: _resolveAuroraState(dashboardState),
              label: _auroraBandLabel(dashboardState),
              onTap: () => context.push(ChatRoutes.chat),
            ),
            error: (_, __) => AuroraStatusBand(
              state: _resolveAuroraState(dashboardState),
              label: _auroraBandLabel(dashboardState),
              onTap: () => context.push(ChatRoutes.chat),
            ),
          );
        },
      );

  void _openBottleneckChat(HomeBottleneck bottleneck) {
    final prompt = context.l10n.dashboardBottleneckPrompt(bottleneck.topic);
    context.go(
      Uri(
        path: '/chat',
        queryParameters: {
          'prompt': prompt,
          'chat_mode': 'growth',
        },
      ).toString(),
    );
  }

  void _startNextAction(HomeGrowthTask task) {
    if (task.id.isEmpty) {
      unawaited(context.push('/tasks'));
      return;
    }

    final taskModel = task.taskModel;
    if (taskModel == null) {
      unawaited(context.push('/tasks/${task.id}'));
      return;
    }

    ref.read(activeTaskProvider.notifier).state = taskModel;
    unawaited(
      context.push('/tasks/${task.id}/execute?origin=home_growth'),
    );
  }

  Widget _buildFirstGoalEmptyState() => ContentConstraint(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing6,
            DS.spacing16,
            DS.spacing10,
          ),
          child: DashboardSectionShell(
            tone: DashboardSurfaceTone.hero,
            padding: const EdgeInsets.all(DS.spacing20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DashboardSectionHeader(
                  icon: Icons.auto_awesome_rounded,
                  iconSize: 40,
                  accentColor: DS.brandPrimary,
                  title: context.l10n.dashboardSetFirstGoal,
                  summary: context.l10n.dashboardSetFirstGoalSummary,
                ),
                const SizedBox(height: DS.spacing16),
                Text(
                  context.l10n.dashboardWhatToPush,
                  style: DS.bodySmall.copyWith(
                    color: DS.textSecondary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: DS.spacing12),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    _GoalChip(
                      label: context.l10n.dashboardGoalExamSprint,
                      icon: Icons.local_fire_department_outlined,
                      onTap: () => context.go(
                        '/chat?prompt=${Uri.encodeComponent(context.l10n.dashboardGoalExamSprintPrompt)}',
                      ),
                    ),
                    _GoalChip(
                      label: context.l10n.dashboardGoalLongTerm,
                      icon: Icons.school_outlined,
                      onTap: () => context.go(
                        '/chat?prompt=${Uri.encodeComponent(context.l10n.dashboardGoalLongTermPrompt)}',
                      ),
                    ),
                    _GoalChip(
                      label: context.l10n.dashboardGoalProject,
                      icon: Icons.rocket_launch_outlined,
                      onTap: () => context.go(
                        '/chat?prompt=${Uri.encodeComponent(context.l10n.dashboardGoalProjectPrompt)}',
                      ),
                    ),
                    _GoalChip(
                      label: context.l10n.dashboardGoalSelfGrowth,
                      icon: Icons.psychology_outlined,
                      onTap: () => context.go(
                        '/chat?prompt=${Uri.encodeComponent(context.l10n.dashboardGoalSelfGrowthPrompt)}',
                      ),
                    ),
                    _GoalChip(
                      label: context.l10n.dashboardGoalNotSure,
                      icon: Icons.help_outline,
                      onTap: () => context.go(
                        '/chat?prompt=${Uri.encodeComponent(context.l10n.dashboardGoalNotSurePrompt)}',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing16),
                Wrap(
                  spacing: DS.spacing12,
                  runSpacing: DS.spacing10,
                  children: [
                    SparkleButton.primary(
                      label: context.l10n.dashboardStartWithAI,
                      onPressed: () => context.go('/goals/new'),
                    ),
                    SparkleButton.ghost(
                      label: I18nService.instance.isChinese
                          ? '快速创建'
                          : 'Quick create',
                      onPressed: () => context.go('/chat'),
                    ),
                    SparkleButton.ghost(
                      label: context.l10n.dashboardOpenTaskList,
                      onPressed: () => context.push('/tasks'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );

  Widget _buildOnboardingWelcome() => ContentConstraint(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing12,
            DS.spacing16,
            DS.spacing16,
          ),
          child: DashboardSectionShell(
            tone: DashboardSurfaceTone.hero,
            padding: const EdgeInsets.all(DS.spacing24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                DashboardSectionHeader(
                  icon: Icons.auto_awesome_rounded,
                  iconSize: 44,
                  accentColor: DS.brandPrimary,
                  title: context.l10n.chatWelcomeTitle,
                  summary: I18nService.instance.isChinese
                      ? '我是你的AI成长伙伴。设定目标，我来帮你一步步达成。'
                      : 'I\'m your AI growth companion. Set a goal and I\'ll help you achieve it step by step.',
                ),
                const SizedBox(height: DS.spacing20),
                _OnboardingQuickCard(
                  icon: Icons.flag_outlined,
                  color: DS.brandPrimary,
                  title: I18nService.instance.isChinese ? '设定目标' : 'Set a goal',
                  subtitle: I18nService.instance.isChinese
                      ? '告诉我你想达成什么，我来帮你制定计划'
                      : 'Tell me what you want to achieve',
                  onTap: () => context.go('/goals/new'),
                ),
                const SizedBox(height: DS.spacing8),
                _OnboardingQuickCard(
                  icon: Icons.chat_bubble_outline,
                  color: DS.success,
                  title: I18nService.instance.isChinese ? '跟Sparkle聊聊' : 'Chat with Sparkle',
                  subtitle: I18nService.instance.isChinese
                      ? '聊聊你的想法，获得个性化建议'
                      : 'Share your thoughts, get personalized guidance',
                  onTap: () => context.go('/chat'),
                ),
                const SizedBox(height: DS.spacing8),
                _OnboardingQuickCard(
                  icon: Icons.explore_outlined,
                  color: DS.info,
                  title: I18nService.instance.isChinese ? '探索知识星图' : 'Explore knowledge map',
                  subtitle: I18nService.instance.isChinese
                      ? '发现你的知识结构，找到提升方向'
                      : 'Discover your knowledge structure and growth areas',
                  onTap: () => context.go('/galaxy'),
                ),
              ],
            ),
          ),
        ),
      );

  List<Widget> _buildDashboardSkeletonSections() => const [
        Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing8,
          ),
          child: SparkleCardSkeleton(),
        ),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: DS.spacing16),
          child: SparkleCardSkeleton(),
        ),
        Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing12,
            DS.spacing16,
            DS.spacing8,
          ),
          child: SparkleCardSkeleton(),
        ),
        Padding(
          padding: EdgeInsets.symmetric(horizontal: DS.spacing16),
          child: SparkleChatBubbleSkeleton(),
        ),
        Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing8,
          ),
          child: SparkleCardSkeleton(),
        ),
      ];

  /// Resolve the actual widget for a given customizable slot id. Returns
  /// `null` when the slot's underlying data isn't present (e.g. an exam
  /// sprint hasn't been started) so the slot is skipped entirely instead
  /// of rendering a placeholder shell.
  Widget? _buildSlotContent(
    String slotId, {
    required DashboardState dashboardState,
    required HomeGrowthState? growthState,
    required AsyncValue<HomeGrowthState> growthAsync,
    required ExamSprintDashboardData? examSprintDashboard,
    required HomeBottleneck? activeBottleneck,
  }) {
    switch (slotId) {
      case DashboardSlotIds.dailyBriefing:
        return _DailyBriefingCard(
          dashboardState: dashboardState,
          isExpanded: _isBriefingExpanded,
          onToggleExpanded: () {
            setState(() {
              _isBriefingExpanded = !_isBriefingExpanded;
            });
          },
        );
      case DashboardSlotIds.metricsRow:
        return MetricsRow(dashboardState: dashboardState);
      case DashboardSlotIds.commandCenter:
        return _HomeCommandCenterCard(
          dashboardState: dashboardState,
          growthState: growthState,
          isLoading: growthState == null && growthAsync.isLoading,
          onStartTask: _startNextAction,
          onOpenTasks: () {
            unawaited(context.push('/tasks'));
          },
          onCreatePlan: () {
            unawaited(context.push('/plans/new?type=growth'));
          },
          onOpenAurora: () {
            unawaited(context.push(ChatRoutes.chat));
          },
          onOpenBottleneckChat: activeBottleneck == null
              ? null
              : () => _openBottleneckChat(activeBottleneck),
        );
      case DashboardSlotIds.understanding:
        return _UnderstandingExpansionSlot(
          isExpanded: _isUnderstandingExpanded,
          onToggle: () {
            setState(() {
              _isUnderstandingExpanded = !_isUnderstandingExpanded;
            });
          },
        );
      case DashboardSlotIds.returnCaseFile:
        return const ReturnCaseFileCard();
      case DashboardSlotIds.goalDetailSnapshot:
        return GoalDetailSnapshotCard(
          onOpenGoal: () => unawaited(context.push('/goals/current')),
        );
      case DashboardSlotIds.multiGoalDashboard:
        return const MultiGoalDashboardCard();
      case DashboardSlotIds.taskBoard:
        return const TaskBoardCard();
      case DashboardSlotIds.examSprint:
        if (examSprintDashboard == null) {
          // Slot was opted-in but no sprint exists yet — render a small CTA
          // instead of silently disappearing. Respectful of the user's
          // explicit choice to keep this slot visible.
          return _buildSlotEmptyCta(
            icon: Icons.local_fire_department_outlined,
            accent: DS.warning,
            titleZh: '考试冲刺',
            titleEn: 'Exam sprint',
            bodyZh: '还没有进行中的冲刺。设置一个目标，看到每日节奏与剩余天数。',
            bodyEn:
                'No active sprint yet. Set a target to see daily cadence and days left.',
            actionLabelZh: '创建冲刺',
            actionLabelEn: 'Create sprint',
            onAction: () => unawaited(context.push('/exam-sprint/setup')),
          );
        }
        return ExamSprintDashboardCard(
          data: examSprintDashboard,
          onRecordResult: () {
            unawaited(
              context.push(
                '/exam-sprint/review?plan_id=${examSprintDashboard.planId}'
                '&subject=${Uri.encodeComponent(examSprintDashboard.subject)}',
              ),
            );
          },
        );
      case DashboardSlotIds.dashboardUpdates:
        return const _DashboardUpdatesSection();
      case DashboardSlotIds.growthQuality:
        return const GrowthQualityCard();
      case DashboardSlotIds.weeklyNarrative:
        return const _WeeklyNarrativeSlot();
      case DashboardSlotIds.community:
        return const _CommunityAccountabilitySlot();
      case DashboardSlotIds.achievementProgress:
        return const AchievementProgressCard();
      case DashboardSlotIds.learningHeatmap:
        return const Padding(
          padding: EdgeInsets.symmetric(horizontal: DS.spacing16),
          child: LearningHeatmapWidget(),
        );
      case DashboardSlotIds.workspaceCards:
        return const DashboardCardSection();
    }
    return null;
  }

  _SlotMeta _slotMeta(
    String slotId, {
    required DashboardState dashboardState,
    required HomeGrowthState? growthState,
    required ExamSprintDashboardData? examSprintDashboard,
    required int workspaceCardCount,
  }) {
    final zh = I18nService.instance.isChinese;
    switch (slotId) {
      case DashboardSlotIds.dailyBriefing:
        final actions = dashboardState.nextActions.length;
        return _SlotMeta(
          title: zh ? '今日简报' : 'Daily briefing',
          icon: Icons.wb_sunny_outlined,
          summary: actions > 0
              ? (zh
                  ? '今天 $actions 件待办 · 已就绪'
                  : '$actions next actions · ready to start')
              : (zh ? '当天的状态与节奏' : 'Today\'s status & pace'),
          accent: DS.brandPrimary,
        );
      case DashboardSlotIds.metricsRow:
        final streak =
            growthState?.streak ?? dashboardState.growthStatus?.streakDays ?? 0;
        return _SlotMeta(
          title: zh ? '关键指标' : 'Key metrics',
          icon: Icons.insights_rounded,
          summary: streak > 0
              ? (zh ? '🔥 连续 $streak 天' : '🔥 $streak-day streak')
              : (zh ? '进度、连续天数、动力' : 'Progress, streak, momentum'),
          accent: DS.info,
        );
      case DashboardSlotIds.commandCenter:
        final nextLabel = growthState?.nextAction?.title ??
            (dashboardState.nextActions.isNotEmpty
                ? dashboardState.nextActions.first.title
                : '');
        return _SlotMeta(
          title: zh ? '指挥中心' : 'Command center',
          icon: Icons.bolt_rounded,
          summary: nextLabel.isNotEmpty
              ? (zh ? '下一步：$nextLabel' : 'Next: $nextLabel')
              : (zh ? '下一步行动入口' : 'Pick up the next action'),
          accent: DS.brandPrimary,
        );
      case DashboardSlotIds.understanding:
        return _SlotMeta(
          title: zh ? '理解面板' : 'Understanding',
          icon: Icons.psychology_outlined,
          summary: zh ? 'Sparkle 对你的认知拆解' : 'How Sparkle reads you',
          accent: DS.info,
        );
      case DashboardSlotIds.returnCaseFile:
        return _SlotMeta(
          title: zh ? '回归档案' : 'Return case file',
          icon: Icons.history_edu_rounded,
          summary: zh ? '上次离开时的现场' : 'Where you left off',
          accent: DS.warning,
        );
      case DashboardSlotIds.goalDetailSnapshot:
        final goal = dashboardState.growth;
        return _SlotMeta(
          title: zh ? '目标详情' : 'Goal snapshot',
          icon: Icons.flag_outlined,
          summary: goal != null
              ? (zh
                  ? '${goal.name} · ${(goal.progress * 100).round()}%'
                  : '${goal.name} · ${(goal.progress * 100).round()}%')
              : (zh ? '当前目标的近况' : 'Active goal snapshot'),
          accent: DS.success,
        );
      case DashboardSlotIds.multiGoalDashboard:
        final tasksTotal = growthState?.tasksTotal ?? 0;
        final tasksDone = growthState?.tasksCompleted ?? 0;
        return _SlotMeta(
          title: zh ? '多目标看板' : 'Multi-goal board',
          icon: Icons.dashboard_customize_outlined,
          summary: tasksTotal > 0
              ? (zh
                  ? '$tasksDone/$tasksTotal 件已完成'
                  : '$tasksDone of $tasksTotal done')
              : (zh ? '所有目标的总览' : 'All goals at a glance'),
          accent: DS.brandPrimary,
        );
      case DashboardSlotIds.taskBoard:
        final total = growthState?.tasksTotal ?? 0;
        final done = growthState?.tasksCompleted ?? 0;
        return _SlotMeta(
          title: zh ? '任务面板' : 'Task board',
          icon: Icons.checklist_rounded,
          summary: total > 0
              ? (zh
                  ? '完成 $done/$total · ${done == total ? "今日达标" : "再 ${total - done} 件冲刺"}'
                  : '$done/$total done · ${done == total ? 'today’s goal hit' : '${total - done} to go'}')
              : (zh ? '今日待办与进度' : 'Today\'s tasks & progress'),
          accent: DS.success,
        );
      case DashboardSlotIds.examSprint:
        if (examSprintDashboard != null) {
          return _SlotMeta(
            title: zh ? '考试冲刺' : 'Exam sprint',
            icon: Icons.local_fire_department_outlined,
            summary: zh
                ? '${examSprintDashboard.subject} · ${examSprintDashboard.daysLeft} 天后'
                : '${examSprintDashboard.subject} · ${examSprintDashboard.daysLeft}d left',
            accent: DS.warning,
          );
        }
        return _SlotMeta(
          title: zh ? '考试冲刺' : 'Exam sprint',
          icon: Icons.local_fire_department_outlined,
          summary: zh ? '尚未启动 · 点开创建' : 'Not started · tap to set up',
          accent: DS.warning,
        );
      case DashboardSlotIds.dashboardUpdates:
        return _SlotMeta(
          title: zh ? '动态' : 'Updates',
          icon: Icons.notifications_outlined,
          summary: zh ? '通知、洞察、提醒' : 'Notifications & insights',
          accent: DS.info,
        );
      case DashboardSlotIds.growthQuality:
        return _SlotMeta(
          title: zh ? '成长质量' : 'Growth quality',
          icon: Icons.trending_up_rounded,
          summary: zh ? '深度、稳定性、平衡' : 'Depth, stability, balance',
          accent: DS.success,
        );
      case DashboardSlotIds.weeklyNarrative:
        return _SlotMeta(
          title: zh ? '本周叙事' : 'Weekly narrative',
          icon: Icons.menu_book_outlined,
          summary: zh ? '一周变化的故事线' : 'This week\'s story',
          accent: DS.info,
        );
      case DashboardSlotIds.community:
        return _SlotMeta(
          title: zh ? '同行社群' : 'Community',
          icon: Icons.group_outlined,
          summary: zh ? '伙伴动态与监督' : 'Partners & accountability',
          accent: DS.brandPrimary,
        );
      case DashboardSlotIds.achievementProgress:
        return _SlotMeta(
          title: zh ? '成就进度' : 'Achievements',
          icon: Icons.emoji_events_outlined,
          summary: zh ? '近期解锁与里程碑' : 'Recent unlocks & milestones',
          accent: DS.warning,
        );
      case DashboardSlotIds.learningHeatmap:
        return _SlotMeta(
          title: zh ? '学习热力图' : 'Learning heatmap',
          icon: Icons.calendar_view_month_rounded,
          summary: zh ? '过去30天的活跃度' : 'Last 30 days of activity',
          accent: DS.info,
        );
      case DashboardSlotIds.workspaceCards:
        return _SlotMeta(
          title: zh ? '工作区卡片' : 'Workspace cards',
          icon: Icons.view_module_outlined,
          summary: workspaceCardCount > 0
              ? (zh
                  ? '$workspaceCardCount 张已显示'
                  : '$workspaceCardCount cards visible')
              : (zh ? '尚未启用任何卡片' : 'No cards enabled'),
          accent: DS.brandPrimary,
        );
    }
    return _SlotMeta(
      title: slotId,
      icon: Icons.extension_outlined,
      accent: DS.brandPrimary,
    );
  }

  Widget _buildEmptyDashboardCta() {
    final zh = I18nService.instance.isChinese;
    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing24,
          DS.spacing16,
          DS.spacing24,
        ),
        child: DashboardSectionShell(
          tone: DashboardSurfaceTone.summary,
          padding: const EdgeInsets.all(DS.spacing20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.tune_rounded,
                    size: 22,
                    color: DS.brandPrimary,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      zh ? '驾驶舱已经清空' : 'Your dashboard is empty',
                      style: DS.titleMedium.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                zh
                    ? '点开下方"自定义"重新选择想要常驻的模块。'
                    : 'Tap "Customize" below to bring slots back.',
                style: DS.bodySmall.copyWith(color: DS.textSecondary),
              ),
              const SizedBox(height: DS.spacing16),
              SparkleButton.primary(
                label: zh ? '自定义驾驶舱' : 'Customize dashboard',
                onPressed: () => unawaited(
                  showSensoryModalBottomSheet<void>(
                    context: context,
                    isScrollControlled: true,
                    backgroundColor: Colors.transparent,
                    builder: (context) => const DashboardEditSheet(),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Inline empty-state surface for individual slots that the user kept
  /// visible but have no underlying data yet. Coherent with the
  /// dashboard-level `_buildEmptyDashboardCta` (same shell tone, same
  /// button family) so the visual language stays consistent regardless
  /// of whether the empty surface lives at slot or screen level.
  Widget _buildSlotEmptyCta({
    required IconData icon,
    required Color accent,
    required String titleZh,
    required String titleEn,
    required String bodyZh,
    required String bodyEn,
    required String actionLabelZh,
    required String actionLabelEn,
    required VoidCallback onAction,
  }) {
    final zh = I18nService.instance.isChinese;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: DashboardSectionShell(
        tone: DashboardSurfaceTone.summary,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: accent.withValues(alpha: 0.18),
                    ),
                  ),
                  child: Icon(icon, size: 16, color: accent),
                ),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: Text(
                    zh ? titleZh : titleEn,
                    style: DS.titleMedium.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightSemiBold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              zh ? bodyZh : bodyEn,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing12),
            Align(
              alignment: Alignment.centerLeft,
              child: SparkleButton.ghost(
                label: zh ? actionLabelZh : actionLabelEn,
                onPressed: onAction,
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Quiet end-of-list discovery affordance for the dashboard editor.
  /// Long-press on any slot still opens the same sheet, but this footer
  /// is the "I want to find the settings" path for users who don't
  /// know about long-press.
  Widget _buildCustomizeFooter() {
    final zh = I18nService.instance.isChinese;
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        DS.spacing8,
        DS.spacing16,
        DS.spacing8,
      ),
      child: Center(
        child: TextButton.icon(
          onPressed: () {
            unawaited(
              SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen),
            );
            unawaited(
              showSensoryModalBottomSheet<void>(
                context: context,
                isScrollControlled: true,
                backgroundColor: Colors.transparent,
                builder: (context) => const DashboardEditSheet(),
              ),
            );
          },
          icon: Icon(
            Icons.tune_rounded,
            size: 18,
            color: DS.textSecondary,
          ),
          label: Text(
            zh ? '自定义驾驶舱' : 'Customize dashboard',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(currentUserProvider);
    final dashboardState = ref.watch(dashboardProvider);
    final examSprintDashboardAsync = ref.watch(examSprintDashboardProvider);
    final growthAsync = ref.watch(homeGrowthStateProvider);
    final dailyContextAsync = ref.watch(homeDailyContextLineProvider);
    final predictions = ref.watch(visiblePredictionsProvider);
    final l10n = AppLocalizations.of(context)!;
    final showFirstGoalEmptyState =
        _shouldShowFirstGoalEmptyState(dashboardState);
    final textScale = MediaQuery.textScalerOf(context).scale(1);
    final mediaPadding = MediaQuery.paddingOf(context);
    final bottomSafeInset = mediaPadding.bottom;

    final category = ResponsiveSystem.getCategory(context);
    final fallbackOmniBarHeight = 52.0 +
        (predictions.isNotEmpty ? (textScale >= 1.2 ? 48.0 : 36.0) : 0.0);
    final measuredOmniBarHeight =
        (_omniBarHeight ?? fallbackOmniBarHeight).clamp(
      _minimumOmniBarViewportInset,
      fallbackOmniBarHeight + _omniBarExpandedBuffer,
    );
    final viewportBottomInset =
        measuredOmniBarHeight + bottomSafeInset + _omniBarComfortSpacing;
    final totalBottomHeight = bottomSafeInset + _bottomScrollTailHeight;

    // Max width for floating components on larger screens
    final floatingMaxWidth = switch (category) {
      DeviceCategory.tablet => DS.contentMaxWidthTablet,
      DeviceCategory.desktop => DS.contentMaxWidthDesktop,
      DeviceCategory.tv => DS.contentMaxWidthDesktop,
      DeviceCategory.watch => double.infinity,
      DeviceCategory.phone => double.infinity,
      DeviceCategory.phablet => double.infinity,
    };

    final growthState = growthAsync.maybeWhen(
      data: (state) => state,
      error: (_, __) => const HomeGrowthState.empty(),
      orElse: () => null,
    );
    final dailyContextLine = dailyContextAsync.maybeWhen(
      data: (line) => line,
      error: (_, __) => HomeDailyContextLine.fallback(),
      orElse: () => null,
    );
    final activeBottleneck = growthState?.activeBottleneck;
    final examSprintDashboard = examSprintDashboardAsync.valueOrNull;
    final slotConfig = ref.watch(dashboardSlotConfigProvider);
    final goalOverview = ref.watch(multiGoalOverviewProvider);
    final hasNoGoals = goalOverview.maybeWhen(
      data: (d) => d.goals.isEmpty,
      orElse: () => false,
    );
    final workspaceCardCount = ref.watch(
      dashboardCardConfigProvider.select((c) => c.visibleCardIds.length),
    );
    var growthSectionIndex = 0;
    final showGrowthHeader = dashboardState.error == null;
    final growthSections = !showGrowthHeader
        ? <Widget>[]
        : <Widget>[
            _staggeredSection(
              index: growthSectionIndex++,
              child: CompactStatusBar(
                user: user,
                dashboardState: dashboardState,
              ),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: _buildAuroraStatusBandSlot(dashboardState),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: ContentConstraint(
                child: UnderstandingSnapshotCard(
                  onOpenChat: () => unawaited(context.push(ChatRoutes.chat)),
                ),
              ),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: const _DashboardGoalSwitcherBand(),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: DailyContextLine(
                text: dailyContextLine?.text,
                isLoading:
                    dailyContextLine == null && dailyContextAsync.isLoading,
              ),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: _HomeCommandCenterCard(
                dashboardState: dashboardState,
                growthState: growthState,
                isLoading: growthState == null && growthAsync.isLoading,
                onStartTask: _startNextAction,
                onOpenTasks: () {
                  unawaited(context.push('/tasks'));
                },
                onCreatePlan: () {
                  unawaited(context.push('/plans/new?type=growth'));
                },
                onOpenAurora: () {
                  unawaited(context.push(ChatRoutes.chat));
                },
                onOpenBottleneckChat: activeBottleneck == null
                    ? null
                    : () => _openBottleneckChat(activeBottleneck),
              ),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: const ReturnCaseFileCard(),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: GoalDetailSnapshotCard(
                onOpenGoal: () => unawaited(context.push('/goals/current')),
              ),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: const MultiGoalDashboardCard(),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: const TaskBoardCard(),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: const GrowthQualityCard(),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: const _CommunityAccountabilitySlot(),
            ),
            if (activeBottleneck != null)
              _staggeredSection(
                index: growthSectionIndex++,
                child: _AttentionSlot(
                  bottleneck: activeBottleneck,
                  onOpen: () => _openBottleneckChat(activeBottleneck),
                ),
              ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: const _WeeklyNarrativeSlot(),
            ),
            if (examSprintDashboard != null)
              _staggeredSection(
                index: growthSectionIndex++,
                child: ExamSprintDashboardCard(
                  data: examSprintDashboard,
                  onRecordResult: () {
                    unawaited(
                      context.push(
                        '/exam-sprint/review?plan_id=${examSprintDashboard.planId}'
                        '&subject=${Uri.encodeComponent(examSprintDashboard.subject)}',
                      ),
                    );
                  },
                ),
              ),
          ];

    var sectionIndex = growthSections.length;
    final dashboardSections = <Widget>[];
    if (dashboardState.error != null) {
      final failureKind = dashboardState.failure?.kind ??
          FailureKindCode.fromCode(dashboardState.failure?.errorCode);
      final zh = I18nService.instance.isChinese;
      final failureIcon = switch (failureKind) {
        FailureKind.auth => Icons.lock_outline_rounded,
        FailureKind.server => Icons.cloud_sync_outlined,
        FailureKind.validation => Icons.edit_note_rounded,
        FailureKind.network || FailureKind.offline => Icons.wifi_off_rounded,
        FailureKind.unknown => Icons.cloud_off_outlined,
      };
      final failureTitle = switch (failureKind) {
        FailureKind.auth => zh ? '需要重新登录' : 'Sign-in needed',
        FailureKind.server => zh ? '服务暂时不稳' : 'Service issue',
        FailureKind.validation => zh ? '需要调整请求' : 'Check request',
        FailureKind.network => zh ? '网络不稳定' : 'Connection issue',
        FailureKind.offline => zh ? '离线了' : 'Offline',
        FailureKind.unknown => zh ? '首页暂时加载失败' : 'Dashboard unavailable',
      };
      final actionLabel = switch (failureKind) {
        FailureKind.auth => zh ? '去登录' : 'Sign in',
        FailureKind.offline => zh ? '连网后重试' : 'Retry online',
        _ => context.l10n.dashboardRetry,
      };
      // R5-F04: Show error UI instead of silently falling back
      dashboardSections
        ..add(
          _staggeredSection(
            index: sectionIndex++,
            child: CompactStatusBar(
              user: user,
              dashboardState: dashboardState,
            ),
          ),
        )
        ..add(
          _staggeredSection(
            index: sectionIndex++,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
              child: Column(
                children: [
                  Icon(failureIcon, size: 40, color: DS.textTertiary),
                  const SizedBox(height: 12),
                  Text(
                    failureTitle,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    dashboardState.error ?? context.l10n.dashboardLoadFailed,
                    style: TextStyle(color: DS.textSecondary, fontSize: 14),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  TextButton.icon(
                    onPressed: () {
                      if (failureKind == FailureKind.auth) {
                        context.go('/login');
                        return;
                      }
                      ref.invalidate(dashboardProvider);
                    },
                    icon: Icon(
                      failureKind == FailureKind.auth
                          ? Icons.login_rounded
                          : Icons.refresh,
                      size: 18,
                    ),
                    label: Text(actionLabel),
                  ),
                ],
              ),
            ),
          ),
        );
    } else if (dashboardState.isLoading) {
      for (final skeleton in _buildDashboardSkeletonSections()) {
        dashboardSections.add(
          _staggeredSection(
            index: sectionIndex++,
            child: skeleton,
          ),
        );
      }
    } else {
      // First-goal empty state always pins to the top of the customizable
      // surface so brand-new users get guidance regardless of which slots
      // they've enabled.
      if (showFirstGoalEmptyState) {
        dashboardSections.add(
          _staggeredSection(
            index: sectionIndex++,
            child: _buildFirstGoalEmptyState(),
          ),
        );
      }

      // Walk the user's slot order, render only what's visible, wrap each
      // in CollapsibleSlot so they can shrink to a 64px header without
      // losing access via the header tap / overflow menu.
      for (final slotId in slotConfig.visibleOrderedSlots) {
        final content = _buildSlotContent(
          slotId,
          dashboardState: dashboardState,
          growthState: growthState,
          growthAsync: growthAsync,
          examSprintDashboard: examSprintDashboard,
          activeBottleneck: activeBottleneck,
        );
        if (content == null) continue;
        final meta = _slotMeta(
          slotId,
          dashboardState: dashboardState,
          growthState: growthState,
          examSprintDashboard: examSprintDashboard,
          workspaceCardCount: workspaceCardCount,
        );
        dashboardSections.add(
          _staggeredSection(
            index: sectionIndex++,
            child: CollapsibleSlot(
              slotId: slotId,
              title: meta.title,
              icon: meta.icon,
              summary: meta.summary,
              accentColor: meta.accent,
              child: content,
            ),
          ),
        );
      }

      // If user has hidden every customizable slot, surface a recovery CTA
      // so the dashboard isn't a blank scroll.
      if (slotConfig.visibleSlotIds.isEmpty) {
        dashboardSections.add(
          _staggeredSection(
            index: sectionIndex++,
            child: _buildEmptyDashboardCta(),
          ),
        );
      } else {
        // Quiet discovery affordance at the end of the visible scroll —
        // gives users a way to find the edit sheet besides long-pressing
        // a slot. Long-press is still the primary "I want to change
        // this" gesture; this footer is the "I want to find the
        // settings" path.
        dashboardSections.add(
          _staggeredSection(
            index: sectionIndex++,
            child: _buildCustomizeFooter(),
          ),
        );
      }
    }

    return SparklePageScaffold(
      role: SparklePageRole.dashboard,
      safeArea: false,
      child: Stack(
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: DS.pageGradientForRole(SparklePageRole.dashboard),
              ),
            ),
          ),
          Positioned.fill(
            child: IgnorePointer(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    center: const Alignment(0.82, -0.28),
                    radius: 1.0,
                    colors: [
                      DS.info.withValues(alpha: 0.1),
                      DS.brandPrimary.withValues(alpha: 0.04),
                      Colors.transparent,
                    ],
                    stops: const [0.0, 0.42, 1.0],
                  ),
                ),
              ),
            ),
          ),
          // Layer 1: Weather Background
          const Positioned.fill(child: WeatherHeader()),

          // Layer 2: Dashboard Content
          SafeArea(
            bottom: false,
            child: RefreshIndicator(
              onRefresh: () async {
                await ref.read(dashboardProvider.notifier).refresh();
                await ref.read(taskListProvider.notifier).refreshTasks();
                await _refreshHomeGrowthState();
              },
              child: Padding(
                padding: EdgeInsets.only(bottom: viewportBottomInset),
                child: ScrollEdgeHaptics(
                  child: CustomScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    slivers: [
                      SliverList(
                        delegate: SliverChildListDelegate(
                          hasNoGoals
                              ? [
                                  _buildOnboardingWelcome(),
                                  ...dashboardSections,
                                ]
                              : [
                                  ...growthSections,
                                  ...dashboardSections,
                                  const AuroraCalibrationStrip(),
                                ],
                        ),
                      ),
                      SliverToBoxAdapter(
                        child: SizedBox(
                          height: totalBottomHeight,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // Layer 3: Unified Omni-Bar (bottom)
          Positioned(
            left: 0,
            right: 0,
            bottom: bottomSafeInset + DS.spacing8,
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: floatingMaxWidth),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                  child: UnifiedOmniBar(
                    hintText: l10n.typeMessage,
                    onHeightChanged: _handleOmniBarHeightChanged,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SlotMeta {
  const _SlotMeta({
    required this.title,
    required this.icon,
    required this.accent,
    this.summary,
  });

  final String title;
  final IconData icon;
  final Color accent;
  final String? summary;
}

class _DashboardGoalSwitcherBand extends StatelessWidget {
  const _DashboardGoalSwitcherBand();

  @override
  Widget build(BuildContext context) => const ContentConstraint(
        child: Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing10,
          ),
          child: Align(
            alignment: Alignment.centerLeft,
            child: GoalSwitcher(dense: true),
          ),
        ),
      );
}

class _UnderstandingExpansionSlot extends StatelessWidget {
  const _UnderstandingExpansionSlot({
    required this.isExpanded,
    required this.onToggle,
  });

  final bool isExpanded;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: Column(
          children: [
            Semantics(
              button: true,
              label: isExpanded
                  ? context.l10n.understandingPanelCollapse
                  : context.l10n.understandingPanelExpand,
              child: InkWell(
                onTap: onToggle,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing12,
                    vertical: DS.spacing10,
                  ),
                  decoration: BoxDecoration(
                    color: scheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: scheme.outlineVariant),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.psychology_alt_outlined,
                        size: 18,
                        color: scheme.primary,
                      ),
                      const SizedBox(width: DS.spacing8),
                      Expanded(
                        child: Text(
                          context.l10n.understandingPanelTitle,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: textTheme.labelLarge?.copyWith(
                            color: scheme.onSurface,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      Icon(
                        isExpanded
                            ? Icons.expand_less_rounded
                            : Icons.expand_more_rounded,
                        color: scheme.onSurfaceVariant,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            ClipRect(
              child: AnimatedSize(
                duration: DS.quick,
                curve: DS.motionCurve(SparkleMotionToken.standard),
                alignment: Alignment.topCenter,
                child: isExpanded
                    ? const UnderstandingPanel(
                        compact: true,
                        initiallyExpanded: true,
                      )
                    : const SizedBox.shrink(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CommunityAccountabilitySlot extends ConsumerWidget {
  const _CommunityAccountabilitySlot();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final overview = ref.watch(accountabilityOverviewProvider);
    return overview.when(
      data: (data) => _CommunityAccountabilitySurface(data: data),
      loading: () => const Padding(
        padding: EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: SparkleCardSkeleton(),
      ),
      error: (_, __) => _HomeErrorCard(
        title: context.l10n.communityAccountabilityPartner,
        message: context.l10n.accountabilityDashboardLoadFailed,
        onRetry: () => ref.invalidate(accountabilityOverviewProvider),
      ),
    );
  }
}

class _CommunityAccountabilitySurface extends StatelessWidget {
  const _CommunityAccountabilitySurface({required this.data});

  final AccountabilityOverviewInfo data;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final active = data.activePartnership;
    final partnerName = active?.partner?.displayName ??
        active?.initiator?.displayName ??
        context.l10n.accountabilityPartner;
    final hasActive = active != null;

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardSectionShell(
          key: const ValueKey('home-accountability-slot'),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DashboardSectionHeader(
                icon: Icons.handshake_outlined,
                accentColor: scheme.tertiary,
                title: context.l10n.communityAccountabilityPartner,
                summary: hasActive
                    ? context.l10n.accountabilityGrowingTogether
                    : context.l10n.communityPartnerDescription,
                trailing: SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  size: 48,
                  onPressed: () => context.push('/community/accountability'),
                  icon: const Icon(Icons.chevron_right_rounded, size: 18),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              if (!hasActive)
                _HomeEmptyInline(
                  icon: Icons.group_add_outlined,
                  title: context.l10n.communityChooseCorePartner,
                  actionLabel: context.l10n.communityChoosePartner,
                  onAction: () => context.push('/community/accountability'),
                )
              else
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _AccountabilityMiniCard(
                        title: partnerName,
                        subtitle: active.partnerGoal ??
                            (active.initiatorGoal.trim().isEmpty
                                ? context.l10n.accountabilityGoalNotSet
                                : active.initiatorGoal),
                        checkedIn: active.partnerCheckedInToday,
                      ),
                      const SizedBox(width: DS.spacing10),
                      _AccountabilityMiniCard(
                        title: context.l10n.accountabilityMe,
                        subtitle: active.initiatorGoal.trim().isEmpty
                            ? context.l10n.accountabilityGoalNotSet
                            : active.initiatorGoal,
                        checkedIn: active.myCheckedInToday,
                      ),
                      const SizedBox(width: DS.spacing10),
                      ActionChip(
                        avatar: Icon(
                          Icons.notifications_active_outlined,
                          size: 18,
                          color: scheme.primary,
                        ),
                        label: Text(context.l10n.accountabilityNudge),
                        onPressed: () =>
                            context.push('/community/accountability'),
                        backgroundColor: scheme.primaryContainer,
                        labelStyle: textTheme.labelLarge?.copyWith(
                          color: scheme.onPrimaryContainer,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AccountabilityMiniCard extends StatelessWidget {
  const _AccountabilityMiniCard({
    required this.title,
    required this.subtitle,
    required this.checkedIn,
  });

  final String title;
  final String subtitle;
  final bool? checkedIn;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final good = checkedIn ?? false;
    final accent = good ? scheme.primary : scheme.secondary;

    return Semantics(
      label: title,
      child: Container(
        width: 176,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: scheme.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              good
                  ? Icons.check_circle_outline_rounded
                  : Icons.radio_button_unchecked_rounded,
              color: accent,
              size: 20,
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: textTheme.labelLarge?.copyWith(
                color: scheme.onSurface,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              subtitle,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: textTheme.bodySmall?.copyWith(
                color: scheme.onSurfaceVariant,
                height: 1.3,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AttentionSlot extends StatelessWidget {
  const _AttentionSlot({
    required this.bottleneck,
    required this.onOpen,
  });

  final HomeBottleneck bottleneck;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) => ContentConstraint(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing10,
          ),
          child: DashboardSectionShell(
            key: const ValueKey('home-attention-slot'),
            tone: DashboardSurfaceTone.summary,
            padding: const EdgeInsets.all(DS.spacing14),
            child: _CommandCenterRiskBanner(
              text: context.l10n.dashboardBottleneckPrompt(bottleneck.topic),
              onTap: onOpen,
            ),
          ),
        ),
      );
}

class _WeeklyNarrativeSlot extends StatelessWidget {
  const _WeeklyNarrativeSlot();

  @override
  Widget build(BuildContext context) => const ContentConstraint(
        child: Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing10,
          ),
          child: WeeklyGrowthNarrativeCard(),
        ),
      );
}

class _HomeErrorCard extends StatelessWidget {
  const _HomeErrorCard({
    required this.title,
    required this.message,
    required this.onRetry,
  });

  final String title;
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardSectionShell(
          key: const ValueKey('home-slot-error'),
          padding: const EdgeInsets.all(DS.spacing14),
          child: Row(
            children: [
              Icon(Icons.error_outline_rounded, color: scheme.error),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            color: scheme.onSurface,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      message,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: scheme.onSurfaceVariant,
                          ),
                    ),
                  ],
                ),
              ),
              TextButton(
                onPressed: onRetry,
                child: Text(context.l10n.dashboardRetry),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _HomeEmptyInline extends StatelessWidget {
  const _HomeEmptyInline({
    required this.icon,
    required this.title,
    required this.actionLabel,
    required this.onAction,
  });

  final IconData icon;
  final String title;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing14),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Row(
        children: [
          Icon(icon, color: scheme.primary),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: scheme.onSurface,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ),
          TextButton(
            onPressed: onAction,
            child: Text(actionLabel),
          ),
        ],
      ),
    );
  }
}

String _formatDeadlineLabel({
  required BuildContext context,
  required int daysToDeadline,
}) {
  if (daysToDeadline == 0) {
    return context.l10n.dashboardDueToday;
  }

  final absoluteDays = daysToDeadline.abs();
  if (daysToDeadline < 0) {
    return context.l10n.dashboardOverdueDays(absoluteDays);
  }

  return context.l10n.dashboardDaysLeft(daysToDeadline);
}

class _HomeCommandCenterCard extends StatelessWidget {
  const _HomeCommandCenterCard({
    required this.dashboardState,
    required this.growthState,
    required this.isLoading,
    required this.onStartTask,
    required this.onOpenTasks,
    required this.onCreatePlan,
    required this.onOpenAurora,
    this.onOpenBottleneckChat,
  });

  final DashboardState dashboardState;
  final HomeGrowthState? growthState;
  final bool isLoading;
  final ValueChanged<HomeGrowthTask> onStartTask;
  final VoidCallback onOpenTasks;
  final VoidCallback onCreatePlan;
  final VoidCallback onOpenAurora;
  final VoidCallback? onOpenBottleneckChat;

  @override
  Widget build(BuildContext context) {
    final state = growthState;
    final zh = I18nService.instance.isChinese;

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardSectionShell(
          key: const ValueKey('dashboard-command-center'),
          tone: DashboardSurfaceTone.hero,
          child: AnimatedSwitcher(
            duration: DS.quick,
            child: isLoading && state == null
                ? const _CommandCenterSkeleton()
                : _CommandCenterContent(
                    dashboardState: dashboardState,
                    growthState: state ?? const HomeGrowthState.empty(),
                    onStartTask: onStartTask,
                    onOpenTasks: onOpenTasks,
                    onCreatePlan: onCreatePlan,
                    onOpenAurora: onOpenAurora,
                    onOpenBottleneckChat: onOpenBottleneckChat,
                    zh: zh,
                  ),
          ),
        ),
      ),
    );
  }
}

class _CommandCenterContent extends StatelessWidget {
  const _CommandCenterContent({
    required this.dashboardState,
    required this.growthState,
    required this.onStartTask,
    required this.onOpenTasks,
    required this.onCreatePlan,
    required this.onOpenAurora,
    required this.zh,
    this.onOpenBottleneckChat,
  });

  final DashboardState dashboardState;
  final HomeGrowthState growthState;
  final ValueChanged<HomeGrowthTask> onStartTask;
  final VoidCallback onOpenTasks;
  final VoidCallback onCreatePlan;
  final VoidCallback onOpenAurora;
  final VoidCallback? onOpenBottleneckChat;
  final bool zh;

  @override
  Widget build(BuildContext context) {
    final nextTask = growthState.nextAction;
    final priorityTask = dashboardState.mostImportantTask;
    final hasActivePlan = growthState.hasActivePlan;
    final bottleneck = growthState.activeBottleneck;
    final progress = growthState.completionRate;
    final health = growthState.planHealth;
    final planName = growthState.activePlan?.name ??
        dashboardState.activePlanProgress?.name ??
        dashboardState.growth?.name;
    final deadlineDays = priorityTask?.daysToDeadline ??
        dashboardState.nextMoveCard?.daysToDeadline ??
        dashboardState.activePlanProgress?.daysToDeadline;

    final hasRisk = bottleneck != null ||
        (deadlineDays != null && deadlineDays <= 2) ||
        (hasActivePlan && health > 0 && health < 0.45);
    final accentColor = hasRisk
        ? DS.warning
        : nextTask != null
            ? DS.brandPrimary
            : hasActivePlan
                ? DS.success
                : DS.info;
    final title = _title(nextTask, priorityTask, hasActivePlan);
    final summary = _summary(context, nextTask, priorityTask, hasActivePlan);
    final riskText = _riskText(context, bottleneck, deadlineDays, health);

    return Column(
      key: const ValueKey('dashboard-command-center-content'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: accentColor.withValues(alpha: 0.12),
                borderRadius: DS.borderRadius16,
                border: Border.all(color: accentColor.withValues(alpha: 0.18)),
              ),
              child: Icon(
                hasRisk
                    ? Icons.priority_high_rounded
                    : nextTask != null
                        ? Icons.play_arrow_rounded
                        : Icons.auto_awesome_rounded,
                color: accentColor,
                size: 22,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    zh ? '现在的指挥台' : 'Command Center',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: context.sparkleTypography.titleLarge.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                      height: 1.18,
                    ),
                  ),
                  if (summary.isNotEmpty) ...[
                    const SizedBox(height: DS.spacing6),
                    Text(
                      summary,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: context.sparkleTypography.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.35,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing14),
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: [
            _DashboardChip(
              icon: Icons.task_alt_rounded,
              label: growthState.hasTasks
                  ? '${growthState.tasksCompleted}/${growthState.tasksTotal}'
                  : (zh ? '今天未排任务' : 'No tasks today'),
            ),
            if (hasActivePlan)
              _DashboardChip(
                icon: Icons.timeline_rounded,
                label: zh
                    ? '健康度 ${(health * 100).round()}%'
                    : '${(health * 100).round()}% health',
              ),
            if (planName != null && planName.trim().isNotEmpty)
              _DashboardChip(
                icon: Icons.flag_rounded,
                label: planName,
              ),
            if (deadlineDays != null)
              _DashboardChip(
                icon: Icons.timelapse_rounded,
                label: _formatDeadlineLabel(
                  context: context,
                  daysToDeadline: deadlineDays,
                ),
              ),
          ],
        ),
        if (growthState.hasTasks || dashboardState.activePlanProgress != null)
          Padding(
            padding: const EdgeInsets.only(top: DS.spacing12),
            child: ClipRRect(
              borderRadius: DS.borderRadiusFull,
              child: LinearProgressIndicator(
                minHeight: 8,
                value: progress > 0
                    ? progress.clamp(0, 1)
                    : (dashboardState.activePlanProgress?.progress ?? 0)
                        .clamp(0, 1),
                backgroundColor: DS.surfaceOverlay,
                valueColor: AlwaysStoppedAnimation<Color>(accentColor),
              ),
            ),
          ),
        if (riskText != null) ...[
          const SizedBox(height: DS.spacing12),
          _CommandCenterRiskBanner(
            text: riskText,
            onTap: onOpenBottleneckChat ?? onOpenAurora,
          ),
        ],
        const SizedBox(height: DS.spacing14),
        LayoutBuilder(
          builder: (context, constraints) {
            final primary = SparkleButton.primary(
              label: nextTask != null
                  ? context.l10n.dashboardStartHere
                  : hasActivePlan
                      ? context.l10n.dashboardOpenTasks
                      : context.l10n.dashboardStartWithAI,
              icon: Icon(
                nextTask != null
                    ? Icons.play_arrow_rounded
                    : hasActivePlan
                        ? Icons.list_alt_rounded
                        : Icons.auto_awesome_rounded,
              ),
              onPressed: nextTask != null
                  ? () => onStartTask(nextTask)
                  : hasActivePlan
                      ? onOpenTasks
                      : onCreatePlan,
            );
            final secondary = SparkleButton.ghost(
              label: zh ? '问 Aurora' : 'Ask Aurora',
              icon: const Icon(Icons.chat_bubble_outline_rounded),
              onPressed: onOpenAurora,
            );

            if (constraints.maxWidth < 360) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  primary,
                  const SizedBox(height: DS.spacing10),
                  secondary,
                ],
              );
            }

            return Row(
              children: [
                Expanded(child: primary),
                const SizedBox(width: DS.spacing10),
                Expanded(child: secondary),
              ],
            );
          },
        ),
      ],
    );
  }

  String _title(
    HomeGrowthTask? nextTask,
    PriorityTaskData? priorityTask,
    bool hasActivePlan,
  ) {
    if (nextTask != null) {
      return nextTask.title;
    }
    if (priorityTask != null && priorityTask.title.trim().isNotEmpty) {
      return priorityTask.title;
    }
    if (hasActivePlan && growthState.hasTasks) {
      return zh ? '今天的任务已经清楚了' : 'Today is mapped out';
    }
    if (hasActivePlan) {
      return zh ? '先检查今天的计划节奏' : 'Check today plan rhythm';
    }
    return zh ? '先定一个今天能开始的目标' : 'Set a goal you can start today';
  }

  String _summary(
    BuildContext context,
    HomeGrowthTask? nextTask,
    PriorityTaskData? priorityTask,
    bool hasActivePlan,
  ) {
    if (nextTask != null) {
      final due = nextTask.dueDate;
      final dueText = due == null
          ? null
          : _formatDeadlineLabel(
              context: context,
              daysToDeadline: DateTime(
                due.year,
                due.month,
                due.day,
              )
                  .difference(
                    DateTime(
                      DateTime.now().year,
                      DateTime.now().month,
                      DateTime.now().day,
                    ),
                  )
                  .inDays,
            );
      return [
        if (dueText != null) dueText,
        if (nextTask.isHighPriority && zh) '高优先级',
        if (nextTask.isHighPriority && !zh) 'High priority',
        if (zh) '完成后会更新计划进度',
        if (!zh) 'Completing it updates your plan progress',
      ].join(' - ');
    }
    if (priorityTask != null && priorityTask.reason.trim().isNotEmpty) {
      return priorityTask.reason;
    }
    if (hasActivePlan && growthState.tasksCompleted >= growthState.tasksTotal) {
      return zh
          ? '今天没有更急的动作。可以复盘、补资料，或让 Aurora 重新排一下。'
          : 'No urgent action is queued. Review, add context, or let Aurora reprioritize.';
    }
    return dashboardState.nextMoveCard?.summary ??
        (zh
            ? 'Sparkle 会把目标拆成下一步、进度和风险提醒。'
            : 'Sparkle will turn it into a next step, progress, and risk signal.');
  }

  String? _riskText(
    BuildContext context,
    HomeBottleneck? bottleneck,
    int? deadlineDays,
    double health,
  ) {
    if (bottleneck != null) {
      return zh
          ? '风险：${bottleneck.topic} 正在卡住进度'
          : 'Risk: ${bottleneck.topic} is slowing progress';
    }
    if (deadlineDays != null && deadlineDays <= 2) {
      return zh
          ? '风险：${_formatDeadlineLabel(context: context, daysToDeadline: deadlineDays)}'
          : 'Risk: ${_formatDeadlineLabel(context: context, daysToDeadline: deadlineDays)}';
    }
    if (health > 0 && health < 0.45) {
      return zh
          ? '风险：计划健康度偏低，需要重新校准'
          : 'Risk: plan health is low; recalibration may help';
    }
    return null;
  }
}

class _CommandCenterRiskBanner extends StatelessWidget {
  const _CommandCenterRiskBanner({
    required this.text,
    required this.onTap,
  });

  final String text;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing10,
          ),
          decoration: BoxDecoration(
            color: DS.warning.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: DS.warning.withValues(alpha: 0.18)),
          ),
          child: Row(
            children: [
              Icon(
                Icons.warning_amber_rounded,
                color: DS.warning,
                size: 18,
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  text,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: context.sparkleTypography.bodySmall.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightMedium,
                    height: 1.3,
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Icon(
                Icons.chevron_right_rounded,
                color: DS.textSecondary,
                size: 18,
              ),
            ],
          ),
        ),
      );
}

class _CommandCenterSkeleton extends StatelessWidget {
  const _CommandCenterSkeleton();

  @override
  Widget build(BuildContext context) => const Column(
        key: ValueKey('dashboard-command-center-skeleton'),
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SparkleSkeleton(width: 44, height: 44, borderRadius: 16),
              SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SparkleSkeleton(width: 112, height: 12, borderRadius: 6),
                    SizedBox(height: DS.spacing8),
                    SparkleSkeleton(height: 22, borderRadius: 11),
                    SizedBox(height: DS.spacing8),
                    SparkleSkeleton(width: 220, height: 14, borderRadius: 7),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: DS.spacing14),
          SparkleSkeleton(height: 8, borderRadius: 4),
          SizedBox(height: DS.spacing14),
          Row(
            children: [
              Expanded(child: SparkleSkeleton(height: 38, borderRadius: 19)),
              SizedBox(width: DS.spacing10),
              Expanded(child: SparkleSkeleton(height: 38, borderRadius: 19)),
            ],
          ),
        ],
      );
}

class _DailyBriefingCard extends StatelessWidget {
  const _DailyBriefingCard({
    required this.dashboardState,
    required this.isExpanded,
    required this.onToggleExpanded,
  });

  final DashboardState dashboardState;
  final bool isExpanded;
  final VoidCallback onToggleExpanded;

  @override
  Widget build(BuildContext context) {
    final observation = dashboardState.whatChangedCard;
    final growthStatus = dashboardState.growthStatus;
    final nextMove = dashboardState.nextMoveCard;
    final task = dashboardState.mostImportantTask;
    final growthSignal = dashboardState.growthSignal;
    final activePlan = dashboardState.activePlanProgress;
    final nextActionCount = dashboardState.nextActions.length;

    final hasObservation = observation != null || growthStatus != null;
    final hasNextMove = nextMove != null || task != null;
    final hasDetailSection = growthSignal != null || activePlan != null;

    if (!hasObservation && !hasNextMove && !hasDetailSection) {
      return const SizedBox.shrink();
    }

    final observationTitle = observation?.headline ?? growthStatus?.headline;
    final observationSummary = observation?.summary ?? growthStatus?.subtitle;
    final nextTitle = nextMove?.headline ?? task?.title;
    final nextSummary = nextMove?.summary ?? task?.reason;
    final estimatedMinutes =
        nextMove?.estimatedMinutes ?? task?.estimatedMinutes;
    final planName = nextMove?.planName ?? task?.planName;
    final daysToDeadline = nextMove?.daysToDeadline ?? task?.daysToDeadline;
    final taskId = nextMove?.taskId ?? task?.id;

    final summaryBits = <String>[
      if (hasNextMove) context.l10n.dashboardMainMove,
      if (nextActionCount > 1)
        context.l10n.dashboardMoreQueued(nextActionCount - 1),
      if (activePlan != null)
        context.l10n.dashboardProgress((activePlan.progress * 100).round()),
    ];

    return ContentConstraint(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing10,
        ),
        child: DashboardSectionShell(
          key: const ValueKey('dashboard-briefing-section'),
          tone: DashboardSurfaceTone.hero,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              DashboardSectionHeader(
                icon: Icons.auto_awesome_rounded,
                iconSize: 40,
                accentColor: DS.brandPrimary,
                title: context.l10n.dashboardTodayBriefing,
                summary: summaryBits.isEmpty
                    ? context.l10n.dashboardBriefingSummary
                    : summaryBits.join(' • '),
                trailing: SparkleIconButton(
                  key: const ValueKey('dashboard-briefing-toggle'),
                  variant: ButtonVariant.ghost,
                  size: 48,
                  onPressed: onToggleExpanded,
                  icon: AnimatedRotation(
                    turns: isExpanded ? 0.5 : 0,
                    duration: DS.durationFast,
                    child: const Icon(
                      Icons.expand_more_rounded,
                      size: 18,
                    ),
                  ),
                ),
              ),
              ClipRect(
                child: AnimatedSize(
                  duration: DS.quick,
                  curve: DS.motionCurve(SparkleMotionToken.standard),
                  alignment: Alignment.topCenter,
                  child: !isExpanded
                      ? const SizedBox.shrink()
                      : Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (hasObservation) ...[
                              const SizedBox(height: DS.spacing12),
                              _BriefingBlock(
                                eyebrow:
                                    context.l10n.dashboardSparkleObservation,
                                title: observationTitle ?? '',
                                summary: observationSummary ?? '',
                              ),
                            ],
                            if (hasNextMove) ...[
                              const SizedBox(height: DS.spacing12),
                              _BriefingBlock(
                                eyebrow: context.l10n.dashboardStartWithThis,
                                title: nextTitle ?? '',
                                summary: nextSummary ?? '',
                                footer: Wrap(
                                  spacing: DS.spacing8,
                                  runSpacing: DS.spacing8,
                                  children: [
                                    if (estimatedMinutes != null &&
                                        estimatedMinutes > 0)
                                      _DashboardChip(
                                        icon: Icons.schedule_rounded,
                                        label: '$estimatedMinutes min',
                                      ),
                                    if (planName != null && planName.isNotEmpty)
                                      _DashboardChip(
                                        icon: Icons.flag_rounded,
                                        label: planName,
                                      ),
                                    if (daysToDeadline != null)
                                      _DashboardChip(
                                        icon: Icons.timelapse_rounded,
                                        label: _formatDeadlineLabel(
                                          context: context,
                                          daysToDeadline: daysToDeadline,
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            ],
                            const SizedBox(height: DS.spacing12),
                            _BriefingActions(
                              hasTaskAction:
                                  taskId != null && taskId.isNotEmpty,
                              taskId: taskId,
                            ),
                            if (growthSignal != null)
                              Padding(
                                padding:
                                    const EdgeInsets.only(top: DS.spacing12),
                                child: _BriefingDetailTile(
                                  icon: Icons.trending_up_rounded,
                                  iconColor: DS.success,
                                  title: context.l10n.dashboardGrowthSignal,
                                  headline: growthSignal.headline,
                                  summary: growthSignal.summary,
                                  trailing: growthSignal.source,
                                ),
                              ),
                            if (growthSignal != null && activePlan != null)
                              const SizedBox(height: DS.spacing10),
                            if (activePlan != null)
                              Padding(
                                padding:
                                    const EdgeInsets.only(top: DS.spacing10),
                                child: _PlanProgressTile(
                                  plan: activePlan,
                                ),
                              ),
                            if (nextActionCount > 1) ...[
                              const SizedBox(height: DS.spacing12),
                              Text(
                                context.l10n.dashboardMoreTasksQueued(
                                  nextActionCount - 1,
                                ),
                                style: context.sparkleTypography.bodySmall
                                    .copyWith(
                                  color: DS.textSecondary,
                                  height: 1.35,
                                ),
                              ),
                            ],
                            const SizedBox(height: DS.spacing12),
                            Wrap(
                              spacing: DS.spacing10,
                              runSpacing: DS.spacing10,
                              children: [
                                SparkleButton.ghost(
                                  label: context.l10n.dashboardStartFocus,
                                  onPressed: () => context.push('/focus'),
                                ),
                                SparkleButton.ghost(
                                  label: 'Chat',
                                  onPressed: () => context.go('/chat'),
                                ),
                              ],
                            ),
                          ],
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

class _BriefingBlock extends StatelessWidget {
  const _BriefingBlock({
    required this.eyebrow,
    required this.title,
    required this.summary,
    this.footer,
  });

  final String eyebrow;
  final String title;
  final String summary;
  final Widget? footer;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.82),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              eyebrow,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              title,
              style: context.sparkleTypography.titleLarge.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            if (summary.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                summary,
                style: context.sparkleTypography.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.35,
                ),
              ),
            ],
            if (footer != null) ...[
              const SizedBox(height: DS.spacing12),
              footer!,
            ],
          ],
        ),
      );
}

class _BriefingActions extends StatelessWidget {
  const _BriefingActions({
    required this.hasTaskAction,
    required this.taskId,
  });

  final bool hasTaskAction;
  final String? taskId;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final primaryButton = SparkleButton.primary(
            label: hasTaskAction
                ? context.l10n.dashboardStartHere
                : context.l10n.dashboardOpenTasks,
            onPressed: () => hasTaskAction
                ? context.push('/tasks/$taskId')
                : context.push('/tasks'),
          );
          final secondaryButton = SparkleButton.ghost(
            label: context.l10n.dashboardTaskList,
            onPressed: () => context.push('/tasks'),
          );

          if (constraints.maxWidth < 360) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                primaryButton,
                const SizedBox(height: DS.spacing10),
                secondaryButton,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: primaryButton),
              const SizedBox(width: DS.spacing10),
              Expanded(child: secondaryButton),
            ],
          );
        },
      );
}

class _BriefingDetailTile extends StatelessWidget {
  const _BriefingDetailTile({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.headline,
    required this.summary,
    this.trailing,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String headline;
  final String summary;
  final String? trailing;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.72),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, size: 18, color: iconColor),
            ),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    headline,
                    style: context.sparkleTypography.labelLarge.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    summary,
                    style: context.sparkleTypography.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.35,
                    ),
                  ),
                ],
              ),
            ),
            if (trailing != null && trailing!.isNotEmpty) ...[
              const SizedBox(width: DS.spacing8),
              Flexible(
                child: Text(
                  trailing!,
                  textAlign: TextAlign.right,
                  style: context.sparkleTypography.labelSmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ),
            ],
          ],
        ),
      );
}

class _PlanProgressTile extends StatelessWidget {
  const _PlanProgressTile({
    required this.plan,
  });

  final ActivePlanProgressData plan;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.72),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    context.l10n.dashboardActivePlan,
                    style: context.sparkleTypography.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
                Text(
                  '${(plan.progress * 100).round()}%',
                  style: context.sparkleTypography.labelLarge.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              plan.name,
              style: context.sparkleTypography.labelLarge.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            ClipRRect(
              borderRadius: DS.borderRadiusFull,
              child: LinearProgressIndicator(
                minHeight: 8,
                value: plan.progress.clamp(0, 1),
                backgroundColor: DS.surfaceOverlay,
                valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.dashboardPhaseLabel(
                plan.phase.isEmpty
                    ? context.l10n.dashboardPhaseInProgress
                    : plan.phase,
              ),
              style: context.sparkleTypography.bodySmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
            if (plan.daysToDeadline != null) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                context.l10n.dashboardDaysToDeadline(plan.daysToDeadline!),
                style: context.sparkleTypography.bodySmall.copyWith(
                  color: DS.textSecondary,
                ),
              ),
            ],
          ],
        ),
      );
}

class _DashboardUpdatesSection extends ConsumerStatefulWidget {
  const _DashboardUpdatesSection();

  @override
  ConsumerState<_DashboardUpdatesSection> createState() =>
      _DashboardUpdatesSectionState();
}

class _DashboardUpdatesSectionState
    extends ConsumerState<_DashboardUpdatesSection> {
  bool _isExpanded = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = ref.read(notificationCenterProvider);
      if (!state.isLoading && state.notifications.isEmpty) {
        unawaited(
          ref.read(notificationCenterProvider.notifier).loadNotifications(),
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final unreadMessages = ref.watch(unreadMessageCountProvider);
    final unreadNotifications =
        ref.watch(unreadNotificationsProvider).maybeWhen(
              data: (notifications) => notifications.length,
              orElse: () => 0,
            );
    final notificationCenterState = ref.watch(notificationCenterProvider);
    final systemUpdates = ref.watch(systemUpdatesProvider).maybeWhen(
          data: (items) => items,
          orElse: () => const <Map<String, dynamic>>[],
        );
    final reviewAsync = ref.watch(nightlyReviewProvider);

    final insightCount = _recentInsightCount(
      notificationCenterState.notifications,
      systemUpdates,
    );
    final hasPendingReview = reviewAsync.maybeWhen(
      data: (review) =>
          review != null &&
          review.widgetPayload != null &&
          review.status != 'reviewed',
      orElse: () => false,
    );
    final hasPrediction = dashboardState.nextIntentForecast != null &&
        dashboardState.nextIntentForecast!.title.isNotEmpty &&
        dashboardState.nextIntentForecast!.summary.isNotEmpty;

    final summaryBits = <String>[
      if (hasPrediction) context.l10n.dashboardPrediction,
      if (unreadMessages > 0)
        context.l10n.dashboardMessagesCount(unreadMessages),
      if (unreadNotifications > 0)
        context.l10n.dashboardAlertsCount(unreadNotifications),
      if (insightCount > 0) context.l10n.dashboardInsightsCount(insightCount),
      if (hasPendingReview) context.l10n.dashboardReviewPending,
    ];

    if (summaryBits.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        ContentConstraint(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              0,
              DS.spacing16,
              DS.spacing4,
            ),
            child: DashboardSectionShell(
              key: const ValueKey('dashboard-updates-section'),
              tone: DashboardSurfaceTone.summary,
              padding: const EdgeInsets.all(14),
              child: InkWell(
                onTap: _toggleExpanded,
                borderRadius: DS.borderRadius16,
                child: DashboardSectionHeader(
                  icon: Icons.notifications_active_outlined,
                  accentColor: DS.info,
                  title: context.l10n.dashboardUpdatesInsights,
                  summary: summaryBits.take(3).join(' • '),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      _SectionCountPill(count: summaryBits.length),
                      const SizedBox(width: DS.spacing8),
                      SparkleIconButton(
                        key: const ValueKey('dashboard-updates-toggle'),
                        variant: ButtonVariant.ghost,
                        size: 48,
                        onPressed: _toggleExpanded,
                        icon: AnimatedRotation(
                          turns: _isExpanded ? 0.5 : 0,
                          duration: DS.durationFast,
                          child: const Icon(
                            Icons.expand_more_rounded,
                            size: 18,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
        ClipRect(
          child: AnimatedSize(
            duration: DS.quick,
            curve: DS.motionCurve(SparkleMotionToken.standard),
            alignment: Alignment.topCenter,
            child: !_isExpanded
                ? const SizedBox.shrink()
                : const Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      PredictedIntentCard(),
                      HomeNotificationCard(),
                      RecentInsightsCard(),
                      NightlyReviewPanel(compact: true),
                    ],
                  ),
          ),
        ),
      ],
    );
  }

  int _recentInsightCount(
    List<UnifiedNotification> notifications,
    List<Map<String, dynamic>> systemUpdates,
  ) {
    final totalNotifications = notifications.where((item) {
      final type = item.type?.toString() ?? '';
      return type.startsWith('theater_') ||
          type == 'learning_report_ready' ||
          type == 'simulation_session_ready';
    }).length;

    final totalSystemUpdates = systemUpdates.where((item) {
      final type = item['type']?.toString() ?? '';
      return type.startsWith('theater_') ||
          type == 'learning_report_ready' ||
          type == 'simulation_session_ready';
    }).length;

    return totalNotifications + totalSystemUpdates;
  }

  void _toggleExpanded() {
    setState(() {
      _isExpanded = !_isExpanded;
    });
  }
}

class _SectionCountPill extends StatelessWidget {
  const _SectionCountPill({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Text(
          '$count',
          style: context.sparkleTypography.labelSmall.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

class _DashboardChip extends StatelessWidget {
  const _DashboardChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: context.sparkleTypography.labelSmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
      );
}

class _GoalChip extends StatelessWidget {
  const _GoalChip({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 44),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: DS.brandPrimary.withValues(alpha: 0.2),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 15, color: DS.brandPrimary),
                const SizedBox(width: 6),
                Text(
                  label,
                  style: DS.labelSmall.copyWith(
                    color: DS.brandPrimary,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _OnboardingQuickCard extends StatelessWidget {
  const _OnboardingQuickCard({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: title,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: DS.borderRadius12,
          child: Container(
            padding: const EdgeInsets.all(DS.spacing14),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.06),
              borderRadius: DS.borderRadius12,
              border: Border.all(color: color.withValues(alpha: 0.15)),
            ),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: DS.borderRadius8,
                  ),
                  child: Icon(icon, color: color, size: 22),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: TextStyle(
                          fontSize: DS.fontSizeBase,
                          fontWeight: DS.fontWeightSemibold,
                          color: DS.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        subtitle,
                        style: TextStyle(
                          fontSize: DS.fontSizeSm,
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                Icon(Icons.chevron_right, color: color.withValues(alpha: 0.4)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
