import 'dart:math' as math;

import 'package:flutter/material.dart';

class MasteryRadarChart extends StatelessWidget {
  const MasteryRadarChart({
    required this.labels,
    required this.values,
    super.key,
  });

  final List<String> labels;
  final List<double> values;

  @override
  Widget build(BuildContext context) {
    final axisCount = math.min(labels.length, values.length);
    if (axisCount < 3) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFF7FAFF),
          borderRadius: BorderRadius.circular(20),
        ),
        child: const Text('至少需要 3 个知识点才能绘制雷达图。'),
      );
    }

    final normalizedValues = values
        .take(axisCount)
        .map((value) => value.clamp(0.0, 1.0))
        .toList();
    final chartLabels = labels.take(axisCount).toList();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF7FAFF),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '知识掌握度雷达图',
            style: TextStyle(fontWeight: FontWeight.w700),
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
                        ),
                      ),
                    ),
                    Positioned.fill(
                      child: CustomPaint(
                        painter: _RadarValuePainter(
                          values: normalizedValues,
                          centerOffset: centerOffset,
                          radius: chartSize / 2,
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
              (index) => Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  '${chartLabels[index]} ${(normalizedValues[index] * 100).round()}%',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RadarGridPainter extends CustomPainter {
  const _RadarGridPainter({
    required this.axisCount,
    required this.levels,
    required this.centerOffset,
    required this.radius,
  });

  final int axisCount;
  final int levels;
  final Offset centerOffset;
  final double radius;

  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = const Color(0xFFCAD8F3)
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
      oldDelegate.radius != radius;
}

class _RadarValuePainter extends CustomPainter {
  const _RadarValuePainter({
    required this.values,
    required this.centerOffset,
    required this.radius,
  });

  final List<double> values;
  final Offset centerOffset;
  final double radius;

  @override
  void paint(Canvas canvas, Size size) {
    final fillPaint = Paint()
      ..color = const Color(0xFF4B7BEC).withValues(alpha: 0.22)
      ..style = PaintingStyle.fill;
    final strokePaint = Paint()
      ..color = const Color(0xFF2A62D5)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    final pointPaint = Paint()
      ..color = const Color(0xFF2A62D5)
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
      oldDelegate.radius != radius;
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
