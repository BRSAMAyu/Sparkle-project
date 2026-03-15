import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/lunar_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/calendar/calendar_routes.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/features/calendar/presentation/providers/calendar_provider.dart';
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

enum CalendarViewMode { month, twoWeeks, year }

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
      ref.read(taskCalendarProvider.notifier).loadTasksForMonth(_focusedDay);
    });
  }

  /// Handle dropping a task on a calendar date
  Future<void> _handleTaskDropped(TaskModel task, DateTime newDueDate) async {
    // Show confirmation dialog
    final confirmed = await showDialog<bool>(
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
      ref.read(taskCalendarProvider.notifier).loadTasksForMonth(_focusedDay);
    }
  }

  CalendarFormat get _tableCalendarFormat {
    switch (_viewMode) {
      case CalendarViewMode.twoWeeks:
        return CalendarFormat.twoWeeks;
      default:
        return CalendarFormat.month;
    }
  }

  @override
  Widget build(BuildContext context) {
    final notifier = ref.read(calendarProvider.notifier);
    // For list below calendar (only shown in non-year mode)
    final selectedEvents =
        notifier.getEventsForDay(_selectedDay ?? _focusedDay);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      safeArea: false,
      floatingActionButton: SparkleIconButton(
        icon: const Icon(Icons.add),
        onPressed: () => _showAddEventDialog(context),
        size: 56,
      ),
      child: Stack(
        children: [
          const Positioned.fill(child: WeatherHeader()),
          SafeArea(
            child: ContentConstraint(
              child: Column(
                children: [
                  _buildHeader(context),
                  _buildViewSwitcher(),
                  const SizedBox(height: 10),
                  Expanded(
                    child: _viewMode == CalendarViewMode.year
                        ? _buildYearView()
                        : Column(
                            children: [
                              _buildTableCalendar(notifier),
                              Divider(color: DS.brandPrimary10),
                              Expanded(
                                child:
                                    _buildEventList(selectedEvents, notifier),
                              ),
                            ],
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
                color: DS.brandPrimaryConst,
              ),
            ),
            const Spacer(),
            // Year display
            Text(
              DateFormat.y(context.l10n.localeName).format(_focusedDay),
              style: TextStyle(color: DS.brandPrimary54, fontSize: 16),
            ),
          ],
        ),
      );

  Widget _buildViewSwitcher() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
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
            value: CalendarViewMode.twoWeeks,
            label: Text(context.l10n.calendarTwoWeekView),
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
    // Actually DateTime.weekday: Mon=1, Sun=7.
    // Let's assume Mon start for consistency with TableCalendar default.
    // If Mon start, offset for Mon(1) is 0. offset for Sun(7) is 6.
    final startOffset = firstWeekday - 1;

    return LayoutBuilder(
      builder: (context, constraints) {
        // Calculate simple grid
        return GridView.count(
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
        );
      },
    );
  }

  Widget _buildTableCalendar(CalendarNotifier notifier) =>
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
            context.push(
              '${CalendarRoutes.dailyDetail}?date=${selectedDay.toIso8601String()}',
            );
          }
        },
        onFormatChanged: (format) {
          // managed by view switcher
        },
        onPageChanged: (focusedDay) {
          _focusedDay = focusedDay;
          // Load task summaries for the new month
          ref.read(taskCalendarProvider.notifier).loadTasksForMonth(focusedDay);
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
            final taskSummaries = ref.watch(taskCalendarProvider).taskSummaries;
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
                  Positioned(
                    bottom: 1,
                    right: 1,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 4, vertical: 1,),
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
                    : DS.warningAccent, // Orange for festivals
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

  Widget _buildEventList(
    List<CalendarEventModel> events,
    CalendarNotifier notifier,
  ) {
    // Header for the list
    return Column(
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
                  context.push(
                    '${CalendarRoutes.dailyDetail}?date=${(_selectedDay ?? _focusedDay).toIso8601String()}',
                  );
                },
                icon: const Icon(Icons.info_outline, size: 16),
              ),
            ],
          ),
        ),
        Expanded(
          child: events.isEmpty
              ? Center(
                  child: Text(
                    context.l10n.calendarNoEvents,
                    style: TextStyle(color: DS.brandPrimary.withAlpha(100)),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                  itemCount: events.length,
                  itemBuilder: (context, index) {
                    final event = events[index];
                    return Dismissible(
                      key: Key(event.id),
                      direction: DismissDirection.endToStart,
                      onDismissed: (direction) {
                        notifier.deleteEvent(event.id);
                      },
                      background: Container(
                        color: DS.error,
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: DS.spacing20),
                        child: Icon(Icons.delete, color: DS.textOnPrimary),
                      ),
                      child: Container(
                        margin: const EdgeInsets.only(bottom: DS.spacing8),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: DS.spacing16,
                            vertical: DS.spacing4,
                          ),
                          tileColor: DS.brandPrimary10,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
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
                            style: TextStyle(color: DS.brandPrimary),
                          ),
                          subtitle: Text(
                            event.isAllDay
                                ? context.l10n.calendarAllDay
                                : Formatters.formatTime24(event.startTime),
                            style: TextStyle(color: DS.brandPrimary54),
                          ),
                          trailing: event.recurrenceRule != null
                              ? Icon(
                                  Icons.repeat,
                                  color: DS.brandPrimary30,
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
  }

  void _showAddEventDialog(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfaceSecondary,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => _EventEditDialog(
        selectedDate: _selectedDay ?? DateTime.now(),
      ),
    );
  }
}

class _EventEditDialog extends ConsumerStatefulWidget {
  const _EventEditDialog({required this.selectedDate});
  final DateTime selectedDate;

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

  final List<int> _colorOptions = [
    0xFF2196F3, // Blue
    0xFF4CAF50, // Green
    0xFFFFC107, // Amber
    0xFFE91E63, // Pink
    0xFF9C27B0, // Purple
  ];

  @override
  void initState() {
    super.initState();
    _titleController = TextEditingController();
    _descController = TextEditingController();
    _locationController = TextEditingController();

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
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  context.l10n.calendarCreateEvent,
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: DS.brandPrimaryConst,
                  ),
                ),
                SparkleButton.primary(
                  label: context.l10n.calendarSave,
                  onPressed: _saveEvent,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing20),
            TextField(
              controller: _titleController,
              style: TextStyle(color: DS.brandPrimary),
              decoration: InputDecoration(
                hintText: context.l10n.calendarTitleHint,
                hintStyle: TextStyle(color: DS.brandPrimary38),
                prefixIcon: Icon(Icons.title, color: DS.brandPrimary70),
                border: InputBorder.none,
                filled: true,
                fillColor: DS.brandPrimary10,
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
              style: TextStyle(color: DS.brandPrimary),
              decoration: InputDecoration(
                hintText: context.l10n.calendarLocationHint,
                hintStyle: TextStyle(color: DS.brandPrimary38),
                prefixIcon:
                    Icon(Icons.location_on_outlined, color: DS.brandPrimary70),
                border: InputBorder.none,
                filled: true,
                fillColor: DS.brandPrimary10,
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _descController,
              style: TextStyle(color: DS.brandPrimary),
              decoration: InputDecoration(
                hintText: context.l10n.calendarDescriptionHint,
                hintStyle: TextStyle(color: DS.brandPrimary38),
                prefixIcon:
                    Icon(Icons.description_outlined, color: DS.brandPrimary70),
                border: InputBorder.none,
                filled: true,
                fillColor: DS.brandPrimary10,
              ),
              maxLines: 3,
            ),
            const SizedBox(height: DS.spacing20),
          ],
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
                  color: DS.brandPrimary10Const,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.calendarStartTime,
                      style: TextStyle(color: DS.brandPrimary54, fontSize: 12),
                    ),
                    Text(
                      Formatters.formatDateTime(_startTime),
                      style: TextStyle(
                        color: DS.brandPrimaryConst,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: DS.spacing10),
          Icon(Icons.arrow_forward, color: DS.brandPrimary38Const, size: 16),
          const SizedBox(width: DS.spacing10),
          Expanded(
            child: GestureDetector(
              onTap: () => _pickDateTime(false),
              child: Container(
                padding: const EdgeInsets.all(DS.md),
                decoration: BoxDecoration(
                  color: DS.brandPrimary10Const,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.calendarEndTime,
                      style: TextStyle(color: DS.brandPrimary54, fontSize: 12),
                    ),
                    Text(
                      Formatters.formatDateTime(_endTime),
                      style: TextStyle(
                        color: DS.brandPrimaryConst,
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
              style: TextStyle(color: DS.brandPrimary),
            ),
            value: _isAllDay,
            onChanged: (val) => setState(() => _isAllDay = val),
            activeThumbColor: DS.primaryBase,
            contentPadding: EdgeInsets.zero,
          ),
          ListTile(
            title: Text(
              context.l10n.calendarReminder,
              style: TextStyle(color: DS.brandPrimary),
            ),
            trailing: DropdownButton<int>(
              value: _reminderMinutes,
              dropdownColor: DS.surfaceTertiary,
              style: TextStyle(color: DS.brandPrimary),
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
              style: TextStyle(color: DS.brandPrimary),
            ),
            trailing: DropdownButton<String?>(
              value: _recurrenceRule,
              dropdownColor: DS.surfaceTertiary,
              style: TextStyle(color: DS.brandPrimary),
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
                    ? Border.all(color: DS.brandPrimaryConst, width: 2)
                    : null,
              ),
              child: isSelected
                  ? Icon(Icons.check, size: 16, color: DS.brandPrimary)
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

  void _saveEvent() {
    if (_titleController.text.isEmpty) {
      AppFeedback.info(context, context.l10n.calendarTitleRequired);
      return;
    }

    final event = CalendarEventModel(
      id: const Uuid().v4(),
      title: _titleController.text,
      description: _descController.text,
      location: _locationController.text,
      startTime: _startTime,
      endTime: _endTime,
      isAllDay: _isAllDay,
      colorValue: _colorValue,
      reminderMinutes: [_reminderMinutes],
      recurrenceRule: _recurrenceRule,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

    ref.read(calendarProvider.notifier).addEvent(event);
    context.pop();
  }
}
