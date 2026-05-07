import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/lunar_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class DailyDetailScreen extends ConsumerWidget {
  const DailyDetailScreen({required this.date, super.key});
  final DateTime date;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final calendarNotifier = ref.watch(calendarProvider.notifier);
    final events = calendarNotifier.getEventsForDay(date);
    final streakHistory = ref.watch(streakHistoryProvider);
    final streakRecord = streakHistory.days.where((record) {
      final day = record.day;
      return day.year == date.year &&
          day.month == date.month &&
          day.day == date.day;
    }).firstOrNull;

    // Filter tasks for this date locally (mock logic as we load all tasks)
    final allTasks = ref.watch(taskListProvider).tasks;
    final dayTasks = allTasks.where((task) {
      final d = task.dueDate;
      if (d == null) return false;
      return d.year == date.year && d.month == date.month && d.day == date.day;
    }).toList();

    // Get Dashboard state for Prism/Flame (Mocking "historic" data with current data for demo)
    final dashboardState = ref.watch(dashboardProvider);
    final lunarData = LunarService().getLunarData(date);

    // Get active plans for this date
    final planListState = ref.watch(planListProvider);
    final activePlans = planListState.activePlans.where((plan) {
      // Plan is active if date falls between createdAt and targetDate
      if (plan.targetDate != null) {
        return date.isAfter(plan.createdAt.subtract(const Duration(days: 1))) &&
            date.isBefore(plan.targetDate!.add(const Duration(days: 1)));
      }
      return plan.isActive;
    }).toList();

    // Get achievements close to unlock for motivation
    final achievementState = ref.watch(achievementProvider);
    final closeToUnlock = achievementState.achievements
        .where((a) => !a.isUnlocked && a.progressPercentage >= 80)
        .take(3)
        .toList();

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: Text(DateFormat.MMMd(context.l10n.localeName).format(date)),
        centerTitle: true,
      ),
      child: ContentConstraint(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 1. Date Header & Lunar
              _buildDateHeader(context, date, lunarData),
              const SizedBox(height: DS.spacing20),

              // 2. Metrics Grid (Flame, Focus, Energy)
              _buildMetricsGrid(context, dashboardState),
              const SizedBox(height: DS.spacing20),

              if (streakRecord != null) ...[
                _buildSectionTitle(
                  context,
                  I18nService.instance.isChinese ? '打卡详情' : 'Check-in Details',
                  Icons.local_fire_department_rounded,
                ),
                const SizedBox(height: DS.spacing10),
                _buildCheckinSnapshot(context, streakRecord, dayTasks),
                const SizedBox(height: DS.spacing20),
              ],

              // 3. Active Plans Section (NEW)
              if (activePlans.isNotEmpty) ...[
                _buildSectionTitle(
                  context,
                  I18nService.instance.isChinese ? '活跃计划' : 'Active Plans',
                  Icons.flag_rounded,
                ),
                const SizedBox(height: DS.spacing10),
                ...activePlans.map((plan) => _buildActivePlanCard(context, ref, plan)),
                const SizedBox(height: DS.spacing20),
              ],

              // 4. Achievements in Progress (NEW)
              if (closeToUnlock.isNotEmpty) ...[
                _buildSectionTitle(
                  context,
                  I18nService.instance.isChinese ? '即将解锁' : 'Close to Unlock',
                  Icons.emoji_events_rounded,
                ),
                const SizedBox(height: DS.spacing10),
                _buildAchievementsInProgress(context, closeToUnlock),
                const SizedBox(height: DS.spacing20),
              ],

              // 5. Cognitive Prism Snapshot
              _buildPrismSnapshot(context, dashboardState),
              const SizedBox(height: DS.spacing20),

              // 6. Events Section
              _buildSectionTitle(
                context,
                context.l10n.dailyDetailEventsSection,
                Icons.event,
              ),
              const SizedBox(height: DS.spacing10),
              _buildEventList(context, ref, events),
              const SizedBox(height: DS.spacing20),

              // 7. Tasks Section
              _buildSectionTitle(
                context,
                context.l10n.dailyDetailTasksSection,
                Icons.check_circle_outline,
              ),
              const SizedBox(height: DS.spacing10),
              _buildTaskList(context, dayTasks),
            ],
          ),
        ),
      ),
    );
  }

  /// Build active plan card with calendar integration
  Widget _buildActivePlanCard(
    BuildContext context,
    WidgetRef ref,
    PlanModel plan,
  ) =>
      Semantics(
        button: true,
        label: I18nService.instance.isChinese
            ? '查看计划 ${plan.name}'
            : 'View plan ${plan.name}',
        child: GestureDetector(
          onTap: () => context.push('/plans/${plan.id}'),
          child: Container(
          margin: const EdgeInsets.only(bottom: DS.spacing8),
          padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              DS.surfaceSecondary,
              Color.lerp(DS.surfaceSecondary, DS.info, 0.08)!,
            ],
          ),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
              color: DS.borderSubtle,
            ),
        ),
        child: Row(
          children: [
            Container(
                padding: const EdgeInsets.all(DS.spacing8),
                decoration: BoxDecoration(
                  color: DS.info.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  plan.type == PlanType.sprint
                      ? Icons.flash_on_rounded
                      : Icons.trending_up_rounded,
                  color: DS.info,
                  size: 20,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      plan.name,
                      style: TextStyle(
                        color: DS.brandPrimaryConst,
                        fontWeight: DS.fontWeightBold,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Row(
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: plan.progress / 100,
                              backgroundColor: DS.info.withValues(alpha: 0.16),
                              valueColor: AlwaysStoppedAnimation<Color>(DS.info),
                              minHeight: 4,
                            ),
                          ),
                        ),
                        const SizedBox(width: DS.spacing8),
                        Text(
                          '${plan.progress.toInt()}%',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: DS.fontWeightSemibold,
                            color: DS.info,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: DS.textSecondary,
                size: 20,
              ),
            ],
          ),
        ),
      ),
      );

  Widget _buildCheckinSnapshot(
    BuildContext context,
    StreakDayRecord record,
    List<TaskModel> dayTasks,
  ) {
    final zh = I18nService.instance.isChinese;
    final completedCount = dayTasks.where((task) => task.status == TaskStatus.completed).length;
    final (title, description, color, icon) = switch (record.status) {
      StreakDayStatus.active => (
          zh ? '今日已形成有效打卡' : 'Valid check-in recorded today',
          zh ? '已完成 $completedCount 个任务，连击记录已计入系统。' : '$completedCount tasks completed. Streak recorded.',
          DS.semanticSuccess,
          Icons.local_fire_department_rounded,
        ),
      StreakDayStatus.frozen => (
          zh ? '今日触发了连击保护' : 'Streak protection triggered',
          zh ? '系统保留了连击，但这一天没有形成标准完成记录。' : 'Streak preserved, but no standard completion record for today.',
          DS.semanticWarning,
          Icons.ac_unit_rounded,
        ),
      StreakDayStatus.missed => (
          zh ? '今日没有形成打卡' : 'No check-in today',
          zh ? '任务与专注记录不足以计入当日连击。' : 'Not enough task or focus records for today\'s streak.',
          DS.textSecondary,
          Icons.event_busy_rounded,
        ),
    };

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontWeight: DS.fontWeightBold,
                    color: color,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  description,
                  style: TextStyle(
                    color: DS.textSecondary,
                    height: 1.4,
                  ),
                ),
                if (record.sourceEvent != null &&
                    record.sourceEvent!.trim().isNotEmpty) ...[
                  const SizedBox(height: DS.spacing6),
                  Text(
                    zh ? '来源事件：${record.sourceEvent}' : 'Source: ${record.sourceEvent}',
                    style: TextStyle(
                      color: DS.textTertiary,
                      fontSize: DS.fontSizeXs,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Build achievements in progress section
  Widget _buildAchievementsInProgress(
    BuildContext context,
    List<AchievementWithProgress> achievements,
  ) =>
      Container(
        padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            DS.surfaceSecondary,
            Color.lerp(DS.surfaceSecondary, DS.brandSecondary, 0.08)!,
          ],
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: DS.borderSubtle,
          ),
        ),
        child: Column(
          children: achievements.map((achievement) {
            final progressPercent = achievement.progressPercentage.toDouble();
            final remaining = 100 - progressPercent;

            return Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: Row(
                children: [
                  Icon(
                    _getAchievementIcon(achievement.achievement.category),
                    color: DS.brandSecondary,
                    size: 18,
                  ),
                  const SizedBox(width: DS.spacing10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          achievement.achievement.name,
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: DS.fontWeightMedium,
                            color: DS.brandPrimaryConst,
                          ),
                        ),
                        const SizedBox(height: DS.spacing4),
                        Row(
                          children: [
                            Expanded(
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(3),
                                child: LinearProgressIndicator(
                                  value: progressPercent / 100,
                                  backgroundColor: DS.brandSecondary.withValues(alpha: 0.2),
                                  valueColor: AlwaysStoppedAnimation<Color>(DS.brandSecondary),
                                  minHeight: 3,
                                ),
                              ),
                            ),
                            const SizedBox(width: DS.spacing8),
                            Text(
                              I18nService.instance.isChinese ? '还差 ${remaining.toInt()}%' : '${remaining.toInt()}% remaining',
                              style: TextStyle(
                                fontSize: 11,
                                color: DS.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      );

  IconData _getAchievementIcon(String? category) {
    switch (category?.toLowerCase()) {
      case 'learning':
        return Icons.school_rounded;
      case 'consistency':
        return Icons.calendar_today_rounded;
      case 'social':
        return Icons.people_rounded;
      case 'exploration':
        return Icons.explore_rounded;
      default:
        return Icons.emoji_events_rounded;
    }
  }

  Widget _buildDateHeader(
    BuildContext context,
    DateTime date,
    LunarData lunar,
  ) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.accent,
        child: Row(
          children: [
            Text(
              '${date.day}',
              style: TextStyle(
                fontSize: 48,
                fontWeight: DS.fontWeightBold,
                color: DS.textPrimary,
              ),
            ),
            const SizedBox(width: DS.lg),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  DateFormat('EEEE', 'zh_CN').format(date),
                  style: TextStyle(
                    fontSize: 18,
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
                Text(
                  '${lunar.lunarMonth}${lunar.lunarDay} ${lunar.term} ${lunar.festivals.join(" ")}',
                  style: TextStyle(fontSize: 14, color: DS.textSecondary),
                ),
              ],
            ),
          ],
        ),
      );

  Widget _buildMetricsGrid(BuildContext context, DashboardState state) => Row(
        children: [
          Expanded(
            child: _buildMetricCard(
              label: context.l10n.dailyDetailFlame,
              value: '${state.flame.level}',
              icon: Icons.local_fire_department,
              color: DS.warningAccent,
            ),
          ),
          const SizedBox(width: DS.md),
          Expanded(
            child: _buildMetricCard(
              label: context.l10n.dailyDetailFocusTime,
              value: '${state.flame.todayFocusMinutes}m',
              icon: Icons.timer,
              color: DS.brandPrimaryAccent,
            ),
          ),
          const SizedBox(width: DS.md),
          Expanded(
            child: _buildMetricCard(
              label: context.l10n.dailyDetailTasksDone,
              value: '${state.flame.tasksCompleted}',
              icon: Icons.task_alt,
              color: DS.successAccent,
            ),
          ),
        ],
      );

  Widget _buildMetricCard({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.symmetric(
          vertical: DS.spacing16,
          horizontal: DS.spacing12,
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: DS.sm),
            Text(
              value,
              style: TextStyle(
                fontSize: 20,
                fontWeight: DS.fontWeightBold,
                color: DS.textPrimary,
              ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              label,
              style: TextStyle(fontSize: 12, color: DS.textSecondary),
            ),
          ],
        ),
      );

  Widget _buildPrismSnapshot(BuildContext context, DashboardState state) {
    if (state.cognitive.status == 'empty') return const SizedBox();

    return Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: DS.prismPurple.withAlpha(30),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: DS.prismPurple.withAlpha(80)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.diamond_outlined, color: DS.prismPurple, size: 20),
              const SizedBox(width: DS.smConst),
              Text(
                context.l10n.dailyDetailPrismTitle,
                style: TextStyle(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.md),
          Text(
            state.cognitive.weeklyPattern ??
                context.l10n.dailyDetailPrismFallback,
            style: TextStyle(color: DS.textPrimary, fontSize: 15),
          ),
          if (state.cognitive.description != null) ...[
            const SizedBox(height: DS.sm),
            Text(
              state.cognitive.description!,
              style: TextStyle(color: DS.textSecondary, fontSize: 13),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSectionTitle(
    BuildContext context,
    String title,
    IconData icon,
  ) =>
      Row(
        children: [
          Icon(icon, size: 18, color: DS.primaryBase),
          const SizedBox(width: DS.sm),
          Text(
            title,
            style: TextStyle(
              color: DS.textPrimary,
              fontSize: 16,
              fontWeight: DS.fontWeightBold,
            ),
          ),
        ],
      );

  Widget _buildEventList(
    BuildContext context,
    WidgetRef ref,
    List<CalendarEventModel> events,
  ) {
    if (events.isEmpty) {
      return _buildEmptyState(context.l10n.calendarNoEvents);
    }
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: events.length,
      itemBuilder: (context, index) {
        final event = events[index];
        return Container(
          margin: const EdgeInsets.only(bottom: DS.spacing8),
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: BorderRadius.circular(12),
            border: Border(
              left: BorderSide(
                  color: _resolveEventColor(event.colorValue), width: 3,),
            ),
          ),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () {
              if (event.taskId != null && event.taskId!.isNotEmpty) {
                final encodedTaskId = Uri.encodeComponent(event.taskId!);
                unawaited(context.push('/tasks/new?taskId=$encodedTaskId'));
                return;
              }
              _showEditEventDialog(context, ref, event);
            },
            child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      event.title,
                      style: TextStyle(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.xs),
                    Text(
                      event.isAllDay
                          ? context.l10n.calendarAllDay
                          : '${Formatters.formatTime24(event.startTime)} - ${Formatters.formatTime24(event.endTime)}',
                      style: TextStyle(color: DS.textSecondary, fontSize: 12),
                    ),
                  ],
                ),
              ),
              if (event.location != null && event.location!.isNotEmpty)
                Icon(
                  Icons.location_on,
                  color: DS.brandPrimary38Const,
                  size: 16,
                ),
            ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildTaskList(BuildContext context, List<TaskModel> tasks) {
    if (tasks.isEmpty) {
      return _buildEmptyState(context.l10n.dailyDetailNoTasks);
    }
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: tasks.length,
      itemBuilder: (context, index) {
        final task = tasks[index];
        final isCompleted = task.status.toString().contains('completed');
        return Container(
          margin: const EdgeInsets.only(bottom: DS.spacing8),
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Row(
            children: [
              Icon(
                isCompleted ? Icons.check_circle : Icons.circle_outlined,
                color: isCompleted
                    ? DS.success
                    : DS.brandPrimary.withValues(alpha: 0.38),
                size: 20,
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: Text(
                  task.title,
                  style: TextStyle(
                    color: isCompleted
                        ? DS.textTertiary
                        : DS.textPrimary,
                    decoration: isCompleted ? TextDecoration.lineThrough : null,
                  ),
                ),
              ),
              if (task.priority > 2)
                Icon(
                  Icons.flag,
                  color: DS.error.withValues(alpha: 0.2),
                  size: 16,
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildEmptyState(String text) => Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: DS.spacing20),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: DS.borderSubtle,
          ), // Dashed border needs CustomPainter
        ),
        child: Center(
          child: Text(text, style: TextStyle(color: DS.textSecondary)),
        ),
      );

  Color _resolveEventColor(int colorValue) {
    switch (colorValue) {
      case 0xFF2196F3:
        return DS.info;
      case 0xFF4CAF50:
        return DS.success;
      case 0xFFFFC107:
        return DS.warning;
      case 0xFFE91E63:
        return DS.brandSecondary;
      case 0xFF9C27B0:
        return DS.prismPurple;
      default:
        return DS.brandPrimary;
    }
  }

  void _showEditEventDialog(
    BuildContext context,
    WidgetRef ref,
    CalendarEventModel event,
  ) {
    final titleController = TextEditingController(text: event.title);
    final descController = TextEditingController(text: event.description ?? '');
    final locationController = TextEditingController(
      text: event.location ?? '',
    );
    var startTime = event.startTime;
    var endTime = event.endTime;
    var isAllDay = event.isAllDay;
    var reminderMinutes = event.reminderMinutes.isNotEmpty
        ? event.reminderMinutes.first
        : 15;

    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfaceSecondary,
        builder: (sheetContext) => StatefulBuilder(
          builder: (sheetContext, setModalState) => Padding(
            padding: EdgeInsets.only(
              left: DS.spacing16,
              right: DS.spacing16,
              top: DS.spacing20,
              bottom: MediaQuery.of(sheetContext).viewInsets.bottom + DS.spacing16,
            ),
            child: SafeArea(
              top: false,
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      I18nService.instance.isChinese ? '编辑日程' : 'Edit Schedule',
                      style: TextStyle(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                        fontSize: 18,
                      ),
                    ),
                    const SizedBox(height: DS.spacing16),
                    TextField(
                      controller: titleController,
                      decoration: InputDecoration(
                        labelText: context.l10n.calTitle,
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(context.l10n.calAllDay),
                      value: isAllDay,
                      onChanged: (value) => setModalState(() => isAllDay = value),
                    ),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(context.l10n.calStartTime),
                      subtitle: Text(Formatters.formatDateTime(startTime)),
                    ),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(context.l10n.calEndTime),
                      subtitle: Text(Formatters.formatDateTime(endTime)),
                    ),
                    TextField(
                      controller: locationController,
                      decoration: InputDecoration(
                        labelText: context.l10n.calLocation,
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    TextField(
                      controller: descController,
                      maxLines: 3,
                      decoration: InputDecoration(
                        labelText: context.l10n.calDescription,
                        border: OutlineInputBorder(),
                      ),
                    ),
                    SizedBox(height: DS.spacing12),
                    DropdownButtonFormField<int>(
                      initialValue: reminderMinutes,
                      decoration: InputDecoration(
                        labelText: context.l10n.calReminderLabel,
                        border: OutlineInputBorder(),
                      ),
                      items: [
                        DropdownMenuItem(value: 0, child: Text(context.l10n.calAtStart)),
                        DropdownMenuItem(value: 5, child: Text(context.l10n.cal5MinBefore)),
                        DropdownMenuItem(value: 15, child: Text(context.l10n.cal15MinBefore)),
                        DropdownMenuItem(value: 30, child: Text(context.l10n.cal30MinBefore)),
                        DropdownMenuItem(value: 60, child: Text(context.l10n.cal1HourBefore)),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setModalState(() => reminderMinutes = value);
                        }
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    Row(
                      children: [
                        Expanded(
                          child: SparkleButton.ghost(
                            label: context.l10n.calCancel,
                            onPressed: () => Navigator.of(sheetContext).pop(),
                          ),
                        ),
                        const SizedBox(width: DS.spacing12),
                        Expanded(
                          child: SparkleButton(
                            label: context.l10n.calSave,
                            onPressed: () async {
                              final updated = event.copyWith(
                                title: titleController.text.trim().isEmpty
                                    ? event.title
                                    : titleController.text.trim(),
                                description: descController.text.trim().isEmpty
                                    ? null
                                    : descController.text.trim(),
                                location: locationController.text.trim().isEmpty
                                    ? null
                                    : locationController.text.trim(),
                                startTime: startTime,
                                endTime: endTime,
                                isAllDay: isAllDay,
                                reminderMinutes: [reminderMinutes],
                                updatedAt: DateTime.now(),
                              );
                              await ref.read(calendarProvider.notifier).updateEvent(updated);
                              if (sheetContext.mounted) {
                                Navigator.of(sheetContext).pop();
                              }
                            },
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
