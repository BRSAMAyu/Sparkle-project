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
    final width = MediaQuery.of(context).size.width - 32; // minus padding
    final cellWidth = width / 8; // 7 days + 1 label column

    return Column(
      children: [
        // Legend / Type Selector
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: AgendaType.values.map((type) {
            final isSelected = _selectedType == type;
            return GestureDetector(
              onTap: () => setState(() => _selectedType = type),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: _getColor(type).withOpacity(isSelected ? 1.0 : 0.2),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: isSelected ? Colors.white : Colors.transparent,
                    width: 2,
                  ),
                ),
                child: Text(
                  _getLabel(type),
                  style: TextStyle(
                    color: isSelected ? Colors.white : Colors.white70,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: 16),
        
        // Header (Days)
        Row(
          children: [
            const SizedBox(width: 30), // Time label column
            ...['一', '二', '三', '四', '五', '六', '日'].map((day) => 
              Expanded(
                child: Center(
                  child: Text(day, style: const TextStyle(fontWeight: FontWeight.bold)),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),

        // Grid
        SizedBox(
          height: 400, // Fixed height for scrollable area
          child: SingleChildScrollView(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Time Labels
                SizedBox(
                  width: 30,
                  child: Column(
                    children: List.generate(24, (index) => 
                      Container(
                        height: 30,
                        alignment: Alignment.topCenter,
                        child: Text(
                          '$index',
                          style: const TextStyle(fontSize: 10, color: Colors.grey),
                        ),
                      ),
                    ),
                  ),
                ),
                // The Grid
                Expanded(
                  child: GestureDetector(
                    onPanUpdate: (details) {
                      // Calculate which cell is touched
                      // This needs precise math relative to the grid container
                      // For MVP, we use Tap on individual cells via GridView
                    },
                    child: GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 7,
                        childAspectRatio: 1.5, // width/height ratio
                      ),
                      itemCount: 168,
                      itemBuilder: (context, index) {
                        return GestureDetector(
                          onTap: () => _updateCell(index),
                          // Support drag by tracking pointer? 
                          // Simpler: Just tap for now, or drag in a future iteration
                          child: Container(
                            margin: const EdgeInsets.all(1),
                            decoration: BoxDecoration(
                              color: _getColor(_gridState[index]),
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
