import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

enum AgendaType {
  busy,      // 1 繁忙
  fragmented, // 2 碎片
  relax      // 3 放松
}

class WeeklyAgendaGrid extends StatefulWidget {
  final Map<String, dynamic>? initialData;
  final Function(Map<String, dynamic> data) onChanged;

  const WeeklyAgendaGrid({
    required this.onChanged, super.key,
    this.initialData,
  });

  @override
  State<WeeklyAgendaGrid> createState() => _WeeklyAgendaGridState();
}

class _WeeklyAgendaGridState extends State<WeeklyAgendaGrid> {
  // Store as flat list for UI: 7 days * 24 hours = 168 slots
  // Index = (dayIndex * 24) + hourIndex
  late List<AgendaType> _gridState;
  AgendaType _selectedType = AgendaType.busy;

  @override
  void initState() {
    super.initState();
    _gridState = List.filled(168, AgendaType.relax);
    // TODO: Parse initialData if provided
  }

  void _updateCell(int index) {
    if (index >= 0 && index < 168) {
      setState(() {
        _gridState[index] = _selectedType;
      });
      // TODO: Call onChanged with structured data
    }
  }

  Color _getColor(AgendaType type) {
    switch (type) {
      case AgendaType.busy:
        return Colors.red.shade300;
      case AgendaType.fragmented:
        return Colors.green.shade300;
      case AgendaType.relax:
        return Colors.blue.shade300;
    }
  }

  String _getLabel(AgendaType type) {
    switch (type) {
      case AgendaType.busy:
        return '繁忙 (专注)';
      case AgendaType.fragmented:
        return '碎片 (提醒)';
      case AgendaType.relax:
        return '放松 (休息)';
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    // Calculate cell size based on screen width
    final screenWidth = MediaQuery.of(context).size.width;
    final availableWidth = screenWidth - 32 - 28; // minus padding and time label column
    final cellWidth = availableWidth / 7;
    final cellHeight = 20.0; // Fixed cell height for compact view

    return Column(
      children: [
        // Legend / Type Selector
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: AgendaType.values.map((type) {
            final isSelected = _selectedType == type;
            return GestureDetector(
              onTap: () => setState(() => _selectedType = type),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: _getColor(type).withOpacity(isSelected ? 1.0 : 0.3),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isSelected ? (isDark ? Colors.white : Colors.grey.shade700) : Colors.transparent,
                    width: 1.5,
                  ),
                ),
                child: Text(
                  _getLabel(type),
                  style: TextStyle(
                    color: isSelected
                        ? (isDark ? Colors.white : Colors.grey.shade900)
                        : (isDark ? Colors.white70 : Colors.grey.shade700),
                    fontSize: 11,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                  ),
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 12),

        // Header (Days)
        Row(
          children: [
            const SizedBox(width: 28), // Time label column width
            ...['一', '二', '三', '四', '五', '六', '日'].map((day) =>
              SizedBox(
                width: cellWidth,
                child: Center(
                  child: Text(
                    day,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                      color: isDark ? Colors.white70 : Colors.grey.shade700,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),

        // Grid with scrollable area
        Container(
          height: 300, // Fixed height for scrollable area
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: isDark ? Colors.white12 : Colors.grey.shade300),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(7),
            child: SingleChildScrollView(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Time Labels
                  Column(
                    children: List.generate(24, (hour) =>
                      Container(
                        width: 28,
                        height: cellHeight,
                        alignment: Alignment.centerRight,
                        padding: const EdgeInsets.only(right: 4),
                        child: Text(
                          '${hour.toString().padLeft(2, '0')}',
                          style: TextStyle(
                            fontSize: 9,
                            color: isDark ? Colors.white54 : Colors.grey.shade600,
                          ),
                        ),
                      ),
                    ),
                  ),
                  // The Grid
                  Expanded(
                    child: Column(
                      children: List.generate(24, (hour) =>
                        Row(
                          children: List.generate(7, (day) {
                            final index = hour * 7 + day;
                            return GestureDetector(
                              onTap: () => _updateCell(index),
                              child: Container(
                                width: cellWidth,
                                height: cellHeight,
                                margin: const EdgeInsets.all(0.5),
                                decoration: BoxDecoration(
                                  color: _getColor(_gridState[index]),
                                  borderRadius: BorderRadius.circular(2),
                                ),
                              ),
                            );
                          }),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
