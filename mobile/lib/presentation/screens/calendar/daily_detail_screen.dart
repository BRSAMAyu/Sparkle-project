import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/calendar_event_model.dart';
import 'package:sparkle/presentation/providers/calendar_provider.dart';
import 'package:sparkle/presentation/providers/task_provider.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/core/services/lunar_service.dart';

class DailyDetailScreen extends ConsumerWidget {
  final DateTime date;

  const DailyDetailScreen({super.key, required this.date});

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
        padding: const EdgeInsets.all(16),
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

  Widget _buildDateHeader(BuildContext context, DateTime date, LunarData lunar) {
    return Container(
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
            style: const TextStyle(fontSize: 48, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(width: 16),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                DateFormat('EEEE', 'zh_CN').format(date),
                style: const TextStyle(fontSize: 18, color: Colors.white, fontWeight: FontWeight.w500),
              ),
              Text(
                '${lunar.lunarMonth}${lunar.lunarDay} ${lunar.term} ${lunar.festivals.join(" ")}',
                style: const TextStyle(fontSize: 14, color: Colors.white70),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMetricsGrid(BuildContext context, DashboardState state) {
    return Row(
      children: [
        Expanded(
          child: _buildMetricCard(
            label: '火花强度',
            value: '${state.flame.level}',
            icon: Icons.local_fire_department,
            color: Colors.orangeAccent,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildMetricCard(
            label: '专注时长',
            value: '${state.flame.todayFocusMinutes}m',
            icon: Icons.timer,
            color: Colors.blueAccent,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildMetricCard(
            label: '完成任务',
            value: '${state.flame.tasksCompleted}',
            icon: Icons.task_alt,
            color: Colors.greenAccent,
          ),
        ),
      ],
    );
  }

  Widget _buildMetricCard({required String label, required String value, required IconData icon, required Color color}) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(15),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withAlpha(20)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(value, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 12, color: Colors.white54)),
        ],
      ),
    );
  }

  Widget _buildPrismSnapshot(BuildContext context, DashboardState state) {
    if (state.cognitive.status == 'empty') return const SizedBox();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppDesignTokens.prismPurple.withAlpha(30),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppDesignTokens.prismPurple.withAlpha(80)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.diamond_outlined, color: AppDesignTokens.prismPurple, size: 20),
              const SizedBox(width: 8),
              const Text('当日认知棱镜', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            state.cognitive.weeklyPattern ?? '今日思维清晰，状态良好',
            style: const TextStyle(color: Colors.white, fontSize: 15),
          ),
          if (state.cognitive.description != null) ...[
            const SizedBox(height: 8),
            Text(
              state.cognitive.description!,
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSectionTitle(BuildContext context, String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 18, color: AppDesignTokens.primaryBase),
        const SizedBox(width: 8),
        Text(title, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
      ],
    );
  }

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
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white10,
            borderRadius: BorderRadius.circular(12),
            border: Border(left: BorderSide(color: Color(event.colorValue), width: 3)),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(event.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text(
                      event.isAllDay ? '全天' : '${DateFormat('HH:mm').format(event.startTime)} - ${DateFormat('HH:mm').format(event.endTime)}',
                      style: const TextStyle(color: Colors.white54, fontSize: 12),
                    ),
                  ],
                ),
              ),
              if (event.location != null && event.location!.isNotEmpty)
                 Icon(Icons.location_on, color: Colors.white38, size: 16),
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
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white10,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Icon(
                task.status.toString().contains('completed') ? Icons.check_circle : Icons.circle_outlined,
                color: task.status.toString().contains('completed') ? Colors.green : Colors.white38,
                size: 20,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  task.title,
                  style: TextStyle(
                    color: task.status.toString().contains('completed') ? Colors.white38 : Colors.white,
                    decoration: task.status.toString().contains('completed') ? TextDecoration.lineThrough : null,
                  ),
                ),
              ),
              if (task.priority > 2)
                 const Icon(Icons.flag, color: Colors.redAccent, size: 16),
            ],
          ),
        );
      },
    );
  }

  Widget _buildEmptyState(String text) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 20),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withAlpha(10), style: BorderStyle.solid), // Dashed border needs CustomPainter
      ),
      child: Center(
        child: Text(text, style: const TextStyle(color: Colors.white38)),
      ),
    );
  }
}
