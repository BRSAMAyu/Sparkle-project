import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
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
import 'package:sparkle/features/goal/goal_routes.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_slot_config_provider.dart';
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
import 'package:sparkle/features/home/presentation/widgets/onboarding_resume_card.dart';
import 'package:sparkle/features/home/presentation/widgets/predicted_intent_card.dart';
import 'package:sparkle/features/home/presentation/widgets/recent_insights_card.dart';
import 'package:sparkle/features/home/presentation/widgets/stuck_recovery_card.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_board_card.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/features/home/presentation/widgets/understanding_panel.dart';
import 'package:sparkle/features/home/presentation/widgets/unified_omni_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_header.dart';
import 'package:sparkle/features/insights/presentation/widgets/return_case_file_card.dart';
import 'package:sparkle/features/insights/presentation/widgets/weekly_growth_narrative_card.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/reviews/presentation/widgets/nightly_review_panel.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';

String _goalDetailLocation(String? goalId) {
  final normalized = goalId?.trim();
  if (normalized == null || normalized.isEmpty) {
    return '/plans';
  }
  return GoalRoutes.detailLocation(Uri.encodeComponent(normalized));
}

/// Shows a text input dialog for freeform Aurora correction.
/// Returns trimmed text only when the user submits; cancel returns null.
Future<String?> showAuroraFreeformCorrectionInputDialog(BuildContext context) {
  final controller = TextEditingController();
  final focusNode = FocusNode();
  final l10n = AppLocalizations.of(context)!;

  return showDialog<String?>(
    context: context,
    builder: (ctx) {
      String? submittedText() {
        final text = controller.text.trim();
        return text.isEmpty ? null : text;
      }

      return AlertDialog(
        title: Text(l10n.homeAuroraDialogTitle),
        content: TextField(
          controller: controller,
          focusNode: focusNode,
          autofocus: true,
          maxLines: 3,
          minLines: 2,
          decoration: InputDecoration(
            hintText: l10n.homeAuroraDialogHint,
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
                    SparkleButton(
            label: l10n.homeAuroraDialogCancel,
            variant: ButtonVariant.text,
            size: ButtonSize.small,
            minWidth: 64,
            minHeight: 40,
            onPressed: () => Navigator.of(ctx).pop(),
          ),
                    SparkleButton(
            label: l10n.homeAuroraDialogSend,
            minWidth: 64,
            minHeight: 40,
            onPressed: () => Navigator.of(ctx).pop(submittedText()),
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

  // J-03：原 `_shouldShowFirstGoalEmptyState` / `_buildFirstGoalEmptyState` /
  // `_buildOnboardingWelcome`（三处互相竞争的引导卡面，合计 3+ 个 CTA）
  // 由 TodayCockpitCard 的 no-goal / fresh 态统一承接（见下方
  // growthSections 与 hasNoGoals 分支），首屏引导面收敛为唯一主卡。

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

  // J-03：`_startNextAction`（原 Command Center 启动任务链路）已迁至
  // today_cockpit_card.dart 的 `_CockpitContent._startTask`，链路不变
  // （/tasks/today → activeTaskProvider → /tasks/{id}/execute）。

  List<Widget> _buildDashboardSkeletonSections() => const [
        // CompactStatusBar skeleton — short wide bar
        Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing8,
            DS.spacing16,
            DS.spacing10,
          ),
          child: SizedBox(
            height: 48,
            child: SparkleCardSkeleton(),
          ),
        ),
        // AuroraStatusBand skeleton — thin strip
        Padding(
          padding: EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing4,
          ),
          child: SizedBox(
            height: 40,
            child: SparkleCardSkeleton(),
          ),
        ),
        // Goal switcher + daily context
        Padding(
          padding: EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing12,
            DS.spacing16,
            DS.spacing8,
          ),
          child: SparkleCardSkeleton(),
        ),
        // Command center skeleton
        Padding(
          padding: EdgeInsets.symmetric(horizontal: DS.spacing16),
          child: SizedBox(
            height: 120,
            child: SparkleCardSkeleton(),
          ),
        ),
        // Goal detail / return case file
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
        // J-03：Command Center 由 TodayCockpitCard 收编（唯一主行动卡）。
        // 主渲染路径在 growthSections 顶部；slot walk 仍会跳过该 id
        // （DASH-01），此处仅为编辑面板/兜底渲染保持一致。
        return const TodayCockpitCard();
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
          onOpenGoal: (goalId) => unawaited(
            context.push(_goalDetailLocation(goalId)),
          ),
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
            title: context.l10n.dashboardExamSprintSlotTitle,
            body: context.l10n.dashboardExamSprintSlotBody,
            actionLabel: context.l10n.dashboardExamSprintSlotAction,
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
          onStartDiagnostic: () {
            unawaited(
              context.push(
                '/exam-sprint/diagnose?subject=${Uri.encodeComponent(examSprintDashboard.subject.isEmpty ? '计算机网络' : examSprintDashboard.subject)}',
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
    final l10n = I18nService.instance.l10n;
    switch (slotId) {
      case DashboardSlotIds.dailyBriefing:
        final actions = dashboardState.nextActions.length;
        return _SlotMeta(
          title: l10n.dashboardSlotDailyBriefing,
          icon: Icons.wb_sunny_outlined,
          summary: actions > 0
              ? l10n.dashboardSlotDailyBriefingReady(actions)
              : l10n.dashboardSlotDailyBriefingEmpty,
          accent: DS.brandPrimary,
        );
      case DashboardSlotIds.metricsRow:
        final streak =
            growthState?.streak ?? dashboardState.growthStatus?.streakDays ?? 0;
        return _SlotMeta(
          title: l10n.dashboardSlotKeyMetrics,
          icon: Icons.insights_rounded,
          summary: streak > 0
              ? l10n.dashboardSlotKeyMetricsStreak(streak)
              : l10n.dashboardSlotKeyMetricsEmpty,
          accent: DS.info,
        );
      case DashboardSlotIds.commandCenter:
        final nextLabel = growthState?.nextAction?.title ??
            (dashboardState.nextActions.isNotEmpty
                ? dashboardState.nextActions.first.title
                : '');
        return _SlotMeta(
          title: l10n.dashboardSlotCommandCenter,
          icon: Icons.bolt_rounded,
          summary: nextLabel.isNotEmpty
              ? l10n.dashboardSlotCommandCenterNext(nextLabel)
              : l10n.dashboardSlotCommandCenterEmpty,
          accent: DS.brandPrimary,
        );
      case DashboardSlotIds.understanding:
        return _SlotMeta(
          title: l10n.dashboardSlotUnderstanding,
          icon: Icons.psychology_outlined,
          summary: l10n.dashboardSlotUnderstandingSummary,
          accent: DS.info,
        );
      case DashboardSlotIds.returnCaseFile:
        return _SlotMeta(
          title: l10n.dashboardSlotReturnCaseFile,
          icon: Icons.history_edu_rounded,
          summary: l10n.dashboardSlotReturnCaseSummary,
          accent: DS.warning,
        );
      case DashboardSlotIds.goalDetailSnapshot:
        final goal = dashboardState.growth;
        return _SlotMeta(
          title: l10n.dashboardSlotGoalDetail,
          icon: Icons.flag_outlined,
          summary: goal != null
              ? '${goal.name} · ${(goal.progress * 100).round()}%'
              : l10n.dashboardSlotGoalDetailSummary,
          accent: DS.success,
        );
      case DashboardSlotIds.multiGoalDashboard:
        final tasksTotal = growthState?.tasksTotal ?? 0;
        final tasksDone = growthState?.tasksCompleted ?? 0;
        return _SlotMeta(
          title: l10n.dashboardSlotMultiGoal,
          icon: Icons.dashboard_customize_outlined,
          summary: tasksTotal > 0
              ? l10n.dashboardSlotMultiGoalProgress(tasksDone, tasksTotal)
              : l10n.dashboardSlotMultiGoalEmpty,
          accent: DS.brandPrimary,
        );
      case DashboardSlotIds.taskBoard:
        final total = growthState?.tasksTotal ?? 0;
        final done = growthState?.tasksCompleted ?? 0;
        return _SlotMeta(
          title: l10n.dashboardSlotTaskBoard,
          icon: Icons.checklist_rounded,
          summary: total > 0
              ? l10n.dashboardSlotTaskBoardDone(done, total, done == total
                  ? l10n.dashboardSlotTaskBoardGoalHit
                  : l10n.dashboardSlotTaskBoardToGo(total - done),)
              : l10n.dashboardSlotTaskBoardEmpty,
          accent: DS.success,
        );
      case DashboardSlotIds.examSprint:
        if (examSprintDashboard != null) {
          return _SlotMeta(
            title: l10n.dashboardSlotExamSprint,
            icon: Icons.local_fire_department_outlined,
            summary: l10n.dashboardSlotExamSprintActive(examSprintDashboard.subject, examSprintDashboard.daysLeft),
            accent: DS.warning,
          );
        }
        return _SlotMeta(
          title: l10n.dashboardSlotExamSprint,
          icon: Icons.local_fire_department_outlined,
          summary: l10n.dashboardSlotExamSprintEmpty,
          accent: DS.warning,
        );
      case DashboardSlotIds.dashboardUpdates:
        return _SlotMeta(
          title: l10n.dashboardSlotUpdates,
          icon: Icons.notifications_outlined,
          summary: l10n.dashboardSlotUpdatesSummary,
          accent: DS.info,
        );
      case DashboardSlotIds.growthQuality:
        return _SlotMeta(
          title: l10n.dashboardSlotGrowthQuality,
          icon: Icons.trending_up_rounded,
          summary: l10n.dashboardSlotGrowthQualitySummary,
          accent: DS.success,
        );
      case DashboardSlotIds.weeklyNarrative:
        return _SlotMeta(
          title: l10n.dashboardSlotWeeklyNarrative,
          icon: Icons.menu_book_outlined,
          summary: l10n.dashboardSlotWeeklyNarrativeSummary,
          accent: DS.info,
        );
      case DashboardSlotIds.community:
        return _SlotMeta(
          title: l10n.dashboardSlotCommunity,
          icon: Icons.group_outlined,
          summary: l10n.dashboardSlotCommunitySummary,
          accent: DS.brandPrimary,
        );
      case DashboardSlotIds.achievementProgress:
        return _SlotMeta(
          title: l10n.dashboardSlotAchievements,
          icon: Icons.emoji_events_outlined,
          summary: l10n.dashboardSlotAchievementsSummary,
          accent: DS.warning,
        );
      case DashboardSlotIds.learningHeatmap:
        return _SlotMeta(
          title: l10n.dashboardSlotHeatmap,
          icon: Icons.calendar_view_month_rounded,
          summary: l10n.dashboardSlotHeatmapSummary,
          accent: DS.info,
        );
      case DashboardSlotIds.workspaceCards:
        return _SlotMeta(
          title: l10n.dashboardSlotWorkspace,
          icon: Icons.view_module_outlined,
          summary: workspaceCardCount > 0
              ? l10n.dashboardSlotWorkspaceVisible(workspaceCardCount)
              : l10n.dashboardSlotWorkspaceEmpty,
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
    final l10n = I18nService.instance.l10n;
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
                      l10n.dashboardEmptyTitle,
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
                l10n.dashboardEmptyBody,
                style: DS.bodySmall.copyWith(color: DS.textSecondary),
              ),
              const SizedBox(height: DS.spacing16),
              SparkleButton.primary(
                label: l10n.dashboardCustomizeButton,
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
    required String title,
    required String body,
    required String actionLabel,
    required VoidCallback onAction,
  }) => Padding(
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
                    title,
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
              body,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing12),
            Align(
              alignment: Alignment.centerLeft,
              child: SparkleButton.ghost(
                label: actionLabel,
                onPressed: onAction,
              ),
            ),
          ],
        ),
      ),
    );

  /// Quiet end-of-list discovery affordance for the dashboard editor.
  /// Long-press on any slot still opens the same sheet, but this footer
  /// is the "I want to find the settings" path for users who don't
  /// know about long-press.
  Widget _buildCustomizeFooter() {
    final l10n = I18nService.instance.l10n;
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
            l10n.dashboardCustomizeButton,
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
    // J-03 信息层级（v3/03_modules/HOME.md）：
    // 1. TodayCockpitCard = 唯一 Primary Action（含 why/stuck/current run）；
    // 2. goal context（cockpit 内 chips + GoalSwitcherBand 紧随其后）；
    // 3. 「我卡住了」在 cockpit 卡内作次级入口；
    // 4. 次要 upcoming / daily context；
    // 5. Aurora understanding receipt 下移至首屏末尾，不再与主行动抢注意力。
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
              child: const TodayCockpitCard(),
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
              child: const ReturnCaseFileCard(),
            ),
            _staggeredSection(
              index: growthSectionIndex++,
              child: GoalDetailSnapshotCard(
                onOpenGoal: (goalId) => unawaited(
                  context.push(_goalDetailLocation(goalId)),
                ),
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
                  onStartDiagnostic: () {
                    unawaited(
                      context.push(
                        '/exam-sprint/diagnose?subject=${Uri.encodeComponent(examSprintDashboard.subject.isEmpty ? '计算机网络' : examSprintDashboard.subject)}',
                      ),
                    );
                  },
                ),
              ),
            // HOME.md 第 5 层：Aurora understanding receipt —— 有用的一条
            // 理解回执，置于首屏行动区之后，而非堆在主行动上方。
            _staggeredSection(
              index: growthSectionIndex++,
              child: ContentConstraint(
                child: UnderstandingSnapshotCard(
                  onOpenChat: () => unawaited(context.push(ChatRoutes.chat)),
                ),
              ),
            ),
          ];

    var sectionIndex = growthSections.length;
    final dashboardSections = <Widget>[];
    if (dashboardState.error != null) {
      final failureKind = dashboardState.failure?.kind ??
          FailureKindCode.fromCode(dashboardState.failure?.errorCode);
      final l10n = I18nService.instance.l10n;
      final failureIcon = switch (failureKind) {
        FailureKind.auth => Icons.lock_outline_rounded,
        FailureKind.server => Icons.cloud_sync_outlined,
        FailureKind.validation => Icons.edit_note_rounded,
        FailureKind.network || FailureKind.offline => Icons.wifi_off_rounded,
        FailureKind.unknown => Icons.cloud_off_outlined,
      };
      final failureTitle = switch (failureKind) {
        FailureKind.auth => l10n.dashboardErrorAuth,
        FailureKind.server => l10n.dashboardErrorServer,
        FailureKind.validation => l10n.dashboardErrorValidation,
        FailureKind.network => l10n.dashboardErrorNetwork,
        FailureKind.offline => l10n.dashboardErrorOffline,
        FailureKind.unknown => l10n.dashboardErrorUnknown,
      };
      final actionLabel = switch (failureKind) {
        FailureKind.auth => l10n.dashboardErrorActionSignIn,
        FailureKind.offline => l10n.dashboardErrorActionRetryOnline,
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
      // J-03：原 first-goal empty state 已由 TodayCockpitCard 的
      // no-goal/fresh 态统一承接（主行动唯一入口），不再单独渲染。

      // N40（A-SPEC7 §4）访客唯一转化点：home 是访客落地面，也是
      // 「进行中任务之外」的安全窗口——卡内联于此，非弹窗；派生可见性
      // 四条守门（仅访客/已有价值信号/未被点掉/无进行中任务），注册用户
      // 与无信号访客渲染 SizedBox.shrink（零布局影响）。挂 dashboardSections
      // 而非 growthSections（wt287 盲区修复）：growthSections 在 hasNoGoals
      // 时整体不渲染，而「没有目标的新访客」恰是转化卡的主受众；两分支
      // 均渲染 dashboardSections，挂这里才保证主受众可见。与 OnboardingResumeCard
      // 相邻但语义互斥（本卡仅 guest，resume 卡仅非 guest），同屏至多见其一。
      // J-02（A-SPEC8B G1 软化）：注册墙改「放行 + 提醒」后的提醒入口——
      // 引导未完成的注册用户可自由体验（价值先于画像），本卡在首页承担
      // 「继续引导」职责。挂 dashboardSections 而非 growthSections：新注册
      // 用户无目标时走 hasNoGoals 分支（growthSections 整体不渲染），挂这
      // 才能覆盖注册即到首屏的主受众。可见性由卡内自守门（非 guest 且
      // completed==false），其余场景渲染 SizedBox.shrink，零布局影响。
      // J-05（「我卡住了」旗舰恢复旅程）：中断回流承接卡——用户卡住
      // （停滞 ≥48h 的未完成任务，检测口径见 stuck_recovery_provider）后
      // 回到 app 的第一屏承接：上次任务 + 一行共情 + 5 分钟最小重启动作，
      // 完成后转正反馈相。挂 dashboardSections（与上方两卡同理由：主受众
      // 场景在 hasNoGoals 分支也可见）；守门在 stuckRecoveryCardProvider
      // （未认证/无停滞/执行中任务一律 SizedBox.shrink，零布局影响）。
      // 排在转化/引导卡之前：把人拉回轨道优先于一切转化钩子。
      dashboardSections
        ..add(
          _staggeredSection(
            index: sectionIndex++,
            child: const StuckRecoveryCard(),
          ),
        )
        ..add(
          _staggeredSection(
            index: sectionIndex++,
            child: const GuestConversionCard(),
          ),
        )
        ..add(
          _staggeredSection(
            index: sectionIndex++,
            child: const OnboardingResumeCard(),
          ),
        );

      // Walk the user's slot order, render only what's visible, wrap each
      // in CollapsibleSlot so they can shrink to a 64px header without
      // losing access via the header tap / overflow menu.
      for (final slotId in slotConfig.visibleOrderedSlots) {
        // DASH-01 fix: skip commandCenter — it now renders as
        // TodayCockpitCard at the top of growthSections (the single primary
        // action card); rendering it again here would duplicate it.
        if (slotId == DashboardSlotIds.commandCenter) continue;

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
            child: SparkleRefreshIndicator(
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
                                  // J-03：无目标分支同样以 cockpit 打头
                                  // （no-goal 态 = 设定第一个目标的唯一
                                  // 主入口），原 _buildOnboardingWelcome
                                  // 三连快卡已移除，避免多 CTA 竞争。
                                  const TodayCockpitCard(),
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
                  semanticLabel: context.l10n.dashboardAccountabilityOpen,
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
                      SemanticPill(
                        label: context.l10n.accountabilityNudge,
                        tone: PillTone.brand,
                        icon: Icons.notifications_active_outlined,
                        onTap: () =>
                            context.push('/community/accountability'),
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
                height: 1.52,
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
                            SparkleButton(
                label: context.l10n.dashboardRetry,
                variant: ButtonVariant.text,
                size: ButtonSize.small,
                minWidth: 64,
                minHeight: 40,
                onPressed: onRetry,
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
                    SparkleButton(
            label: actionLabel,
            variant: ButtonVariant.text,
            size: ButtonSize.small,
            minWidth: 64,
            minHeight: 40,
            onPressed: onAction,
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
                  style: context.typo.bodySmall.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightMedium,
                    height: 1.52,
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
                  semanticLabel: context.l10n.dashboardBriefingToggle,
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
                                        label: context.l10n.dashboardEstimatedMinutes(estimatedMinutes),
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
                                style: context.typo.bodySmall
                                    .copyWith(
                                  color: DS.textSecondary,
                                  height: 1.52,
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
                                  label: context.l10n.chat,
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
              style: context.typo.labelSmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              title,
              style: context.typo.titleLarge.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            if (summary.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                summary,
                style: context.typo.bodyMedium.copyWith(
                  color: DS.textSecondary,
                  height: 1.52,
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
                    style: context.typo.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    headline,
                    style: context.typo.labelLarge.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    summary,
                    style: context.typo.bodySmall.copyWith(
                      color: DS.textSecondary,
                      height: 1.52,
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
                  style: context.typo.labelSmall.copyWith(
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
                    style: context.typo.labelSmall.copyWith(
                      color: DS.textSecondary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
                Text(
                  '${(plan.progress * 100).round()}%',
                  style: context.typo.labelLarge.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              plan.name,
              style: context.typo.labelLarge.copyWith(
                fontWeight: DS.fontWeightBold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            ClipRRect(
              borderRadius: DS.borderRadiusFull,
              // U-01 Step 3：确定性进度条迁 owner。
              child: LoadingIndicator.linear(
                size: 8,
                value: plan.progress.clamp(0, 1),
                backgroundColor: DS.surfaceOverlay,
                color: DS.brandPrimary,
                liveRegion: false,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.dashboardPhaseLabel(
                plan.phase.isEmpty
                    ? context.l10n.dashboardPhaseInProgress
                    : plan.phase,
              ),
              style: context.typo.bodySmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
            if (plan.daysToDeadline != null) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                context.l10n.dashboardDaysToDeadline(plan.daysToDeadline!),
                style: context.typo.bodySmall.copyWith(
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
                        semanticLabel: context.l10n.dashboardUpdatesToggle,
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
          style: context.typo.labelSmall.copyWith(
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
              style: context.typo.labelSmall.copyWith(
                color: DS.textSecondary,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
      );
}
