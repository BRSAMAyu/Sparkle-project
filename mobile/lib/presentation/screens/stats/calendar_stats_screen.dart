import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/presentation/widgets/home/weather_header.dart';

class CalendarStatsScreen extends ConsumerStatefulWidget {
  const CalendarStatsScreen({super.key});

  @override
  ConsumerState<CalendarStatsScreen> createState() => _CalendarStatsScreenState();
}

class _CalendarStatsScreenState extends ConsumerState<CalendarStatsScreen> {
  DateTime _currentDate = DateTime.now();
  String _viewMode = 'Month'; // Month, Year, Week

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppDesignTokens.deepSpaceStart,
      body: Stack(
        children: [
          const Positioned.fill(child: WeatherHeader()),
          SafeArea(
            child: Column(
              children: [
                _buildHeader(context),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        _buildControls(),
                        const SizedBox(height: 20),
                        _buildCalendarView(context),
                        const SizedBox(height: 20),
                        _buildStatsAnalysis(context),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
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
        ],
      ),
    );
  }

  Widget _buildControls() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        IconButton(
          icon: Icon(Icons.chevron_left, color: Colors.white70),
          onPressed: () {
            setState(() {
              if (_viewMode == 'Month') {
                 _currentDate = DateTime(_currentDate.year, _currentDate.month - 1);
              }
            });
          },
        ),
        Text(
          DateFormat('MMMM yyyy', 'zh_CN').format(_currentDate),
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
        ),
        IconButton(
          icon: Icon(Icons.chevron_right, color: Colors.white70),
          onPressed: () {
             setState(() {
              if (_viewMode == 'Month') {
                 _currentDate = DateTime(_currentDate.year, _currentDate.month + 1);
              }
            });
          },
        ),
        Container(
          height: 36,
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(18),
          ),
          child: Row(
            children: ['Week', 'Month', 'Year'].map((mode) {
              final isSelected = _viewMode == mode;
              return GestureDetector(
                onTap: () => setState(() => _viewMode = mode),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: isSelected ? AppDesignTokens.primaryBase : Colors.transparent,
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Text(
                    mode,
                    style: TextStyle(
                      fontSize: 12,
                      color: isSelected ? Colors.white : Colors.white60,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ),
      ],
    );
  }

  Widget _buildCalendarView(BuildContext context) {
    // 7 columns
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      child: Column(
        children: [
          _buildWeekDays(),
          const SizedBox(height: 12),
          _buildMonthGrid(),
        ],
      ),
    );
  }

  Widget _buildWeekDays() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: ['一', '二', '三', '四', '五', '六', '日'].map((day) {
        return SizedBox(
          width: 30,
          child: Center(
            child: Text(
              day,
              style: TextStyle(fontSize: 12, color: Colors.white54),
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildMonthGrid() {
    final daysInMonth = DateTime(_currentDate.year, _currentDate.month + 1, 0).day;
    final firstWeekday = DateTime(_currentDate.year, _currentDate.month, 1).weekday;
    
    // Total cells = offset + days
    final List<Widget> cells = [];
    
    for (int i = 0; i < firstWeekday - 1; i++) {
      cells.add(const SizedBox());
    }

    for (int i = 1; i <= daysInMonth; i++) {
      // Mock data intensity
      int intensity = (i * 3 + _currentDate.month) % 5;
      
      cells.add(
        GestureDetector(
          onTap: () {
            // Show details
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Selected: $i')));
          },
          child: Container(
            decoration: BoxDecoration(
              color: _getColorForLevel(intensity),
              borderRadius: BorderRadius.circular(6),
            ),
            alignment: Alignment.center,
            child: Text('$i', style: TextStyle(color: Colors.white, fontSize: 12)),
          ),
        ),
      );
    }

    return GridView.count(
      shrinkWrap: true,
      crossAxisCount: 7,
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      physics: const NeverScrollableScrollPhysics(),
      children: cells,
    );
  }

  Color _getColorForLevel(int level) {
    const baseColor = Colors.orange;
    switch (level) {
      case 0: return Colors.white.withValues(alpha: 0.05);
      case 1: return baseColor.withValues(alpha: 0.2);
      case 2: return baseColor.withValues(alpha: 0.4);
      case 3: return baseColor.withValues(alpha: 0.6);
      case 4: return baseColor.withValues(alpha: 0.9);
      default: return Colors.white.withValues(alpha: 0.05);
    }
  }

  Widget _buildStatsAnalysis(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '习惯养成分析',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 16),
          _buildStatRow('最长连续专注', '12 天'),
          const Divider(color: Colors.white10),
          _buildStatRow('本月总时长', '45 小时'),
          const Divider(color: Colors.white10),
          _buildStatRow('平均每日完成', '3.5 个任务'),
        ],
      ),
    );
  }

  Widget _buildStatRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: Colors.white70)),
          Text(value, style: TextStyle(color: Colors.orangeAccent, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
