import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/scroll_edge_haptics.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/errors/failures.dart';
import 'package:sparkle/core/models/aurora_correction_payload.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_progress_card.dart';
import 'package:sparkle/features/aurora/data/services/aurora_telemetry_service.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_calibration_strip.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/data/services/message_notification_service.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/exam_sprint_dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/home/presentation/providers/notification_provider.dart';
import 'package:sparkle/features/chat/chat_routes.dart';
import 'package:sparkle/features/home/presentation/providers/spine_status_band_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/aurora_status_band.dart';
import 'package:sparkle/features/home/presentation/widgets/compact_status_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/daily_context_line.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_card_section.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_section.dart';
import 'package:sparkle/features/home/presentation/widgets/exam_sprint_dashboard_card.dart';
import 'package:sparkle/features/home/presentation/widgets/home_notification_card.dart';
import 'package:sparkle/features/home/presentation/widgets/learning_heatmap_widget.dart';
import 'package:sparkle/features/home/presentation/widgets/metrics_row.dart';
import 'package:sparkle/features/home/presentation/widgets/predicted_intent_card.dart';
import 'package:sparkle/features/home/presentation/widgets/recent_insights_card.dart';
import 'package:sparkle/features/home/presentation/widgets/task_board/task_board_card.dart';
import 'package:sparkle/features/home/presentation/widgets/unified_omni_bar.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_header.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/reviews/presentation/providers/nightly_review_provider.dart';
import 'package:sparkle/features/reviews/presentation/widgets/nightly_review_panel.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
            onPressed: () => Navigator.of(ctx).pop(null),
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
    unawaited(telemetry.recordStatusBandCorrection(
      label: text,
      semanticValue: semanticValue,
      isDisconfirming: isDisconfirming,
      bandStatus: bandStatus,
      isFreeform: true,
      freeformText: text,
    ));
  }
  unawaited(
    context.push(ChatRoutes.chat, extra: {
      'initial_user_message': text,
      'aurora_correction': AuroraCorrectionPayload.freeform(
        surface: AuroraCorrectionSurface.dashboard,
        semanticValue: semanticValue,
        label: text,
        freeformText: text,
        isDisconfirming: isDisconfirming,
        bandStatus: bandStatus,
      ).toJson(),
    }),
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
      dashboardSections.add(
        _staggeredSection(
          index: sectionIndex++,
          child: CompactStatusBar(
            user: user,
            dashboardState: dashboardState,
          ),
        ),
      );
      dashboardSections.add(
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
      dashboardSections.addAll([
        _staggeredSection(
          index: sectionIndex++,
          child: Builder(builder: (context) {
            final bandAsync = ref.watch(spineStatusBandProvider);
            return bandAsync.when(
              data: (band) => AuroraStatusBand(
                state: band != null
                    ? AuroraStatusBand.mapBandStatus(band.bandStatus)
                    : _resolveAuroraState(dashboardState),
                label: band?.bandSummary.isNotEmpty == true
                    ? band!.bandSummary
                    : _auroraBandLabel(dashboardState),
                correctionOptions: band?.correctionOptions ?? [],
                cooldownRemainingSeconds: band?.cooldownRemainingSeconds,
                cooldownCanOverride: band?.cooldownCanOverride ?? false,
                onTap: () => context.push(ChatRoutes.chat),
                onCorrectionTap: (opt) {
                  if (opt.isFreeform) {
                    _showFreeformCorrectionDialog(
                      context,
                      bandStatus: band?.bandStatus.protocolValue ?? '',
                      semanticValue: opt.semanticValue,
                      isDisconfirming: opt.isDisconfirming,
                      telemetry:
                          AuroraTelemetryService(ref.read(apiClientProvider)),
                    );
                  } else {
                    final telemetry =
                        AuroraTelemetryService(ref.read(apiClientProvider));
                    unawaited(telemetry.recordStatusBandCorrection(
                      label: opt.label,
                      semanticValue: opt.semanticValue,
                      isDisconfirming: opt.isDisconfirming,
                      bandStatus: band?.bandStatus.protocolValue ?? '',
                    ));
                    final payload = AuroraCorrectionPayload.chip(
                      surface: AuroraCorrectionSurface.dashboard,
                      semanticValue: opt.semanticValue,
                      label: opt.label,
                      isDisconfirming: opt.isDisconfirming,
                      bandStatus: band?.bandStatus.protocolValue ?? '',
                    );
                    context.push(ChatRoutes.chat, extra: {
                      'initial_user_message': opt.label,
                      'aurora_correction': payload.toJson(),
                    });
                  }
                },
                onCooldownOverride: () {
                  final telemetry =
                      AuroraTelemetryService(ref.read(apiClientProvider));
                  unawaited(telemetry.recordStatusBandCorrection(
                    label: context.l10n.dashboardQuickCalibration,
                    semanticValue: 'quick_calibration',
                    isDisconfirming: false,
                    bandStatus: band?.bandStatus.protocolValue ?? '',
                  ));
                  final payload = AuroraCorrectionPayload.calibrationOverride(
                    surface: AuroraCorrectionSurface.dashboard,
                    semanticValue: 'quick_calibration',
                    label: context.l10n.dashboardQuickCalibration,
                    bandStatus: band?.bandStatus.protocolValue ?? '',
                  );
                  context.push(ChatRoutes.chat, extra: {
                    'initial_user_message':
                        context.l10n.dashboardQuickCalibration,
                    'aurora_correction': payload.toJson(),
                  });
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
          }),
        ),
        _staggeredSection(
          index: sectionIndex++,
          child: _DailyBriefingCard(
            dashboardState: dashboardState,
            isExpanded: _isBriefingExpanded,
            onToggleExpanded: () {
              setState(() {
                _isBriefingExpanded = !_isBriefingExpanded;
              });
            },
          ),
        ),
        _staggeredSection(
          index: sectionIndex++,
          child: MetricsRow(dashboardState: dashboardState),
        ),
      ]);

      // Always show the full rich dashboard sections — workspace modules,
      // achievement progress, heatmap, and task board handle their own
      // empty/loading states internally.  Only prepend the "set first goal"
      // prompt when the legacy dashboard provider confirms there are no
      // actions, sprints or growth plans yet.
      if (showFirstGoalEmptyState) {
        dashboardSections.add(
          _staggeredSection(
            index: sectionIndex++,
            child: _buildFirstGoalEmptyState(),
          ),
        );
      }
      dashboardSections.addAll([
        _staggeredSection(
          index: sectionIndex++,
          child: const _DashboardUpdatesSection(),
        ),
        _staggeredSection(
          index: sectionIndex++,
          child: const DashboardCardSection(),
        ),
        _staggeredSection(
          index: sectionIndex++,
          child: const AchievementProgressCard(),
        ),
        _staggeredSection(
          index: sectionIndex++,
          child: const Padding(
            padding: EdgeInsets.symmetric(horizontal: DS.spacing16),
            child: LearningHeatmapWidget(),
          ),
        ),
        _staggeredSection(
          index: sectionIndex++,
          child: const TaskBoardCard(),
        ),
      ]);
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
                          [
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
          padding: const EdgeInsets.all(DS.spacing16),
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
        if (nextTask.isHighPriority) zh ? '高优先级' : 'High priority',
        zh ? '完成后会更新计划进度' : 'Completing it updates your plan progress',
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
                  size: 34,
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
              if (hasObservation) ...[
                const SizedBox(height: DS.spacing12),
                _BriefingBlock(
                  eyebrow: context.l10n.dashboardSparkleObservation,
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
                      if (estimatedMinutes != null && estimatedMinutes > 0)
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
                hasTaskAction: taskId != null && taskId.isNotEmpty,
                taskId: taskId,
              ),
              ClipRect(
                child: AnimatedSize(
                  duration: DS.quick,
                  curve: DS.motionCurve(SparkleMotionToken.standard),
                  alignment: Alignment.topCenter,
                  child: !isExpanded
                      ? const SizedBox.shrink()
                      : Padding(
                          padding: const EdgeInsets.only(top: DS.spacing12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (growthSignal != null)
                                _BriefingDetailTile(
                                  icon: Icons.trending_up_rounded,
                                  iconColor: DS.success,
                                  title: context.l10n.dashboardGrowthSignal,
                                  headline: growthSignal.headline,
                                  summary: growthSignal.summary,
                                  trailing: growthSignal.source,
                                ),
                              if (growthSignal != null && activePlan != null)
                                const SizedBox(height: DS.spacing10),
                              if (activePlan != null)
                                _PlanProgressTile(
                                  plan: activePlan,
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
                        size: 34,
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
