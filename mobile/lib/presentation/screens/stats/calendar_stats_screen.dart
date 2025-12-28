import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/core/services/lunar_service.dart';
import 'package:sparkle/data/models/calendar_event_model.dart';
import 'package:sparkle/presentation/providers/calendar_provider.dart';
import 'package:sparkle/presentation/screens/calendar/daily_detail_screen.dart';
import 'package:sparkle/presentation/widgets/home/weather_header.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:uuid/uuid.dart';

enum CalendarViewMode { month, twoWeeks, year }

class CalendarStatsScreen extends ConsumerStatefulWidget {
  const CalendarStatsScreen({super.key});

  @override
  ConsumerState<CalendarStatsScreen> createState() => _CalendarStatsScreenState();
}

class _CalendarStatsScreenState extends ConsumerState<CalendarStatsScreen> {
  CalendarViewMode _viewMode = CalendarViewMode.month;
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;
  final LunarService _lunarService = LunarService();

  @override
  void initState() {
    super.initState();
    _selectedDay = _focusedDay;
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
    final selectedEvents = notifier.getEventsForDay(_selectedDay ?? _focusedDay);

    return Scaffold(
      backgroundColor: AppDesignTokens.deepSpaceStart,
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showAddEventDialog(context),
        backgroundColor: AppDesignTokens.primaryBase,
        child: Icon(Icons.add, color: DS.brandPrimary),
      ),
      body: Stack(
        children: [
          const Positioned.fill(child: WeatherHeader()),
          SafeArea(
            child: Column(
              children: [
                _buildHeader(context),
                _buildViewSwitcher(),
                SizedBox(height: 10),
                Expanded(
                  child: _viewMode == CalendarViewMode.year
                      ? _buildYearView()
                      : Column(
                          children: [
                            _buildTableCalendar(notifier),
                            Divider(color: DS.brandPrimary10Const),
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

  Widget _buildHeader(BuildContext context) => Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          IconButton(
            icon: Icon(Icons.arrow_back_ios_new, color: AppColors.textOnDark(context)),
            onPressed: () => context.pop(),
          ),
          Text(
            '日程与日历',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: AppColors.textOnDark(context),
            ),
          ),
          const Spacer(),
          // Year display
          Text(
            DateFormat('yyyy年').format(_focusedDay),
            style: TextStyle(color: DS.brandPrimary54, fontSize: 16),
          ),
        ],
      ),
    );

  Widget _buildViewSwitcher() => Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      width: double.infinity,
      child: SegmentedButton<CalendarViewMode>(
        segments: const [
           ButtonSegment(value: CalendarViewMode.month, label: Text('月视图')),
           ButtonSegment(value: CalendarViewMode.twoWeeks, label: Text('双周')),
           ButtonSegment(value: CalendarViewMode.year, label: Text('年视图')),
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
                return AppDesignTokens.primaryBase;
              }
              return DS.brandPrimary10;
            },
          ),
          foregroundColor: WidgetStateProperty.all(DS.brandPrimary),
        ),
      ),
    );

  Widget _buildYearView() => LayoutBuilder(
      builder: (context, constraints) {
        // Calculate cell size to fit 3 columns
        final monthWidth = (constraints.maxWidth - 40) / 3;
        final monthHeight = (constraints.maxHeight - 40) / 4;
        
        return GridView.builder(
          padding: EdgeInsets.all(DS.lg),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 3,
            childAspectRatio: monthWidth / monthHeight,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
          ),
          itemCount: 12,
          itemBuilder: (context, index) {
            final monthDate = DateTime(_focusedDay.year, index + 1);
            final isCurrentMonth = monthDate.month == DateTime.now().month && monthDate.year == DateTime.now().year;
            
            return GestureDetector(
              onTap: () {
                 setState(() {
                   _focusedDay = monthDate;
                   _viewMode = CalendarViewMode.month;
                 });
              },
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: isCurrentMonth ? AppDesignTokens.primaryBase.withAlpha(30) : DS.brandPrimary.withAlpha(5),
                  borderRadius: BorderRadius.circular(8),
                  border: isCurrentMonth ? Border.all(color: AppDesignTokens.primaryBase.withAlpha(100)) : null,
                ),
                child: Column(
                  children: [
                    // Month Name
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4.0),
                      child: Text(
                        '${index + 1}月',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: isCurrentMonth ? AppDesignTokens.primaryBase : DS.brandPrimary70,
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

  Widget _buildMiniMonthGrid(DateTime monthDate) {
    final daysInMonth = DateTime(monthDate.year, monthDate.month + 1, 0).day;
    final firstWeekday = DateTime(monthDate.year, monthDate.month).weekday;
    final offset = firstWeekday % 7; // Sunday is 7, but in mini grid let's assume standard Sun-Sat or Mon-Sun. TableCalendar defaults to Mon start usually? Let's stick to Mon=1.
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
            ...List.generate(startOffset, (_) => SizedBox()),
            // Days
            ...List.generate(daysInMonth, (i) {
              final day = i + 1;
              return Center(
                child: Text(
                  '$day',
                  style: TextStyle(
                    fontSize: 8,
                    color: DS.brandPrimary38Const,
                  ),
                ),
              );
            }),
          ],
        );
      },
    );
  }

  Widget _buildTableCalendar(CalendarNotifier notifier) => TableCalendar<CalendarEventModel>(
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
           Navigator.of(context).push(
             MaterialPageRoute(builder: (_) => DailyDetailScreen(date: selectedDay)),
           );
        }
      },
      onFormatChanged: (format) {
         // managed by view switcher
      },
      onPageChanged: (focusedDay) {
        _focusedDay = focusedDay;
      },
      eventLoader: (day) => notifier.getEventsForDay(day),
      calendarStyle: CalendarStyle(
        outsideDaysVisible: false,
        defaultTextStyle: TextStyle(color: DS.brandPrimaryConst),
        weekendTextStyle: TextStyle(color: DS.brandPrimary70Const),
        selectedDecoration: BoxDecoration(
          color: AppDesignTokens.primaryBase,
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
        leftChevronIcon: Icon(Icons.chevron_left, color: DS.brandPrimaryConst),
        rightChevronIcon: Icon(Icons.chevron_right, color: DS.brandPrimaryConst),
      ),
      calendarBuilders: CalendarBuilders(
        markerBuilder: (context, date, events) {
          if (events.isEmpty) return null;
          return Positioned(
            bottom: 1,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: events.take(3).map((event) => Container(
                  margin: const EdgeInsets.symmetric(horizontal: 1.0),
                  width: 5.0,
                  height: 5.0,
                  decoration: BoxDecoration(
                    color: Color(event.colorValue),
                    shape: BoxShape.circle,
                  ),
                ),).toList(),
            ),
          );
        },
        defaultBuilder: (context, day, focusedDay) => _buildCalendarCell(day, false),
        todayBuilder: (context, day, focusedDay) => _buildCalendarCell(day, true),
        selectedBuilder: (context, day, focusedDay) => _buildCalendarCell(day, false, isSelected: true),
      ),
    );

  Widget _buildCalendarCell(DateTime day, bool isToday, {bool isSelected = false}) {
    final lunarData = _lunarService.getLunarData(day);
    
    return Container(
      margin: EdgeInsets.all(DS.xs),
      decoration: isSelected ? BoxDecoration(
        color: AppDesignTokens.primaryBase,
        shape: BoxShape.circle,
      ) : isToday ? BoxDecoration(
        color: DS.brandPrimary24,
        shape: BoxShape.circle,
      ) : null,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${day.day}',
            style: TextStyle(
              color: isSelected || isToday ? DS.brandPrimary : DS.brandPrimary,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (lunarData.isFestival || lunarData.term.isNotEmpty)
            Text(
              lunarData.displayString,
              style: TextStyle(
                fontSize: 9,
                color: isSelected ? DS.brandPrimary : AppDesignTokens.warningAccent, // Orange for festivals
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
                color: isSelected ? DS.brandPrimary70 : DS.brandPrimary38,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildEventList(List<CalendarEventModel> events, CalendarNotifier notifier) {
     // Header for the list
     return Column(
       children: [
         Padding(
           padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
           child: Row(
             mainAxisAlignment: MainAxisAlignment.spaceBetween,
             children: [
               Text(
                 '${DateFormat('MM月dd日').format(_selectedDay ?? _focusedDay)} 日程',
                 style: TextStyle(color: DS.brandPrimary70Const, fontWeight: FontWeight.bold),
               ),
               TextButton.icon(
                 onPressed: () {
                   Navigator.of(context).push(
                     MaterialPageRoute(builder: (_) => DailyDetailScreen(date: _selectedDay ?? _focusedDay)),
                   );
                 },
                 icon: Icon(Icons.info_outline, size: 16, color: AppDesignTokens.primaryBase),
                 label: Text('查看详情', style: TextStyle(color: AppDesignTokens.primaryBase)),
               ),
             ],
           ),
         ),
         Expanded(
           child: events.isEmpty 
           ? Center(
               child: Text('暂无日程', style: TextStyle(color: DS.brandPrimary.withAlpha(100))),
             )
           : ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
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
                    padding: const EdgeInsets.only(right: 20),
                    child: Icon(Icons.delete, color: DS.brandPrimary),
                  ),
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      tileColor: DS.brandPrimary10,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      leading: Container(
                        width: 12,
                        height: 12,
                        decoration: BoxDecoration(
                          color: Color(event.colorValue),
                          shape: BoxShape.circle,
                        ),
                      ),
                      title: Text(event.title, style: TextStyle(color: DS.brandPrimary)),
                      subtitle: Text(
                        event.isAllDay ? '全天' : DateFormat('HH:mm').format(event.startTime),
                        style: TextStyle(color: DS.brandPrimary54),
                      ),
                      trailing: event.recurrenceRule != null ? Icon(Icons.repeat, color: DS.brandPrimary30, size: 16) : null,
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
  String? _recurrenceRule; // null, daily, weekly, monthly

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
              Text(
                '新建日程',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: DS.brandPrimary),
              ),
              TextButton(
                onPressed: _saveEvent,
                child: Text('保存', style: TextStyle(color: AppDesignTokens.primaryBase)),
              ),
            ],
          ),
          SizedBox(height: 20),
          TextField(
            controller: _titleController,
            style: TextStyle(color: DS.brandPrimary),
            decoration: InputDecoration(
              hintText: '标题',
              hintStyle: TextStyle(color: DS.brandPrimary38Const),
              prefixIcon: Icon(Icons.title, color: DS.brandPrimary70Const),
              border: InputBorder.none,
              filled: true,
              fillColor: DS.brandPrimary10Const,
            ),
          ),
          SizedBox(height: 10),
          _buildTimeRow(),
          SizedBox(height: 10),
          _buildOptionsRow(),
          SizedBox(height: 10),
          _buildColorPicker(),
          SizedBox(height: 10),
          TextField(
            controller: _locationController,
            style: TextStyle(color: DS.brandPrimary),
            decoration: InputDecoration(
              hintText: '地点',
              hintStyle: TextStyle(color: DS.brandPrimary38Const),
              prefixIcon: Icon(Icons.location_on_outlined, color: DS.brandPrimary70Const),
              border: InputBorder.none,
              filled: true,
              fillColor: DS.brandPrimary10Const,
            ),
          ),
          SizedBox(height: 10),
          TextField(
            controller: _descController,
            style: TextStyle(color: DS.brandPrimary),
            decoration: InputDecoration(
              hintText: '描述',
              hintStyle: TextStyle(color: DS.brandPrimary38Const),
              prefixIcon: Icon(Icons.description_outlined, color: DS.brandPrimary70Const),
              border: InputBorder.none,
              filled: true,
              fillColor: DS.brandPrimary10Const,
            ),
            maxLines: 3,
          ),
          SizedBox(height: 20),
        ],
      ),
    );

  Widget _buildTimeRow() => Row(
      children: [
        Expanded(
          child: GestureDetector(
            onTap: () => _pickDateTime(true),
            child: Container(
              padding: EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: DS.brandPrimary10Const,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('brandPrimary54', style: TextStyle(fontSize: 12)),
                  Text(
                    DateFormat('MM-dd HH:mm').format(_startTime),
                    style: TextStyle(color: DS.brandPrimaryConst, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
          ),
        ),
        SizedBox(width: 10),
        Icon(Icons.arrow_forward, color: DS.brandPrimary38Const, size: 16),
        SizedBox(width: 10),
        Expanded(
          child: GestureDetector(
            onTap: () => _pickDateTime(false),
            child: Container(
              padding: EdgeInsets.all(DS.md),
              decoration: BoxDecoration(
                color: DS.brandPrimary10Const,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('brandPrimary54', style: TextStyle(fontSize: 12)),
                  Text(
                    DateFormat('MM-dd HH:mm').format(_endTime),
                    style: TextStyle(color: DS.brandPrimaryConst, fontWeight: FontWeight.bold),
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
          title: Text('brandPrimary'),
          value: _isAllDay,
          onChanged: (val) => setState(() => _isAllDay = val),
          activeThumbColor: AppDesignTokens.primaryBase,
          contentPadding: EdgeInsets.zero,
        ),
        ListTile(
          title: Text('brandPrimary'),
          trailing: DropdownButton<int>(
            value: _reminderMinutes,
            dropdownColor: const Color(0xFF2C2C2C),
            style: TextStyle(color: DS.brandPrimary),
            underline: Container(),
            items: const [
              DropdownMenuItem(value: 0, child: Text('日程开始时')),
              DropdownMenuItem(value: 5, child: Text('5分钟前')),
              DropdownMenuItem(value: 15, child: Text('15分钟前')),
              DropdownMenuItem(value: 30, child: Text('30分钟前')),
              DropdownMenuItem(value: 60, child: Text('1小时前')),
              DropdownMenuItem(value: 1440, child: Text('1天前')),
            ],
            onChanged: (val) => setState(() => _reminderMinutes = val!),
          ),
          contentPadding: EdgeInsets.zero,
        ),
        ListTile(
          title: Text('brandPrimary'),
          trailing: DropdownButton<String?>(
            value: _recurrenceRule,
            dropdownColor: const Color(0xFF2C2C2C),
            style: TextStyle(color: DS.brandPrimary),
            underline: Container(),
            items: const [
              DropdownMenuItem(child: Text('不重复')),
              DropdownMenuItem(value: 'daily', child: Text('每天')),
              DropdownMenuItem(value: 'weekly', child: Text('每周')),
              DropdownMenuItem(value: 'monthly', child: Text('每月')),
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
            margin: const EdgeInsets.only(right: 12),
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: Color(color),
              shape: BoxShape.circle,
              border: isSelected ? Border.all(color: DS.brandPrimaryConst, width: 2) : null,
            ),
            child: isSelected ? Icon(Icons.check, size: 16, color: DS.brandPrimary) : null,
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
      reminderMinutes: [_reminderMinutes], 
      recurrenceRule: _recurrenceRule,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

    ref.read(calendarProvider.notifier).addEvent(event);
    context.pop();
  }
}
