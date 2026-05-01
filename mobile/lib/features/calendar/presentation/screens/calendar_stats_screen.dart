import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/lunar_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/calendar/calendar_routes.dart';
import 'package:sparkle/features/calendar/data/models/calendar_day_aggregate.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
import 'package:sparkle/features/calendar/presentation/providers/unified_calendar_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/weather_header.dart';
// Import task provider for updating tasks
import 'package:sparkle/features/task/presentation/providers/task_provider.dart'
    show taskListProvider;
import 'package:sparkle/shared/entities/task_model.dart';
// Import drag and drop components
import 'package:sparkle/shared/widgets/draggable_task_card.dart'
    show CalendarDayDragTarget;
import 'package:table_calendar/table_calendar.dart';
import 'package:uuid/uuid.dart';

enum CalendarViewMode { month, insights, year }

Color _resolveCalendarColor(int colorValue) {
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

class CalendarStatsScreen extends ConsumerStatefulWidget {
  const CalendarStatsScreen({super.key, this.initialDate});

  final DateTime? initialDate;

  @override
  ConsumerState<CalendarStatsScreen> createState() =>
      _CalendarStatsScreenState();
}

class _CalendarStatsScreenState extends ConsumerState<CalendarStatsScreen> {
  CalendarViewMode _viewMode = CalendarViewMode.month;
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  final LunarService _lunarService = LunarService();
  // Cached per-build: avoids redundant Theme.of(context) calls in helper methods
  bool _isDark = false;

  String _formatMonthLabel(int month) => DateFormat.MMM(context.l10n.localeName)
      .format(DateTime(_focusedDay.year, month));

  String _formatMonthDay(DateTime date) =>
      DateFormat.MMMd(context.l10n.localeName).format(date);

  @override
  void initState() {
    super.initState();
    if (widget.initialDate != null) {
      _focusedDay = widget.initialDate!;
    }
    _selectedDay = _focusedDay;
    // Load task summaries for the initial month
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(
        ref.read(taskCalendarProvider.notifier).loadTasksForMonth(_focusedDay),
      );
      unawaited(
        ref.read(unifiedCalendarProvider.notifier).loadMonth(_focusedDay),
      );
    });
  }

  /// Handle dropping a task on a calendar date
  Future<void> _handleTaskDropped(TaskModel task, DateTime newDueDate) async {
    // Show confirmation dialog
    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: DS.surfaceBase,
        title: Text(
          context.l10n.calendarSetDueDateTitle,
          style: TextStyle(color: DS.brandPrimary),
        ),
        content: Text(
          context.l10n.calendarSetDueDateMessage(
            task.title,
            _formatMonthDay(newDueDate),
          ),
          style: TextStyle(color: DS.brandPrimary70),
        ),
        actions: [
          SparkleButton.ghost(
            label: context.l10n.cancel,
            onPressed: () => Navigator.pop(context, false),
          ),
          SparkleButton.primary(
            label: context.l10n.contentReviewConfirm,
            onPressed: () => Navigator.pop(context, true),
          ),
        ],
      ),
    );

    if ((confirmed ?? false) && mounted) {
      // Update the task with new due date
      final taskUpdate = TaskUpdate(dueDate: newDueDate);
      await ref.read(taskListProvider.notifier).updateTask(task.id, taskUpdate);

      // Refresh task summaries for the current month
      await ref.read(taskCalendarProvider.notifier).loadTasksForMonth(
            _focusedDay,
            force: true,
          );
      await ref
          .read(unifiedCalendarProvider.notifier)
          .refreshMonth(_focusedDay);
      if (mounted) {
        AppFeedback.success(
          context,
          context.l10n
              .calTaskRescheduled(task.title, _formatMonthDay(newDueDate)),
        );
      }
    }
  }

  CalendarFormat get _tableCalendarFormat {
    switch (_viewMode) {
      default:
        return CalendarFormat.month;
    }
  }

  @override
  Widget build(BuildContext context) {
    final notifier = ref.read(calendarProvider.notifier);
    final calendarState = ref.watch(calendarProvider);
    final taskCalendarState = ref.watch(taskCalendarProvider);
    // Cache isDark once per build so helper methods don't each call Theme.of(context),
    // which would register multiple InheritedWidget listeners and cause redundant rebuilds.
    _isDark = Theme.of(context).brightness == Brightness.dark;
    // For list below calendar (only shown in non-year mode)
    final selectedEvents = calendarState.events
        .where((event) =>
            notifier.isSameDay(event.startTime, _selectedDay ?? _focusedDay))
        .toList();
    final taskState = ref.watch(taskListProvider);
    final selectedTasks = taskState.tasks.where((task) {
      final dueDate = task.dueDate;
      if (dueDate == null) return false;
      final target = _selectedDay ?? _focusedDay;
      return dueDate.year == target.year &&
          dueDate.month == target.month &&
          dueDate.day == target.day;
    }).toList();

    return SparklePageScaffold(
      role: SparklePageRole.content,
      safeArea: false,
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddEventDialog(context),
        child: const Icon(Icons.add),
      ),
      child: Stack(
        children: [
          const Positioned.fill(child: WeatherHeader()),
          SafeArea(
            child: ContentConstraint(
              child: Column(
                children: [
                  SparkleStaggerItem(
                    index: 0,
                    child: _buildHeader(context),
                  ),
                  SparkleStaggerItem(
                    index: 1,
                    child: _buildViewSwitcher(),
                  ),
                  const SizedBox(height: 10),
                  Expanded(
                    child: SparkleStaggerItem(
                      index: 2,
                      child: _viewMode == CalendarViewMode.year
                          ? _buildYearView()
                          : _viewMode == CalendarViewMode.insights
                              ? _buildInsightsView()
                              : Column(
                                  children: [
                                    _buildTableCalendar(
                                      notifier,
                                      taskCalendarState.taskSummaries,
                                    ),
                                    Divider(color: DS.brandPrimary10),
                                    Expanded(
                                      child: _buildAgendaList(
                                        selectedEvents,
                                        selectedTasks,
                                        notifier,
                                      ),
                                    ),
                                  ],
                                ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
        child: Row(
          children: [
            SparkleIconButton(
              icon: const Icon(Icons.arrow_back_ios_new),
              onPressed: () => context.pop(),
              variant: ButtonVariant.ghost,
            ),
            Text(
              context.l10n.calendarTitle,
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: DS.textPrimary,
              ),
            ),
            const Spacer(),
            // Year display
            Text(
              DateFormat.y(context.l10n.localeName).format(_focusedDay),
              style: TextStyle(color: DS.textSecondary, fontSize: 16),
            ),
          ],
        ),
      );

  Widget _buildViewSwitcher() {
    final isDark = _isDark;
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      width: double.infinity,
      child: SegmentedButton<CalendarViewMode>(
        segments: [
          ButtonSegment(
            value: CalendarViewMode.month,
            label: Text(context.l10n.calendarMonthView),
          ),
          ButtonSegment(
            value: CalendarViewMode.insights,
            label: Text(
              I18nService.instance.isChinese ? '热力' : 'Heat',
            ),
          ),
          ButtonSegment(
            value: CalendarViewMode.year,
            label: Text(context.l10n.calendarYearView),
          ),
        ],
        selected: {_viewMode},
        onSelectionChanged: (Set<CalendarViewMode> newSelection) {
          setState(() {
            _viewMode = newSelection.first;
          });
        },
        style: ButtonStyle(
          visualDensity: VisualDensity.compact,
          backgroundColor: WidgetStateProperty.resolveWith<Color>(
            (Set<WidgetState> states) {
              if (states.contains(WidgetState.selected)) {
                return DS.primaryBase;
              }
              return isDark ? DS.surfaceTertiary : DS.brandPrimary10;
            },
          ),
          foregroundColor: WidgetStateProperty.resolveWith<Color>(
            (Set<WidgetState> states) {
              if (states.contains(WidgetState.selected)) {
                return DS.textOnPrimary;
              }
              return isDark ? DS.textSecondary : DS.brandPrimary;
            },
          ),
        ),
      ),
    );
  }

  Widget _buildYearView() {
    final isDark = _isDark;
    return LayoutBuilder(
      builder: (context, constraints) {
        // Responsive columns: 3 on mobile, 4 on tablet/desktop
        final crossAxisCount = context.isMobile ? 3 : 4;
        final monthWidth = (constraints.maxWidth - 40) / crossAxisCount;
        final monthHeight =
            (constraints.maxHeight - 40) / ((12 / crossAxisCount).ceil());

        return GridView.builder(
          padding: const EdgeInsets.all(DS.lg),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            childAspectRatio: monthWidth / monthHeight,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
          ),
          itemCount: 12,
          itemBuilder: (context, index) {
            final monthDate = DateTime(_focusedDay.year, index + 1);
            final isCurrentMonth = monthDate.month == DateTime.now().month &&
                monthDate.year == DateTime.now().year;

            return GestureDetector(
              onTap: () {
                setState(() {
                  _focusedDay = monthDate;
                  _viewMode = CalendarViewMode.month;
                });
              },
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: isCurrentMonth
                      ? isDark
                          ? DS.surfaceTertiary
                          : DS.primaryBase.withAlpha(30)
                      : isDark
                          ? DS.surfaceSecondary
                          : DS.neutral100,
                  borderRadius: BorderRadius.circular(8),
                  border: isCurrentMonth
                      ? Border.all(
                          color: isDark ? DS.textSecondary : DS.primaryBase,
                          width: 1.5,
                        )
                      : null,
                ),
                child: Column(
                  children: [
                    // Month Name
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4.0),
                      child: Text(
                        _formatMonthLabel(index + 1),
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: isCurrentMonth
                              ? DS.textPrimary
                              : DS.textSecondary,
                        ),
                      ),
                    ),
                    // Custom Mini Grid
                    Expanded(
                      child: _buildMiniMonthGrid(monthDate),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildMiniMonthGrid(DateTime monthDate) {
    final daysInMonth = DateTime(monthDate.year, monthDate.month + 1, 0).day;
    final firstWeekday = DateTime(monthDate.year, monthDate.month).weekday;
    final isDark = _isDark;
    // Actually DateTime.weekday: Mon=1, Sun=7.
    // Let's assume Mon start for consistency with TableCalendar default.
    // If Mon start, offset for Mon(1) is 0. offset for Sun(7) is 6.
    final startOffset = firstWeekday - 1;

    return LayoutBuilder(
      builder: (context, constraints) => GridView.count(
        crossAxisCount: 7,
        padding: const EdgeInsets.all(2),
        physics: const NeverScrollableScrollPhysics(),
        children: [
          // Empty slots
          ...List.generate(startOffset, (_) => const SizedBox()),
          // Days
          ...List.generate(daysInMonth, (i) {
            final day = i + 1;
            final now = DateTime.now();
            final isToday = day == now.day &&
                monthDate.month == now.month &&
                monthDate.year == now.year;
            return Center(
              child: Text(
                '$day',
                style: TextStyle(
                  fontSize: 8,
                  color: isToday
                      ? DS.primaryBase
                      : isDark
                          ? DS.textSecondary
                          : DS.textPrimary,
                  fontWeight: isToday ? FontWeight.bold : FontWeight.normal,
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildTableCalendar(
    CalendarNotifier notifier,
    Map<DateTime, TaskDaySummary> taskSummaries,
  ) =>
      TableCalendar<CalendarEventModel>(
        firstDay: DateTime.utc(2020, 10, 16),
        lastDay: DateTime.utc(2030, 3, 14),
        focusedDay: _focusedDay,
        calendarFormat: _tableCalendarFormat,
        selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
        onDaySelected: (selectedDay, focusedDay) {
          if (!isSameDay(_selectedDay, selectedDay)) {
            setState(() {
              _selectedDay = selectedDay;
              _focusedDay = focusedDay;
            });
            // Navigate to detail screen on second tap or button click?
            // Requirement: "Clicking each specific date's detail page"
            // Let's implement single tap selects, and we add a way to open detail.
            // Or open detail immediately? Usually calendar selects first.
            // Let's assume selecting updates the list below.
            // Adding a small button or gesture to open full detail.
            // Actually, let's open it immediately on tap if already selected?
            // Or just provide a button.
            // Let's add an "Enter Detail" button in the list header or make the list tapable.
          } else {
            // If tapping already selected day, open detail
            unawaited(
              context.push(
                '${CalendarRoutes.dailyDetail}?date=${selectedDay.toIso8601String()}',
              ),
            );
          }
        },
        onFormatChanged: (format) {
          // managed by view switcher
        },
        onPageChanged: (focusedDay) {
          _focusedDay = focusedDay;
          // Load task summaries for the new month
          unawaited(
            ref
                .read(taskCalendarProvider.notifier)
                .loadTasksForMonth(focusedDay),
          );
          unawaited(
            ref.read(unifiedCalendarProvider.notifier).loadMonth(focusedDay),
          );
        },
        eventLoader: (day) => notifier.getEventsForDay(day),
        calendarStyle: CalendarStyle(
          outsideDaysVisible: false,
          defaultTextStyle: TextStyle(color: DS.brandPrimary),
          weekendTextStyle: TextStyle(color: DS.brandPrimary70),
          selectedDecoration: BoxDecoration(
            color: DS.primaryBase,
            shape: BoxShape.circle,
          ),
          todayDecoration: BoxDecoration(
            color: DS.brandPrimary24,
            shape: BoxShape.circle,
          ),
        ),
        headerStyle: HeaderStyle(
          formatButtonVisible: false,
          titleCentered: true,
          titleTextStyle: TextStyle(color: DS.brandPrimaryConst, fontSize: 16),
          leftChevronIcon: Icon(Icons.chevron_left, color: DS.brandPrimary),
          rightChevronIcon: Icon(Icons.chevron_right, color: DS.brandPrimary),
        ),
        calendarBuilders: CalendarBuilders(
          markerBuilder: (context, date, events) {
            final normalizedDate = DateTime(date.year, date.month, date.day);
            final taskSummary = taskSummaries[normalizedDate];

            // Show calendar events
            final eventMarkers = events.isEmpty
                ? <Widget>[]
                : events
                    .take(3)
                    .map(
                      (event) => Container(
                        margin: const EdgeInsets.symmetric(horizontal: 1.0),
                        width: 5.0,
                        height: 5.0,
                        decoration: BoxDecoration(
                          color: _resolveCalendarColor(event.colorValue),
                          shape: BoxShape.circle,
                        ),
                      ),
                    )
                    .toList();

            // Show task markers
            final taskMarkers = <Widget>[];
            if (taskSummary != null && taskSummary.hasTasks) {
              final today = DateTime.now();
              final isToday = date.year == today.year &&
                  date.month == today.month &&
                  date.day == today.day;

              // Determine color based on task status
              Color markerColor;
              Color textColor;
              if (taskSummary.overdue > 0) {
                markerColor = DS.error;
                textColor = DS.textOnPrimary;
              } else if (isToday) {
                markerColor = DS.info;
                textColor = DS.textOnPrimary;
              } else {
                markerColor = DS.neutral500;
                textColor = DS.textOnPrimary;
              }

              // Add dot or number badge
              if (taskSummary.total >= 4) {
                // Show number badge for 4+ tasks
                taskMarkers.add(
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 4,
                      vertical: 1,
                    ),
                    decoration: BoxDecoration(
                      color: markerColor,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 16,
                      minHeight: 12,
                    ),
                    child: Text(
                      '${taskSummary.total}',
                      style: TextStyle(
                        color: textColor,
                        fontSize: 8,
                        fontWeight: FontWeight.bold,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                );
              } else {
                // Show dots for 1-3 tasks
                for (var i = 0; i < taskSummary.total && i < 3; i++) {
                  taskMarkers.add(
                    Container(
                      margin: const EdgeInsets.symmetric(horizontal: 1.0),
                      width: 5.0,
                      height: 5.0,
                      decoration: BoxDecoration(
                        color: markerColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                  );
                }
              }
            }

            // Combine events and task markers
            final allMarkers = [...eventMarkers, ...taskMarkers];
            if (allMarkers.isEmpty) return null;

            return Positioned(
              bottom: 1,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: allMarkers,
              ),
            );
          },
          defaultBuilder: (context, day, focusedDay) => CalendarDayDragTarget(
            date: day,
            onTaskDropped: _handleTaskDropped,
            child: _buildCalendarCell(day, false),
          ),
          todayBuilder: (context, day, focusedDay) => CalendarDayDragTarget(
            date: day,
            onTaskDropped: _handleTaskDropped,
            child: _buildCalendarCell(day, true),
          ),
          selectedBuilder: (context, day, focusedDay) => CalendarDayDragTarget(
            date: day,
            onTaskDropped: _handleTaskDropped,
            child: _buildCalendarCell(day, false, isSelected: true),
          ),
        ),
      );

  Widget _buildCalendarCell(
    DateTime day,
    bool isToday, {
    bool isSelected = false,
  }) {
    final lunarData = _lunarService.getLunarData(day);

    return Container(
      margin: const EdgeInsets.all(DS.xs),
      decoration: isSelected
          ? BoxDecoration(
              color: DS.primaryBase,
              shape: BoxShape.circle,
            )
          : isToday
              ? BoxDecoration(
                  color: DS.brandPrimary24,
                  shape: BoxShape.circle,
                )
              : null,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${day.day}',
            style: TextStyle(
              color: isSelected
                  ? DS.textOnPrimary
                  : isToday
                      ? DS.primaryBase
                      : DS.textPrimary,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (lunarData.isFestival || lunarData.term.isNotEmpty)
            Text(
              lunarData.displayString,
              style: TextStyle(
                fontSize: 9,
                color: isSelected
                    ? DS.textOnPrimary.withValues(alpha: 0.7)
                    : DS.warning,
                fontWeight: FontWeight.bold,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            )
          else
            Text(
              lunarData.displayString,
              style: TextStyle(
                fontSize: 9,
                color: isSelected
                    ? DS.textOnPrimary.withValues(alpha: 0.6)
                    : DS.textSecondary,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildAgendaList(
    List<CalendarEventModel> events,
    List<TaskModel> tasks,
    CalendarNotifier notifier,
  ) =>
      Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing16,
              vertical: DS.spacing8,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  context.l10n.calendarDayScheduleTitle(
                    _formatMonthDay(_selectedDay ?? _focusedDay),
                  ),
                  style: TextStyle(
                    color: DS.brandPrimary70Const,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SparkleButton.ghost(
                  label: context.l10n.calendarViewDetails,
                  onPressed: () {
                    unawaited(
                      context.push(
                        '${CalendarRoutes.dailyDetail}?date=${(_selectedDay ?? _focusedDay).toIso8601String()}',
                      ),
                    );
                  },
                  icon: const Icon(Icons.info_outline, size: 16),
                ),
              ],
            ),
          ),
          Expanded(
            child: events.isEmpty && tasks.isEmpty
                ? Center(
                    child: Text(
                      I18nService.instance.isChinese
                          ? '这一天还没有安排任务或日程'
                          : 'No tasks or events scheduled for this day',
                      style: TextStyle(color: DS.textTertiary),
                    ),
                  )
                : ListView.builder(
                    padding:
                        const EdgeInsets.symmetric(horizontal: DS.spacing16),
                    itemCount: tasks.length + events.length,
                    itemBuilder: (context, index) {
                      if (index < tasks.length) {
                        final task = tasks[index];
                        return _buildTaskAgendaCard(task);
                      }

                      final event = events[index - tasks.length];
                      return Dismissible(
                        key: Key(event.id),
                        direction: DismissDirection.endToStart,
                        onDismissed: (direction) {
                          unawaited(notifier.deleteEvent(event.id));
                        },
                        background: Container(
                          margin: const EdgeInsets.only(bottom: DS.spacing8),
                          decoration: BoxDecoration(
                            color: DS.error.withValues(alpha: 0.9),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          alignment: Alignment.centerRight,
                          padding: const EdgeInsets.only(right: DS.spacing20),
                          child: Icon(Icons.delete, color: DS.textOnPrimary),
                        ),
                        child: Container(
                          margin: const EdgeInsets.only(bottom: DS.spacing8),
                          child: ListTile(
                            onTap: () {
                              if (event.taskId != null &&
                                  event.taskId!.isNotEmpty) {
                                unawaited(
                                  context.push(
                                      '/tasks/new?taskId=${event.taskId!}'),
                                );
                                return;
                              }
                              _showEditEventDialog(context, event);
                            },
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: DS.spacing16,
                              vertical: DS.spacing4,
                            ),
                            tileColor: DS.surfaceSecondary,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                              side: BorderSide(color: DS.borderSubtle),
                            ),
                            leading: Container(
                              width: 12,
                              height: 12,
                              decoration: BoxDecoration(
                                color: _resolveCalendarColor(event.colorValue),
                                shape: BoxShape.circle,
                              ),
                            ),
                            title: Text(
                              event.title,
                              style: TextStyle(
                                color: DS.textPrimary,
                                fontWeight: DS.fontWeightSemibold,
                              ),
                            ),
                            subtitle: Text(
                              event.isAllDay
                                  ? context.l10n.calendarAllDay
                                  : Formatters.formatTime24(event.startTime),
                              style: TextStyle(color: DS.textSecondary),
                            ),
                            trailing: event.recurrenceRule != null
                                ? Icon(
                                    Icons.repeat,
                                    color: DS.textTertiary,
                                    size: 16,
                                  )
                                : null,
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      );

  Widget _buildInsightsView() {
    final unifiedState = ref.watch(unifiedCalendarProvider);
    final streakStats = ref.watch(streakStatsProvider);
    final monthKey =
        '${_focusedDay.year}-${_focusedDay.month.toString().padLeft(2, '0')}';
    final aggregate = unifiedState.monthAggregates[monthKey];

    if (!unifiedState.isMonthLoaded(_focusedDay.year, _focusedDay.month) &&
        !unifiedState.isLoading) {
      unawaited(
        Future.microtask(
          () =>
              ref.read(unifiedCalendarProvider.notifier).loadMonth(_focusedDay),
        ),
      );
    }

    if (unifiedState.isLoading && aggregate == null) {
      return const _CalendarInsightsLoadingSkeleton();
    }

    if (aggregate == null) {
      return Center(
        child: Text(
          I18nService.instance.isChinese ? '暂无热力数据' : 'No heat data available',
          style: TextStyle(color: DS.textSecondary),
        ),
      );
    }

    final peakDay = aggregate.dayAggregates.values.fold<CalendarDayAggregate?>(
      null,
      (best, current) {
        if (best == null) return current;
        return current.intensityLevel > best.intensityLevel ? current : best;
      },
    );

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing16,
        0,
        DS.spacing16,
        DS.spacing16,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: DS.spacing10,
            runSpacing: DS.spacing10,
            children: [
              _buildInsightMetric(
                label: context.l10n.calStreakDays,
                value: '${streakStats.currentStreak}',
                detail: I18nService.instance.isChinese
                    ? '保持你的成就节奏'
                    : 'Keep your achievement rhythm',
                icon: Icons.local_fire_department_rounded,
                color: DS.warningAccent,
              ),
              _buildInsightMetric(
                label: context.l10n.calActiveDays,
                value: '${aggregate.activeDays}',
                detail: I18nService.instance.isChinese
                    ? '本月有行动的日期'
                    : 'Active days this month',
                icon: Icons.calendar_month_rounded,
                color: DS.info,
              ),
              _buildInsightMetric(
                label: context.l10n.calCompletedTasks,
                value: '${aggregate.totalCompletedTasks}',
                detail: I18nService.instance.isChinese
                    ? '本月完成的任务数'
                    : 'Tasks completed this month',
                icon: Icons.task_alt_rounded,
                color: DS.success,
              ),
              _buildInsightMetric(
                label: context.l10n.calFocusDuration,
                value:
                    '${(aggregate.totalFocusMinutes / 60).toStringAsFixed(1)}h',
                detail: I18nService.instance.isChinese
                    ? '本月累计专注'
                    : 'Total focus time this month',
                icon: Icons.bolt_rounded,
                color: DS.prismPurple,
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          MaterialStyler(
            material: AppMaterials.ceramic(context),
            borderRadius: DS.borderRadius20,
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  I18nService.instance.isChinese ? '学习热力' : 'Learning Heatmap',
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                SizedBox(height: DS.spacing6),
                Text(
                  I18nService.instance.isChinese
                      ? '用热力看连续性、完成度和学习投入，而不是重复浏览日程表。'
                      : 'View continuity, completion, and learning engagement through heatmaps, instead of repeatedly browsing the schedule.',
                  style: TextStyle(color: DS.textSecondary, fontSize: 12),
                ),
                const SizedBox(height: DS.spacing16),
                _buildActivityHeatmap(aggregate),
                const SizedBox(height: DS.spacing12),
                Row(
                  children: [
                    Text(
                      I18nService.instance.isChinese ? '低' : 'Low',
                      style: TextStyle(fontSize: 11, color: DS.textSecondary),
                    ),
                    SizedBox(width: DS.spacing6),
                    ...List.generate(
                      5,
                      (index) => Container(
                        width: 12,
                        height: 12,
                        margin: const EdgeInsets.only(right: DS.spacing4),
                        decoration: BoxDecoration(
                          color: _resolveHeatColor(index),
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                    Text(
                      I18nService.instance.isChinese ? '高' : 'High',
                      style: TextStyle(fontSize: 11, color: DS.textSecondary),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          MaterialStyler(
            material: AppMaterials.ceramic(context),
            borderRadius: DS.borderRadius20,
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  I18nService.instance.isChinese
                      ? '月度亮点'
                      : 'Monthly Highlights',
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                SizedBox(height: DS.spacing10),
                _buildInsightLine(
                  icon: Icons.trending_up_rounded,
                  title: context.l10n.calHottestDay,
                  value: peakDay == null
                      ? (I18nService.instance.isChinese ? '暂无' : 'N/A')
                      : '${peakDay.date.month}/${peakDay.date.day} · ${peakDay.summaryText}',
                ),
                _buildInsightLine(
                  icon: Icons.flag_rounded,
                  title: context.l10n.calCurrentMainGoal,
                  value: aggregate.activePlan?.name ??
                      (I18nService.instance.isChinese
                          ? '本月暂无活跃计划'
                          : 'No active plan this month'),
                ),
                _buildInsightLine(
                  icon: Icons.emoji_events_rounded,
                  title: context.l10n.calAchievementMomentum,
                  value: streakStats.currentStreak >= 7
                      ? (I18nService.instance.isChinese
                          ? '连续状态很好，适合冲刺里程碑'
                          : 'Great streak! Time to sprint for milestones')
                      : (I18nService.instance.isChinese
                          ? '先把连续性拉起来，会更容易触发成就闭环'
                          : 'Build your consistency first to trigger achievement loops'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInsightMetric({
    required String label,
    required String value,
    required String detail,
    required IconData icon,
    required Color color,
  }) =>
      SizedBox(
        width: 156,
        child: MaterialStyler(
          material: AppMaterials.ceramic(context),
          borderRadius: DS.borderRadius16,
          padding: const EdgeInsets.all(DS.spacing12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: color, size: 18),
              const SizedBox(height: DS.spacing10),
              Text(
                value,
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                label,
                style: TextStyle(
                  color: DS.textPrimary,
                  fontWeight: DS.fontWeightSemibold,
                ),
              ),
              const SizedBox(height: DS.spacing2),
              Text(
                detail,
                style: TextStyle(color: DS.textSecondary, fontSize: 12),
              ),
            ],
          ),
        ),
      );

  Widget _buildActivityHeatmap(CalendarMonthAggregate aggregate) {
    final firstDay = DateTime(aggregate.year, aggregate.month);
    final daysInMonth = DateTime(aggregate.year, aggregate.month + 1, 0).day;
    final offset = firstDay.weekday - 1;
    final cells = <Widget>[];

    for (var i = 0; i < offset; i++) {
      cells.add(const SizedBox());
    }

    for (var day = 1; day <= daysInMonth; day++) {
      final aggregateDay = aggregate.dayAggregates[day];
      final intensity = aggregateDay?.intensityLevel ?? 0;
      final date = DateTime(aggregate.year, aggregate.month, day);
      final isSelected = _selectedDay != null &&
          _selectedDay!.year == date.year &&
          _selectedDay!.month == date.month &&
          _selectedDay!.day == date.day;
      cells.add(
        GestureDetector(
          onTap: () {
            setState(() {
              _selectedDay = date;
              _focusedDay = date;
              _viewMode = CalendarViewMode.month;
            });
          },
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            decoration: BoxDecoration(
              color: _resolveHeatColor(intensity),
              borderRadius: BorderRadius.circular(6),
              border: isSelected
                  ? Border.all(color: DS.brandPrimary, width: 1.5)
                  : null,
            ),
            alignment: Alignment.center,
            child: Text(
              '$day',
              style: TextStyle(
                color: intensity >= 3 ? DS.textOnPrimary : DS.textPrimary,
                fontSize: 11,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ),
        ),
      );
    }

    return AspectRatio(
      aspectRatio: 7 / 5,
      child: GridView.count(
        crossAxisCount: 7,
        crossAxisSpacing: DS.spacing6,
        mainAxisSpacing: DS.spacing6,
        physics: const NeverScrollableScrollPhysics(),
        children: cells,
      ),
    );
  }

  Widget _buildInsightLine({
    required IconData icon,
    required String title,
    required String value,
  }) =>
      Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 16, color: DS.brandPrimary),
            const SizedBox(width: DS.spacing8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: DS.spacing2),
                  Text(
                    value,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Color _resolveHeatColor(int level) {
    final clamped = level.clamp(0, 4);
    return switch (clamped) {
      0 => DS.surfaceTertiary,
      1 => DS.brandPrimary.withValues(alpha: 0.18),
      2 => DS.brandPrimary.withValues(alpha: 0.35),
      3 => DS.brandPrimary.withValues(alpha: 0.58),
      _ => DS.brandPrimary,
    };
  }

  Widget _buildTaskAgendaCard(TaskModel task) {
    final dueLabel = task.dueDate == null
        ? (I18nService.instance.isChinese ? '未安排时间' : 'No time set')
        : Formatters.formatDateTime(task.dueDate!);
    final statusColor = switch (task.status) {
      TaskStatus.completed => DS.success,
      TaskStatus.inProgress => DS.info,
      TaskStatus.stuck => DS.warning,
      TaskStatus.pending => DS.warning,
      TaskStatus.abandoned => DS.textSecondary,
    };

    return Container(
      margin: const EdgeInsets.only(bottom: DS.spacing8),
      child: ListTile(
        onTap: () => context.push('/tasks/${task.id}'),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing6,
        ),
        tileColor: DS.surfaceSecondary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: DS.borderSubtle),
        ),
        leading: Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: statusColor,
            shape: BoxShape.circle,
          ),
        ),
        title: Text(
          task.title,
          style: TextStyle(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        subtitle: Text(
          context.l10n.calTaskWithDue(
              task.planId != null
                  ? context.l10n.calTaskTypeTask
                  : context.l10n.calTaskTypeTodo,
              dueLabel),
          style: TextStyle(color: DS.textSecondary),
        ),
        trailing: Icon(
          Icons.chevron_right_rounded,
          color: DS.textSecondary,
        ),
      ),
    );
  }

  void _showAddEventDialog(BuildContext context) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfaceSecondary,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        builder: (context) => _EventEditDialog(
          selectedDate: _selectedDay ?? DateTime.now(),
        ),
      ),
    );
  }

  void _showEditEventDialog(BuildContext context, CalendarEventModel event) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfaceSecondary,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        builder: (context) => _EventEditDialog(
          selectedDate: event.startTime,
          initialEvent: event,
        ),
      ),
    );
  }
}

class _CalendarInsightsLoadingSkeleton extends StatelessWidget {
  const _CalendarInsightsLoadingSkeleton();

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          0,
          DS.spacing16,
          DS.spacing16,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: DS.spacing10,
              runSpacing: DS.spacing10,
              children: List.generate(
                4,
                (_) => SizedBox(
                  width: 156,
                  child: MaterialStyler(
                    material: AppMaterials.ceramic(context),
                    borderRadius: DS.borderRadius16,
                    padding: const EdgeInsets.all(DS.spacing12),
                    child: const _CalendarSkeletonMetric(),
                  ),
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            MaterialStyler(
              material: AppMaterials.ceramic(context),
              borderRadius: DS.borderRadius20,
              padding: const EdgeInsets.all(DS.spacing16),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _CalendarSkeletonBar(widthFactor: 0.36),
                  SizedBox(height: DS.spacing10),
                  _CalendarSkeletonBar(widthFactor: 0.82, height: 12),
                  SizedBox(height: DS.spacing16),
                  AspectRatio(
                    aspectRatio: 7 / 5,
                    child: _CalendarSkeletonGrid(),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _CalendarSkeletonMetric extends StatelessWidget {
  const _CalendarSkeletonMetric();

  @override
  Widget build(BuildContext context) => const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _CalendarSkeletonDot(),
          SizedBox(height: DS.spacing10),
          _CalendarSkeletonBar(widthFactor: 0.44, height: 20),
          SizedBox(height: DS.spacing8),
          _CalendarSkeletonBar(widthFactor: 0.72, height: 12),
        ],
      );
}

class _CalendarSkeletonGrid extends StatelessWidget {
  const _CalendarSkeletonGrid();

  @override
  Widget build(BuildContext context) => GridView.count(
        crossAxisCount: 7,
        crossAxisSpacing: DS.spacing6,
        mainAxisSpacing: DS.spacing6,
        physics: const NeverScrollableScrollPhysics(),
        children: List.generate(
          35,
          (index) => DecoratedBox(
            decoration: BoxDecoration(
              color: index.isEven ? DS.surfaceTertiary : DS.surfaceSecondary,
              borderRadius: BorderRadius.circular(6),
            ),
          ),
        ),
      );
}

class _CalendarSkeletonDot extends StatelessWidget {
  const _CalendarSkeletonDot();

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfaceTertiary,
          borderRadius: BorderRadius.circular(999),
        ),
        child: const SizedBox(width: 18, height: 18),
      );
}

class _CalendarSkeletonBar extends StatelessWidget {
  const _CalendarSkeletonBar({
    required this.widthFactor,
    this.height = 16,
  });

  final double widthFactor;
  final double height;

  @override
  Widget build(BuildContext context) => FractionallySizedBox(
        widthFactor: widthFactor,
        alignment: Alignment.centerLeft,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: DS.surfaceTertiary,
            borderRadius: BorderRadius.circular(999),
          ),
          child: SizedBox(height: height),
        ),
      );
}

class _EventEditDialog extends ConsumerStatefulWidget {
  const _EventEditDialog({
    required this.selectedDate,
    this.initialEvent,
  });
  final DateTime selectedDate;
  final CalendarEventModel? initialEvent;

  @override
  ConsumerState<_EventEditDialog> createState() => _EventEditDialogState();
}

class _EventEditDialogState extends ConsumerState<_EventEditDialog> {
  late TextEditingController _titleController;
  late TextEditingController _descController;
  late TextEditingController _locationController;
  late DateTime _startTime;
  late DateTime _endTime;
  bool _isAllDay = false;
  int _colorValue = 0xFF2196F3;
  int _reminderMinutes = 15;
  String? _recurrenceRule;
  bool _isSaving = false;
  String? _saveError;

  final List<int> _colorOptions = [
    0xFF2196F3, // Blue
    0xFF4CAF50, // Green
    0xFFFFC107, // Amber
    0xFFE91E63, // Pink
    0xFF9C27B0, // Purple
  ];

  InputDecoration _fieldDecoration({
    required String hintText,
    required IconData icon,
  }) =>
      InputDecoration(
        hintText: hintText,
        hintStyle: TextStyle(color: DS.textTertiary),
        prefixIcon: Icon(icon, color: DS.textSecondary),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: DS.borderSubtle),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: DS.borderSubtle),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide(color: DS.primaryBase.withValues(alpha: 0.45)),
        ),
        filled: true,
        fillColor: DS.surfacePrimary,
      );

  @override
  void initState() {
    super.initState();
    final initialEvent = widget.initialEvent;
    _titleController = TextEditingController(text: initialEvent?.title ?? '');
    _descController = TextEditingController(
      text: initialEvent?.description ?? '',
    );
    _locationController = TextEditingController(
      text: initialEvent?.location ?? '',
    );

    if (initialEvent != null) {
      _startTime = initialEvent.startTime;
      _endTime = initialEvent.endTime;
      _isAllDay = initialEvent.isAllDay;
      _colorValue = initialEvent.colorValue;
      _reminderMinutes = initialEvent.reminderMinutes.isNotEmpty
          ? initialEvent.reminderMinutes.first
          : 15;
      _recurrenceRule = initialEvent.recurrenceRule;
      return;
    }

    final now = DateTime.now();
    _startTime = DateTime(
      widget.selectedDate.year,
      widget.selectedDate.month,
      widget.selectedDate.day,
      now.hour + 1,
    );
    _endTime = _startTime.add(const Duration(hours: 1));
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descController.dispose();
    _locationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
          left: DS.spacing16,
          right: DS.spacing16,
          top: DS.spacing20,
        ),
        child: SafeArea(
          top: false,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      widget.initialEvent == null
                          ? context.l10n.calendarCreateEvent
                          : (I18nService.instance.isChinese
                              ? '编辑日程'
                              : 'Edit Event'),
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: DS.textPrimary,
                      ),
                    ),
                    SparkleButton.primary(
                      label: context.l10n.calendarSave,
                      onPressed: _saveEvent,
                      loading: _isSaving,
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing20),
                if (_saveError != null) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(DS.spacing12),
                    decoration: BoxDecoration(
                      color: DS.error.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: DS.error.withValues(alpha: 0.24),
                      ),
                    ),
                    child: Text(
                      _saveError!,
                      style: TextStyle(
                        color: DS.error,
                        fontWeight: DS.fontWeightSemibold,
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                ],
                TextField(
                  controller: _titleController,
                  enabled: !_isSaving,
                  style: TextStyle(color: DS.textPrimary),
                  decoration: _fieldDecoration(
                    hintText: context.l10n.calendarTitleHint,
                    icon: Icons.title,
                  ),
                ),
                const SizedBox(height: DS.spacing10),
                _buildTimeRow(),
                const SizedBox(height: DS.spacing10),
                _buildOptionsRow(),
                const SizedBox(height: DS.spacing10),
                _buildColorPicker(),
                const SizedBox(height: DS.spacing10),
                TextField(
                  controller: _locationController,
                  enabled: !_isSaving,
                  style: TextStyle(color: DS.textPrimary),
                  decoration: _fieldDecoration(
                    hintText: context.l10n.calendarLocationHint,
                    icon: Icons.location_on_outlined,
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _descController,
                  enabled: !_isSaving,
                  style: TextStyle(color: DS.textPrimary),
                  decoration: _fieldDecoration(
                    hintText: context.l10n.calendarDescriptionHint,
                    icon: Icons.description_outlined,
                  ),
                  maxLines: 3,
                ),
                const SizedBox(height: DS.spacing20),
              ],
            ),
          ),
        ),
      );

  Widget _buildTimeRow() => Row(
        children: [
          Expanded(
            child: GestureDetector(
              onTap: () => _pickDateTime(true),
              child: Container(
                padding: const EdgeInsets.all(DS.md),
                decoration: BoxDecoration(
                  color: DS.surfacePrimary,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: DS.borderSubtle),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.calendarStartTime,
                      style: TextStyle(color: DS.textSecondary, fontSize: 12),
                    ),
                    Text(
                      Formatters.formatDateTime(_startTime),
                      style: TextStyle(
                        color: DS.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: DS.spacing10),
          Icon(Icons.arrow_forward, color: DS.textTertiary, size: 16),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: GestureDetector(
              onTap: () => _pickDateTime(false),
              child: Container(
                padding: const EdgeInsets.all(DS.md),
                decoration: BoxDecoration(
                  color: DS.surfacePrimary,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: DS.borderSubtle),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.calendarEndTime,
                      style: TextStyle(color: DS.textSecondary, fontSize: 12),
                    ),
                    Text(
                      Formatters.formatDateTime(_endTime),
                      style: TextStyle(
                        color: DS.textPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      );

  Widget _buildOptionsRow() => Column(
        children: [
          SwitchListTile(
            title: Text(
              context.l10n.calendarAllDay,
              style: TextStyle(color: DS.textPrimary),
            ),
            value: _isAllDay,
            onChanged: (val) => setState(() => _isAllDay = val),
            activeThumbColor: DS.primaryBase,
            contentPadding: EdgeInsets.zero,
          ),
          ListTile(
            title: Text(
              context.l10n.calendarReminder,
              style: TextStyle(color: DS.textPrimary),
            ),
            trailing: DropdownButton<int>(
              value: _reminderMinutes,
              dropdownColor: DS.surfaceTertiary,
              style: TextStyle(color: DS.textPrimary),
              underline: Container(),
              items: [
                DropdownMenuItem(
                  value: 0,
                  child: Text(context.l10n.calendarReminderAtStart),
                ),
                DropdownMenuItem(
                  value: 5,
                  child: Text(context.l10n.calendarReminderMinutes(5)),
                ),
                DropdownMenuItem(
                  value: 15,
                  child: Text(context.l10n.calendarReminderMinutes(15)),
                ),
                DropdownMenuItem(
                  value: 30,
                  child: Text(context.l10n.calendarReminderMinutes(30)),
                ),
                DropdownMenuItem(
                  value: 60,
                  child: Text(context.l10n.calendarReminderHours(1)),
                ),
                DropdownMenuItem(
                  value: 1440,
                  child: Text(context.l10n.calendarReminderDays(1)),
                ),
              ],
              onChanged: (val) => setState(() => _reminderMinutes = val!),
            ),
            contentPadding: EdgeInsets.zero,
          ),
          ListTile(
            title: Text(
              context.l10n.calendarRepeat,
              style: TextStyle(color: DS.textPrimary),
            ),
            trailing: DropdownButton<String?>(
              value: _recurrenceRule,
              dropdownColor: DS.surfaceTertiary,
              style: TextStyle(color: DS.textPrimary),
              underline: Container(),
              items: [
                DropdownMenuItem(
                  child: Text(context.l10n.calendarRepeatNone),
                ),
                DropdownMenuItem(
                  value: 'daily',
                  child: Text(context.l10n.calendarRepeatDaily),
                ),
                DropdownMenuItem(
                  value: 'weekly',
                  child: Text(context.l10n.calendarRepeatWeekly),
                ),
                DropdownMenuItem(
                  value: 'monthly',
                  child: Text(context.l10n.calendarRepeatMonthly),
                ),
              ],
              onChanged: (val) => setState(() => _recurrenceRule = val),
            ),
            contentPadding: EdgeInsets.zero,
          ),
        ],
      );

  Widget _buildColorPicker() => Row(
        children: _colorOptions.map((color) {
          final isSelected = _colorValue == color;
          return GestureDetector(
            onTap: () => setState(() => _colorValue = color),
            child: Container(
              margin: const EdgeInsets.only(right: DS.spacing12),
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: _resolveCalendarColor(color),
                shape: BoxShape.circle,
                border: isSelected
                    ? Border.all(color: DS.textPrimary, width: 2)
                    : null,
              ),
              child: isSelected
                  ? Icon(Icons.check, size: 16, color: DS.surfacePrimary)
                  : null,
            ),
          );
        }).toList(),
      );

  Future<void> _pickDateTime(bool isStart) async {
    final initialDate = isStart ? _startTime : _endTime;
    final date = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );

    if (date != null) {
      if (!mounted) return;
      final time = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(initialDate),
      );

      if (time != null) {
        setState(() {
          final newDateTime = DateTime(
            date.year,
            date.month,
            date.day,
            time.hour,
            time.minute,
          );
          if (isStart) {
            _startTime = newDateTime;
            if (_endTime.isBefore(_startTime)) {
              _endTime = _startTime.add(const Duration(hours: 1));
            }
          } else {
            _endTime = newDateTime;
          }
        });
      }
    }
  }

  Future<void> _saveEvent() async {
    // Dismiss keyboard and commit any pending IME composition before validation
    FocusScope.of(context).unfocus();
    if (_titleController.text.isEmpty) {
      setState(() {
        _saveError = context.l10n.calendarTitleRequired;
      });
      return;
    }

    if (!_endTime.isAfter(_startTime)) {
      setState(() {
        _saveError = context.l10n.calEndAfterStart;
      });
      return;
    }

    setState(() {
      _isSaving = true;
      _saveError = null;
    });

    final existingEvent = widget.initialEvent;
    final event = CalendarEventModel(
      id: existingEvent?.id ?? const Uuid().v4(),
      title: _titleController.text,
      description: _descController.text,
      location: _locationController.text,
      startTime: _startTime,
      endTime: _endTime,
      isAllDay: _isAllDay,
      colorValue: _colorValue,
      reminderMinutes: [_reminderMinutes],
      recurrenceRule: _recurrenceRule,
      taskId: existingEvent?.taskId,
      planId: existingEvent?.planId,
      source: existingEvent?.source ?? 'manual',
      sourceMetadata: existingEvent?.sourceMetadata,
      createdAt: existingEvent?.createdAt ?? DateTime.now(),
      updatedAt: DateTime.now(),
    );

    try {
      if (existingEvent != null) {
        await ref.read(calendarProvider.notifier).updateEvent(event);
        if (!mounted) return;
        context.pop();
        AppFeedback.success(context,
            I18nService.instance.isChinese ? '日程已更新' : 'Event updated');
        return;
      }
      final result = await ref.read(calendarProvider.notifier).addEvent(event);
      if (!mounted) return;
      context.pop();
      if (result.persistedRemotely) {
        AppFeedback.success(context,
            I18nService.instance.isChinese ? '日程已创建' : 'Event created');
      } else {
        AppFeedback.info(
          context,
          result.message ??
              (I18nService.instance.isChinese
                  ? '已保存到本地，稍后会自动同步到云端。'
                  : 'Saved locally, will sync to cloud automatically.'),
        );
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _saveError = context.l10n.calCreateEventFailed(e.toString());
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }
}
