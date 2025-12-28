import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/core/services/lunar_service.dart';
import 'package:sparkle/data/models/calendar_event_model.dart';
import 'package:sparkle/presentation/providers/calendar_provider.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';

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
      if (task.dueDate == null) return false;
      final d = task.dueDate!;
      return d.year == date.year && d.month == date.month && d.day == date.day;
    }).toList();

    // Get Dashboard state for Prism/Flame (Mocking "historic" data with current data for demo)
    final dashboardState = ref.watch(dashboardProvider);
    final lunarData = LunarService().getLunarData(date);

    return Scaffold(
      backgroundColor: const Color(0xFF121212), // Deep dark
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(DateFormat('MM月dd日').format(date)),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Date Header & Lunar
            _buildDateHeader(context, date, lunarData),
            const SizedBox(height: 20),
            
            // 2. Metrics Grid (Flame, Focus, Energy)
            _buildMetricsGrid(context, dashboardState),
            const SizedBox(height: 20),
            
            // 3. Cognitive Prism Snapshot
            _buildPrismSnapshot(context, dashboardState),
            const SizedBox(height: 20),

            // 4. Events Section
            _buildSectionTitle(context, '日程事件', Icons.event),
            const SizedBox(height: 10),
            _buildEventList(context, events),
            const SizedBox(height: 20),

            // 5. Tasks Section
            _buildSectionTitle(context, '任务清单', Icons.check_circle_outline),
            const SizedBox(height: 10),
            _buildTaskList(context, dayTasks),
          ],
        ),
      ),
    );
  }

  Widget _buildDateHeader(BuildContext context, DateTime date, LunarData lunar) => Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [AppDesignTokens.primaryBase.withAlpha(150), AppDesignTokens.primaryBase.withAlpha(50)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        children: [
          Text(
            '${date.day}',
            style: const TextStyle(fontSize: 48, fontWeight: FontWeight.bold, color: DS.brandPrimary),
          ),
          const SizedBox(width: DS.lg),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                DateFormat('EEEE', 'zh_CN').format(date),
                style: const TextStyle(fontSize: 18, color: DS.brandPrimary, fontWeight: FontWeight.w500),
              ),
              Text(
                '${lunar.lunarMonth}${lunar.lunarDay} ${lunar.term} ${lunar.festivals.join(" ")}',
                style: const TextStyle(fontSize: 14, color: DS.brandPrimary70),
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
            label: '火花强度',
            value: '${state.flame.level}',
            icon: Icons.local_fire_department,
            color: AppDesignTokens.warningAccent,
          ),
        ),
        const SizedBox(width: DS.md),
        Expanded(
          child: _buildMetricCard(
            label: '专注时长',
            value: '${state.flame.todayFocusMinutes}m',
            icon: Icons.timer,
            color: DS.brandPrimaryAccent,
          ),
        ),
        const SizedBox(width: DS.md),
        Expanded(
          child: _buildMetricCard(
            label: '完成任务',
            value: '${state.flame.tasksCompleted}',
            icon: Icons.task_alt,
            color: DS.successAccent,
          ),
        ),
      ],
    );

  Widget _buildMetricCard({required String label, required String value, required IconData icon, required Color color}) => Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withAlpha(15),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: DS.brandPrimary.withAlpha(20)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: DS.sm),
          Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: DS.brandPrimary)),
          const SizedBox(height: DS.xs),
          Text(label, style: const TextStyle(fontSize: 12, color: DS.brandPrimary54)),
        ],
      ),
    );

  Widget _buildPrismSnapshot(BuildContext context, DashboardState state) {
    if (state.cognitive.status == 'empty') return const SizedBox();

    return Container(
      padding: const EdgeInsets.all(DS.lg),
      decoration: BoxDecoration(
        color: AppDesignTokens.prismPurple.withAlpha(30),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppDesignTokens.prismPurple.withAlpha(80)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.diamond_outlined, color: AppDesignTokens.prismPurple, size: 20),
              SizedBox(width: DS.sm),
              Text('当日认知棱镜', style: TextStyle(color: DS.brandPrimary, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: DS.md),
          Text(
            state.cognitive.weeklyPattern ?? '今日思维清晰，状态良好',
            style: const TextStyle(color: DS.brandPrimary, fontSize: 15),
          ),
          if (state.cognitive.description != null) ...[
            const SizedBox(height: DS.sm),
            Text(
              state.cognitive.description!,
              style: const TextStyle(color: DS.brandPrimary70, fontSize: 13),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSectionTitle(BuildContext context, String title, IconData icon) => Row(
      children: [
        Icon(icon, size: 18, color: AppDesignTokens.primaryBase),
        const SizedBox(width: DS.sm),
        Text(title, style: const TextStyle(color: DS.brandPrimary, fontSize: 16, fontWeight: FontWeight.bold)),
      ],
    );

  Widget _buildEventList(BuildContext context, List<CalendarEventModel> events) {
    if (events.isEmpty) {
      return _buildEmptyState('暂无日程');
    }
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: events.length,
      itemBuilder: (context, index) {
        final event = events[index];
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: DS.brandPrimary10,
            borderRadius: BorderRadius.circular(12),
            border: Border(left: BorderSide(color: Color(event.colorValue), width: 3)),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(event.title, style: const TextStyle(color: DS.brandPrimary, fontWeight: FontWeight.bold)),
                    const SizedBox(height: DS.xs),
                    Text(
                      event.isAllDay ? '全天' : '${DateFormat('HH:mm').format(event.startTime)} - ${DateFormat('HH:mm').format(event.endTime)}',
                      style: const TextStyle(color: DS.brandPrimary54, fontSize: 12),
                    ),
                  ],
                ),
              ),
              if (event.location != null && event.location!.isNotEmpty)
                 const Icon(Icons.location_on, color: DS.brandPrimary38, size: 16),
            ],
          ),
        );
      },
    );
  }

  Widget _buildTaskList(BuildContext context, List tasks) {
    if (tasks.isEmpty) {
      return _buildEmptyState('暂无任务');
    }
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: tasks.length,
      itemBuilder: (context, index) {
        final task = tasks[index];
        return Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: DS.brandPrimary10,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Icon(
                task.status.toString().contains('completed') ? Icons.check_circle : Icons.circle_outlined,
                color: task.status.toString().contains('completed') ? DS.success : DS.brandPrimary38,
                size: 20,
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: Text(
                  task.title,
                  style: TextStyle(
                    color: task.status.toString().contains('completed') ? DS.brandPrimary38 : DS.brandPrimary,
                    decoration: task.status.toString().contains('completed') ? TextDecoration.lineThrough : null,
                  ),
                ),
              ),
              if (task.priority > 2)
                 const Icon(Icons.flag, color: DS.errorAccent, size: 16),
            ],
          ),
        );
      },
    );
  }

  Widget _buildEmptyState(String text) => Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 20),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withAlpha(5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: DS.brandPrimary.withAlpha(10)), // Dashed border needs CustomPainter
      ),
      child: Center(
        child: Text(text, style: const TextStyle(color: DS.brandPrimary38)),
      ),
    );
}
