import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/lunar_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class DailyDetailScreen extends ConsumerWidget {
  const DailyDetailScreen({required this.date, super.key});
  final DateTime date;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final calendarNotifier = ref.watch(calendarProvider.notifier);
    final events = calendarNotifier.getEventsForDay(date);

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

              // 3. Cognitive Prism Snapshot
              _buildPrismSnapshot(context, dashboardState),
              const SizedBox(height: DS.spacing20),

              // 4. Events Section
              _buildSectionTitle(
                context,
                context.l10n.dailyDetailEventsSection,
                Icons.event,
              ),
              const SizedBox(height: DS.spacing10),
              _buildEventList(context, events),
              const SizedBox(height: DS.spacing20),

              // 5. Tasks Section
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
                fontWeight: FontWeight.bold,
                color: DS.brandPrimaryConst,
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
                    color: DS.brandPrimaryConst,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  '${lunar.lunarMonth}${lunar.lunarDay} ${lunar.term} ${lunar.festivals.join(" ")}',
                  style: TextStyle(fontSize: 14, color: DS.brandPrimary70),
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
                fontWeight: FontWeight.bold,
                color: DS.brandPrimaryConst,
              ),
            ),
            const SizedBox(height: DS.xs),
            Text(
              label,
              style: TextStyle(fontSize: 12, color: DS.brandPrimary54),
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
                  color: DS.brandPrimaryConst,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.md),
          Text(
            state.cognitive.weeklyPattern ??
                context.l10n.dailyDetailPrismFallback,
            style: TextStyle(color: DS.brandPrimaryConst, fontSize: 15),
          ),
          if (state.cognitive.description != null) ...[
            const SizedBox(height: DS.sm),
            Text(
              state.cognitive.description!,
              style: TextStyle(color: DS.brandPrimary70Const, fontSize: 13),
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
              color: DS.brandPrimaryConst,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      );

  Widget _buildEventList(
    BuildContext context,
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
            color: DS.brandPrimary10Const,
            borderRadius: BorderRadius.circular(12),
            border: Border(
              left: BorderSide(
                  color: _resolveEventColor(event.colorValue), width: 3,),
            ),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      event.title,
                      style: TextStyle(
                        color: DS.brandPrimaryConst,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: DS.xs),
                    Text(
                      event.isAllDay
                          ? context.l10n.calendarAllDay
                          : '${Formatters.formatTime24(event.startTime)} - ${Formatters.formatTime24(event.endTime)}',
                      style: TextStyle(color: DS.brandPrimary54, fontSize: 12),
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
            color: DS.brandPrimary.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
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
                        ? DS.brandPrimary.withValues(alpha: 0.38)
                        : DS.brandPrimary,
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
          color: DS.brandPrimary.withAlpha(5),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: DS.brandPrimary.withAlpha(10),
          ), // Dashed border needs CustomPainter
        ),
        child: Center(
          child: Text(text, style: TextStyle(color: DS.brandPrimary38)),
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
}
