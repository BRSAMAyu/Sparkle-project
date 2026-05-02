import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';

class MasteryRadarChart extends StatelessWidget {
  const MasteryRadarChart({
    required this.labels,
    required this.values,
    this.selectedIndex,
    this.secondaryValues,
    this.onValueTap,
    super.key,
  });

  final List<String> labels;
  final List<double> values;
  final int? selectedIndex;
  final List<double>? secondaryValues;
  final ValueChanged<int>? onValueTap;

  @override
  Widget build(BuildContext context) {
    final axisCount = math.min(labels.length, values.length);
    if (axisCount < 3) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(context.l10n.reportRadarMinNodes),
      );
    }

    final normalizedValues =
        values.take(axisCount).map((value) => value.clamp(0.0, 1.0)).toList();
    final comparisonValues = secondaryValues
        ?.take(axisCount)
        .map((value) => value.clamp(0.0, 1.0))
        .toList();
    final chartLabels = labels.take(axisCount).toList();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            I18nService.instance.isChinese ? '知识掌握度雷达图' : 'Mastery Radar',
            style: const TextStyle(fontWeight: DS.fontWeightBold),
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 280,
            child: LayoutBuilder(
              builder: (context, constraints) {
                final chartSize = math.min(constraints.maxWidth, 220.0);
                final labelRadius = chartSize / 2 + 24;
                final centerOffset = Offset(constraints.maxWidth / 2, 140);

                return Stack(
                  children: [
                    Positioned.fill(
                      child: CustomPaint(
                        painter: _RadarGridPainter(
                          axisCount: axisCount,
                          levels: 4,
                          centerOffset: centerOffset,
                          radius: chartSize / 2,
                          gridColor: Theme.of(context)
                              .colorScheme
                              .outlineVariant
                              .withValues(alpha: 0.7),
                        ),
                      ),
                    ),
                    Positioned.fill(
                      child: comparisonValues == null
                          ? const SizedBox.shrink()
                          : CustomPaint(
                              painter: _RadarComparisonPainter(
                                values: comparisonValues,
                                centerOffset: centerOffset,
                                radius: chartSize / 2,
                                strokeColor: Theme.of(context)
                                    .colorScheme
                                    .outline
                                    .withValues(alpha: 0.7),
                              ),
                            ),
                    ),
                    Positioned.fill(
                      child: CustomPaint(
                        painter: _RadarValuePainter(
                          values: normalizedValues,
                          centerOffset: centerOffset,
                          radius: chartSize / 2,
                          fillColor: DS.info.withValues(alpha: 0.22),
                          strokeColor: DS.brandPrimary,
                        ),
                      ),
                    ),
                    ...List.generate(axisCount, (index) {
                      final angle =
                          (-math.pi / 2) + (2 * math.pi * index / axisCount);
                      final x = centerOffset.dx + math.cos(angle) * labelRadius;
                      final y = centerOffset.dy + math.sin(angle) * labelRadius;
                      return Positioned(
                        left: x - 42,
                        top: y - 16,
                        width: 84,
                        child: Text(
                          chartLabels[index],
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      );
                    }),
                  ],
                );
              },
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: List.generate(
              axisCount,
              (index) {
                final selected = selectedIndex == index;
                return InkWell(
                  onTap: onValueTap == null ? null : () => onValueTap!(index),
                  borderRadius: BorderRadius.circular(999),
                  child: Ink(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: selected
                          ? DS.info.withValues(alpha: 0.14)
                          : Theme.of(context).colorScheme.surface,
                      borderRadius: BorderRadius.circular(999),
                      border: selected
                          ? Border.all(
                              color: DS.info.withValues(alpha: 0.28),
                            )
                          : null,
                    ),
                    child: Text(
                      '${chartLabels[index]} ${(normalizedValues[index] * 100).round()}%',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            fontWeight: selected ? DS.fontWeightBold : null,
                          ),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _RadarComparisonPainter extends CustomPainter {
  const _RadarComparisonPainter({
    required this.values,
    required this.centerOffset,
    required this.radius,
    required this.strokeColor,
  });

  final List<double> values;
  final Offset centerOffset;
  final double radius;
  final Color strokeColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 3) {
      return;
    }
    final points = List<Offset>.generate(
      values.length,
      (axis) => _pointForAxis(
        axis,
        values.length,
        centerOffset,
        radius * values[axis],
      ),
    );
    final paint = Paint()
      ..color = strokeColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6;
    for (var index = 0; index < points.length; index++) {
      final start = points[index];
      final end = points[(index + 1) % points.length];
      _drawDashedLine(canvas, start, end, paint);
    }
  }

  void _drawDashedLine(Canvas canvas, Offset start, Offset end, Paint paint) {
    const dash = 6.0;
    const gap = 4.0;
    final vector = end - start;
    final distance = vector.distance;
    if (distance == 0) {
      return;
    }
    final direction = vector / distance;
    var progress = 0.0;
    while (progress < distance) {
      final dashStart = start + (direction * progress);
      final dashEnd = start + (direction * math.min(progress + dash, distance));
      canvas.drawLine(dashStart, dashEnd, paint);
      progress += dash + gap;
    }
  }

  @override
  bool shouldRepaint(covariant _RadarComparisonPainter oldDelegate) =>
      oldDelegate.values != values ||
      oldDelegate.centerOffset != centerOffset ||
      oldDelegate.radius != radius ||
      oldDelegate.strokeColor != strokeColor;
}

class _RadarGridPainter extends CustomPainter {
  const _RadarGridPainter({
    required this.axisCount,
    required this.levels,
    required this.centerOffset,
    required this.radius,
    required this.gridColor,
  });

  final int axisCount;
  final int levels;
  final Offset centerOffset;
  final double radius;
  final Color gridColor;

  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = gridColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    for (var level = 1; level <= levels; level++) {
      final levelRadius = radius * (level / levels);
      final path = Path();
      for (var axis = 0; axis < axisCount; axis++) {
        final point = _pointForAxis(axis, axisCount, centerOffset, levelRadius);
        if (axis == 0) {
          path.moveTo(point.dx, point.dy);
        } else {
          path.lineTo(point.dx, point.dy);
        }
      }
      path.close();
      canvas.drawPath(path, gridPaint);
    }

    for (var axis = 0; axis < axisCount; axis++) {
      final point = _pointForAxis(axis, axisCount, centerOffset, radius);
      canvas.drawLine(centerOffset, point, gridPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _RadarGridPainter oldDelegate) =>
      oldDelegate.axisCount != axisCount ||
      oldDelegate.levels != levels ||
      oldDelegate.centerOffset != centerOffset ||
      oldDelegate.radius != radius ||
      oldDelegate.gridColor != gridColor;
}

class _RadarValuePainter extends CustomPainter {
  const _RadarValuePainter({
    required this.values,
    required this.centerOffset,
    required this.radius,
    required this.fillColor,
    required this.strokeColor,
  });

  final List<double> values;
  final Offset centerOffset;
  final double radius;
  final Color fillColor;
  final Color strokeColor;

  @override
  void paint(Canvas canvas, Size size) {
    final fillPaint = Paint()
      ..color = fillColor
      ..style = PaintingStyle.fill;
    final strokePaint = Paint()
      ..color = strokeColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    final pointPaint = Paint()
      ..color = strokeColor
      ..style = PaintingStyle.fill;

    final path = Path();
    for (var axis = 0; axis < values.length; axis++) {
      final point = _pointForAxis(
        axis,
        values.length,
        centerOffset,
        radius * values[axis],
      );
      if (axis == 0) {
        path.moveTo(point.dx, point.dy);
      } else {
        path.lineTo(point.dx, point.dy);
      }
    }
    path.close();

    canvas
      ..drawPath(path, fillPaint)
      ..drawPath(path, strokePaint);

    for (var axis = 0; axis < values.length; axis++) {
      final point = _pointForAxis(
        axis,
        values.length,
        centerOffset,
        radius * values[axis],
      );
      canvas.drawCircle(point, 3.5, pointPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _RadarValuePainter oldDelegate) =>
      oldDelegate.values != values ||
      oldDelegate.centerOffset != centerOffset ||
      oldDelegate.radius != radius ||
      oldDelegate.fillColor != fillColor ||
      oldDelegate.strokeColor != strokeColor;
}

Offset _pointForAxis(
  int axis,
  int axisCount,
  Offset centerOffset,
  double radius,
) {
  final angle = (-math.pi / 2) + (2 * math.pi * axis / axisCount);
  return Offset(
    centerOffset.dx + math.cos(angle) * radius,
    centerOffset.dy + math.sin(angle) * radius,
  );
}
