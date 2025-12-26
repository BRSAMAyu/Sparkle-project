import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/presentation/widgets/home/weather_header.dart';
import 'package:sparkle/core/services/lunar_service.dart';
import 'package:sparkle/presentation/providers/calendar_provider.dart';
import 'package:sparkle/data/models/calendar_event_model.dart';
import 'package:uuid/uuid.dart';

class CalendarStatsScreen extends ConsumerStatefulWidget {
  const CalendarStatsScreen({super.key});

  @override
  ConsumerState<CalendarStatsScreen> createState() => _CalendarStatsScreenState();
}

class _CalendarStatsScreenState extends ConsumerState<CalendarStatsScreen> {
  CalendarFormat _calendarFormat = CalendarFormat.month;
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  final LunarService _lunarService = LunarService();

  @override
  void initState() {
    super.initState();
    _selectedDay = _focusedDay;
  }

  @override
  Widget build(BuildContext context) {
    final calendarState = ref.watch(calendarProvider);
    final notifier = ref.read(calendarProvider.notifier);
    final selectedEvents = notifier.getEventsForDay(_selectedDay ?? _focusedDay);

    return Scaffold(
      backgroundColor: AppDesignTokens.deepSpaceStart,
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddEventDialog(context),
        backgroundColor: AppDesignTokens.primaryBase,
        child: const Icon(Icons.add, color: Colors.white),
      ),
      body: Stack(
        children: [
          const Positioned.fill(child: WeatherHeader()),
          SafeArea(
            child: Column(
              children: [
                _buildHeader(context),
                Expanded(
                  child: Column(
                    children: [
                      _buildTableCalendar(notifier),
                      const Divider(color: Colors.white10),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        child: Row(
                          children: [
                            Text(
                              '${DateFormat('MM月dd日').format(_selectedDay!)} ${_getWeekDay(_selectedDay!)}',
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _lunarService.getLunarInfo(_selectedDay!)['lunarDate'],
                                style: const TextStyle(
                                  fontSize: 14,
                                  color: Colors.white60,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        child: _buildEventList(selectedEvents, notifier),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _getWeekDay(DateTime date) {
    const weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    return weekdays[date.weekday - 1];
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          IconButton(
            icon: Icon(Icons.arrow_back_ios_new, color: AppColors.textOnDark(context)),
            onPressed: () => context.pop(),
          ),
          Text(
            '专注日历',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: AppColors.textOnDark(context),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.calendar_view_week, color: Colors.white),
            onPressed: () {
              setState(() {
                _calendarFormat = _calendarFormat == CalendarFormat.month
                    ? CalendarFormat.twoWeeks
                    : CalendarFormat.month;
              });
            },
          ),
        ],
      ),
    );
  }

  Widget _buildTableCalendar(CalendarNotifier notifier) {
    return TableCalendar<CalendarEventModel>(
      firstDay: DateTime.utc(2020, 10, 16),
      lastDay: DateTime.utc(2030, 3, 14),
      focusedDay: _focusedDay,
      calendarFormat: _calendarFormat,
      selectedDayPredicate: (day) => isSameDay(_selectedDay, day),
      onDaySelected: (selectedDay, focusedDay) {
        if (!isSameDay(_selectedDay, selectedDay)) {
          setState(() {
            _selectedDay = selectedDay;
            _focusedDay = focusedDay;
          });
        }
      },
      onFormatChanged: (format) {
        if (_calendarFormat != format) {
          setState(() {
            _calendarFormat = format;
          });
        }
      },
      onPageChanged: (focusedDay) {
        _focusedDay = focusedDay;
      },
      eventLoader: (day) {
        return notifier.getEventsForDay(day);
      },
      calendarStyle: const CalendarStyle(
        outsideDaysVisible: false,
        defaultTextStyle: TextStyle(color: Colors.white),
        weekendTextStyle: TextStyle(color: Colors.white70),
        selectedDecoration: BoxDecoration(
          color: AppDesignTokens.primaryBase,
          shape: BoxShape.circle,
        ),
        todayDecoration: BoxDecoration(
          color: Colors.white24,
          shape: BoxShape.circle,
        ),
      ),
      headerStyle: HeaderStyle(
        formatButtonVisible: false,
        titleCentered: true,
        titleTextStyle: const TextStyle(color: Colors.white, fontSize: 16),
        leftChevronIcon: const Icon(Icons.chevron_left, color: Colors.white),
        rightChevronIcon: const Icon(Icons.chevron_right, color: Colors.white),
      ),
      calendarBuilders: CalendarBuilders(
        markerBuilder: (context, date, events) {
          if (events.isEmpty) return null;
          return Positioned(
            bottom: 1,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: events.take(3).map((event) {
                return Container(
                  margin: const EdgeInsets.symmetric(horizontal: 1.0),
                  width: 5.0,
                  height: 5.0,
                  decoration: BoxDecoration(
                    color: Color(event.colorValue),
                    shape: BoxShape.circle,
                  ),
                );
              }).toList(),
            ),
          );
        },
        defaultBuilder: (context, day, focusedDay) {
           return _buildCalendarCell(day, false);
        },
        todayBuilder: (context, day, focusedDay) {
           return _buildCalendarCell(day, true); // Highlight today if needed, but standard style handles bg
        },
        selectedBuilder: (context, day, focusedDay) {
          return _buildCalendarCell(day, false, isSelected: true);
        },
      ),
    );
  }

  Widget _buildCalendarCell(DateTime day, bool isToday, {bool isSelected = false}) {
    final lunarData = _lunarService.getLunarData(day);
    
    return Container(
      margin: const EdgeInsets.all(4),
      decoration: isSelected ? BoxDecoration(
        color: AppDesignTokens.primaryBase,
        shape: BoxShape.circle,
      ) : isToday ? BoxDecoration(
        color: Colors.white24,
        shape: BoxShape.circle,
      ) : null,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${day.day}',
            style: TextStyle(
              color: isSelected || isToday ? Colors.white : Colors.white,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (lunarData.isFestival || lunarData.term.isNotEmpty)
            Text(
              lunarData.displayString,
              style: TextStyle(
                fontSize: 9,
                color: isSelected ? Colors.white : AppDesignTokens.secondaryBase,
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
                color: isSelected ? Colors.white70 : Colors.white38,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildEventList(List<CalendarEventModel> events, CalendarNotifier notifier) {
    if (events.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.event_busy, size: 48, color: Colors.white.withAlpha(50)),
            const SizedBox(height: 10),
            Text(
              '今天没有安排',
              style: TextStyle(color: Colors.white.withAlpha(100)),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: events.length,
      itemBuilder: (context, index) {
        final event = events[index];
        return Dismissible(
          key: Key(event.id),
          direction: DismissDirection.endToStart,
          onDismissed: (direction) {
            notifier.deleteEvent(event.id);
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('事件已删除')),
            );
          },
          background: Container(
            color: Colors.red,
            alignment: Alignment.centerRight,
            padding: const EdgeInsets.only(right: 20),
            child: const Icon(Icons.delete, color: Colors.white),
          ),
          child: Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(20),
              borderRadius: BorderRadius.circular(12),
              border: Border(
                left: BorderSide(color: Color(event.colorValue), width: 4),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      event.title,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    Text(
                      event.isAllDay
                          ? '全天'
                          : '${DateFormat('HH:mm').format(event.startTime)} - ${DateFormat('HH:mm').format(event.endTime)}',
                      style: const TextStyle(color: Colors.white70),
                    ),
                  ],
                ),
                if (event.description != null && event.description!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    event.description!,
                    style: const TextStyle(color: Colors.white54, fontSize: 13),
                  ),
                ],
                if (event.location != null && event.location!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.location_on, size: 12, color: Colors.white54),
                      const SizedBox(width: 4),
                      Text(
                        event.location!,
                        style: const TextStyle(color: Colors.white54, fontSize: 12),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  void _showAddEventDialog(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF1E1E1E),
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
  final DateTime selectedDate;

  const _EventEditDialog({required this.selectedDate});

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
  int _reminderMinutes = 15; // Default 15 min

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
      0,
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
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
        left: 16,
        right: 16,
        top: 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                '新建日程',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              TextButton(
                onPressed: _saveEvent,
                child: const Text('保存', style: TextStyle(color: AppDesignTokens.primaryBase)),
              ),
            ],
          ),
          const SizedBox(height: 20),
          TextField(
            controller: _titleController,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              hintText: '标题',
              hintStyle: TextStyle(color: Colors.white38),
              prefixIcon: Icon(Icons.title, color: Colors.white70),
              border: InputBorder.none,
              filled: true,
              fillColor: Colors.white10,
            ),
          ),
          const SizedBox(height: 10),
          _buildTimeRow(),
          const SizedBox(height: 10),
          SwitchListTile(
            title: const Text('全天', style: TextStyle(color: Colors.white)),
            value: _isAllDay,
            onChanged: (val) => setState(() => _isAllDay = val),
            activeColor: AppDesignTokens.primaryBase,
            contentPadding: EdgeInsets.zero,
          ),
          const SizedBox(height: 10),
          _buildColorPicker(),
          const SizedBox(height: 10),
          TextField(
            controller: _locationController,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              hintText: '地点',
              hintStyle: TextStyle(color: Colors.white38),
              prefixIcon: Icon(Icons.location_on_outlined, color: Colors.white70),
              border: InputBorder.none,
              filled: true,
              fillColor: Colors.white10,
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _descController,
            style: const TextStyle(color: Colors.white),
            decoration: const InputDecoration(
              hintText: '描述',
              hintStyle: TextStyle(color: Colors.white38),
              prefixIcon: Icon(Icons.description_outlined, color: Colors.white70),
              border: InputBorder.none,
              filled: true,
              fillColor: Colors.white10,
            ),
            maxLines: 3,
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildTimeRow() {
    return Row(
      children: [
        Expanded(
          child: GestureDetector(
            onTap: () => _pickDateTime(true),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white10,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('开始', style: TextStyle(color: Colors.white54, fontSize: 12)),
                  Text(
                    DateFormat('MM-dd HH:mm').format(_startTime),
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        const Icon(Icons.arrow_forward, color: Colors.white38, size: 16),
        const SizedBox(width: 10),
        Expanded(
          child: GestureDetector(
            onTap: () => _pickDateTime(false),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white10,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('结束', style: TextStyle(color: Colors.white54, fontSize: 12)),
                  Text(
                    DateFormat('MM-dd HH:mm').format(_endTime),
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildColorPicker() {
    return Row(
      children: _colorOptions.map((color) {
        final isSelected = _colorValue == color;
        return GestureDetector(
          onTap: () => setState(() => _colorValue = color),
          child: Container(
            margin: const EdgeInsets.only(right: 12),
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: Color(color),
              shape: BoxShape.circle,
              border: isSelected ? Border.all(color: Colors.white, width: 2) : null,
            ),
            child: isSelected ? const Icon(Icons.check, size: 16, color: Colors.white) : null,
          ),
        );
      }).toList(),
    );
  }

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
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请输入标题')),
      );
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
      reminderMinutes: [_reminderMinutes], // Default reminder
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

    ref.read(calendarProvider.notifier).addEvent(event);
    context.pop();
  }
}