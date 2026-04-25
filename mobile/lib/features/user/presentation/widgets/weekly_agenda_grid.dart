import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

enum AgendaType {
  busy, // 1 繁忙
  fragmented, // 2 碎片
  relax // 3 放松
}

class WeeklyAgendaGrid extends StatefulWidget {
  const WeeklyAgendaGrid({
    required this.onChanged,
    super.key,
    this.initialData,
  });
  final Map<String, dynamic>? initialData;
  final ValueChanged<Map<String, dynamic>> onChanged;

  @override
  State<WeeklyAgendaGrid> createState() => _WeeklyAgendaGridState();
}

class _WeeklyAgendaGridState extends State<WeeklyAgendaGrid> {
  // Store as flat list for UI: 7 days * 24 hours = 168 slots
  // Index = (hourIndex * 7) + dayIndex
  late List<AgendaType> _gridState;
  AgendaType _selectedType = AgendaType.busy;

  @override
  void initState() {
    super.initState();
    _gridState = List.filled(168, AgendaType.relax);
    _parseInitialData();
  }

  void _parseInitialData() {
    if (widget.initialData == null) return;

    final data = widget.initialData!;
    final grid = data['grid'] as List<dynamic>?;
    if (grid != null && grid.length == 168) {
      _gridState = grid.map((e) {
        final typeStr = e as String?;
        switch (typeStr) {
          case 'busy':
            return AgendaType.busy;
          case 'fragmented':
            return AgendaType.fragmented;
          case 'relax':
          default:
            return AgendaType.relax;
        }
      }).toList();
    }
  }

  Map<String, dynamic> _exportData() => {
        'grid': _gridState.map((e) => e.name).toList(),
      };

  void _updateCell(int index) {
    if (index >= 0 && index < 168) {
      // Avoid unnecessary rebuilds if value is same
      if (_gridState[index] != _selectedType) {
        setState(() {
          _gridState[index] = _selectedType;
        });
        // Call onChanged with structured data
        widget.onChanged(_exportData());
      }
    }
  }

  Color _getColor(AgendaType type) {
    switch (type) {
      case AgendaType.busy:
        return DS.error.shade300;
      case AgendaType.fragmented:
        return DS.success.shade300;
      case AgendaType.relax:
        return DS.brandPrimary.shade100; // Lighter blue for default
    }
  }

  String _getLabel(AgendaType type) {
    switch (type) {
      case AgendaType.busy:
        return context.l10n.agendaBusy;
      case AgendaType.fragmented:
        return context.l10n.agendaFragmented;
      case AgendaType.relax:
        return context.l10n.agendaRelax;
    }
  }

  Color _getLegendTextColor(AgendaType type, bool isSelected) {
    if (isSelected) {
      return Colors.white.withValues(alpha: 0.96);
    }
    switch (type) {
      case AgendaType.busy:
        return DS.error.shade900;
      case AgendaType.fragmented:
        return DS.success.shade900;
      case AgendaType.relax:
        return DS.info.shade900;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    const cellHeight = 32.0; // Increased touch target
    final weekdays = [
      MaterialLocalizations.of(context).narrowWeekdays[1],
      MaterialLocalizations.of(context).narrowWeekdays[2],
      MaterialLocalizations.of(context).narrowWeekdays[3],
      MaterialLocalizations.of(context).narrowWeekdays[4],
      MaterialLocalizations.of(context).narrowWeekdays[5],
      MaterialLocalizations.of(context).narrowWeekdays[6],
      MaterialLocalizations.of(context).narrowWeekdays[0],
    ];

    return Column(
      children: [
        // Legend / Type Selector
        Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          alignment: WrapAlignment.center,
          children: AgendaType.values.map((type) {
            final isSelected = _selectedType == type;
            return GestureDetector(
              onTap: () => setState(() => _selectedType = type),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing10,
                  vertical: DS.spacing8,
                ),
                decoration: BoxDecoration(
                  color:
                      _getColor(type).withValues(alpha: isSelected ? 1.0 : 0.5),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: isSelected
                        ? (isDark ? DS.brandPrimary : DS.brandPrimary54)
                        : DS.surfacePrimary.withValues(alpha: 0),
                    width: 2,
                  ),
                  boxShadow: isSelected
                      ? [
                          BoxShadow(
                            color: _getColor(type).withValues(alpha: 0.4),
                            blurRadius: 4,
                            offset: const Offset(0, 2),
                          ),
                        ]
                      : null,
                ),
                child: Text(
                  _getLabel(type),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: _getLegendTextColor(type, isSelected),
                    fontSize: 12,
                    fontWeight: isSelected ? FontWeight.bold : DS.fontWeightMedium,
                  ),
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: DS.spacing16),

        // Content Area with LayoutBuilder
        LayoutBuilder(
          builder: (context, constraints) {
            final availableWidth = constraints.maxWidth;
            const timeLabelWidth = 32.0;
            final gridWidth = availableWidth - timeLabelWidth;
            final cellWidth = gridWidth / 7;

            return Column(
              children: [
                // Header (Days)
                Row(
                  children: [
                    const SizedBox(width: timeLabelWidth),
                    ...weekdays.map(
                      (day) => Expanded(
                        child: Center(
                          child: Text(
                            day,
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                              color: isDark
                                  ? DS.brandPrimary70
                                  : DS.brandPrimary.shade700,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing8),

                // Main Layout: Row [TimeLabels, Grid]
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Time Labels
                    SizedBox(
                      width: timeLabelWidth,
                      child: Column(
                        children: List.generate(
                          24,
                          (hour) => Container(
                            height: cellHeight,
                            alignment: Alignment.centerRight,
                            padding: const EdgeInsets.only(right: DS.spacing6),
                            child: Text(
                              hour.toString().padLeft(2, '0'),
                              style: TextStyle(
                                fontSize: 10,
                                color: isDark
                                    ? DS.brandPrimary54
                                    : DS.brandPrimary.shade600,
                                fontWeight: DS.fontWeightMedium,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),

                    // The Grid Area
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(DS.spacing4),
                        child: GestureDetector(
                          onPanStart: (details) => _handleInput(
                            details.localPosition,
                            cellWidth,
                            cellHeight,
                          ),
                          onPanUpdate: (details) => _handleInput(
                            details.localPosition,
                            cellWidth,
                            cellHeight,
                          ),
                          onTapDown: (details) => _handleInput(
                            details.localPosition,
                            cellWidth,
                            cellHeight,
                          ),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: List.generate(
                              24,
                              (hour) => Row(
                                children: List.generate(7, (day) {
                                  final index = hour * 7 + day;
                                  return Expanded(
                                    child: Container(
                                      height: cellHeight,
                                      decoration: BoxDecoration(
                                        color: _getColor(_gridState[index]),
                                        border: Border(
                                          right: BorderSide(
                                            color: isDark
                                                ? DS.brandPrimary10
                                                : DS.brandPrimary.shade200,
                                            width: 0.5,
                                          ),
                                          bottom: BorderSide(
                                            color: isDark
                                                ? DS.brandPrimary10
                                                : DS.brandPrimary.shade200,
                                            width: 0.5,
                                          ),
                                        ),
                                      ),
                                    ),
                                  );
                                }),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            );
          },
        ),
      ],
    );
  }

  void _handleInput(Offset localPosition, double cellWidth, double cellHeight) {
    // Clamp coordinates to valid range to prevent index out of bounds
    // We add a small epsilon to width/height to ensure we can reach the last cell easily
    // but floor() handles it.

    final x = localPosition.dx;
    final y = localPosition.dy;

    // Ignore if out of bounds (though GestureDetector is constrained, panUpdate might go out)
    if (x < 0 || y < 0) return;

    final day = (x / cellWidth).floor();
    final hour = (y / cellHeight).floor();

    if (day >= 0 && day < 7 && hour >= 0 && hour < 24) {
      final index = hour * 7 + day;
      _updateCell(index);
    }
  }
}
