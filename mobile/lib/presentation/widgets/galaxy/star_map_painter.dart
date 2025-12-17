import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:sparkle/data/models/galaxy_model.dart';

/// Pre-processed node data for efficient painting
class ProcessedNode {
  final GalaxyNodeModel node;
  final Color color;
  final double radius;

  ProcessedNode({
    required this.node,
    required this.color,
    required this.radius,
  });
}

/// Pre-processed connection data for efficient painting
class ProcessedConnection {
  final Offset start;
  final Offset end;
  final Color startColor;
  final Color endColor;
  final double distance;

  ProcessedConnection({
    required this.start,
    required this.end,
    required this.startColor,
    required this.endColor,
    required this.distance,
  });
}

class StarMapPainter extends CustomPainter {
  final List<GalaxyNodeModel> nodes;
  final Map<String, Offset> positions;
  final double scale;

  // Pre-processed data (computed once in constructor)
  late final List<ProcessedNode> _processedNodes;
  late final List<ProcessedConnection> _processedConnections;
  late final Map<String, Color> _colorCache;

  StarMapPainter({
    required this.nodes,
    required this.positions,
    this.scale = 1.0,
  }) {
    _preprocessData();
  }

  /// Pre-process all data in the constructor to avoid repeated work in paint()
  void _preprocessData() {
    // Build color cache
    _colorCache = {};
    for (var node in nodes) {
      _colorCache[node.id] = _parseColor(node.baseColor);
    }

    // Build processed nodes
    _processedNodes = nodes.map((node) {
      final color = _colorCache[node.id] ?? Colors.white;
      final radius = 3.0 + node.importance * 2.0;
      return ProcessedNode(node: node, color: color, radius: radius);
    }).toList();

    // Build processed connections with gradient data
    _processedConnections = [];
    for (var node in nodes) {
      if (node.parentId != null) {
        final start = positions[node.parentId];
        final end = positions[node.id];

        if (start != null && end != null) {
          final childColor = _colorCache[node.id] ?? Colors.white;
          final parentColor = _colorCache[node.parentId] ?? Colors.white;
          final distance = (end - start).distance;

          _processedConnections.add(
            ProcessedConnection(
              start: start,
              end: end,
              startColor: parentColor,
              endColor: childColor,
              distance: distance,
            ),
          );
        }
      }
    }
  }

  /// Parse hex color string - only called once per node during preprocessing
  Color _parseColor(String? hex) {
    if (hex == null || hex.isEmpty) return Colors.white;
    try {
      return Color(int.parse(hex.replaceFirst('#', '0xFF')));
    } catch (e) {
      return Colors.white;
    }
  }

  @override
  void paint(Canvas canvas, Size size) {
    _drawConnections(canvas);
    _drawNodes(canvas);
  }

  /// Draw connections with radial gradient effect (energy flow / blood vessel feel)
  void _drawConnections(Canvas canvas) {
    for (var connection in _processedConnections) {
      _drawGradientLine(
        canvas,
        connection.start,
        connection.end,
        connection.startColor,
        connection.endColor,
        connection.distance,
      );
    }
  }

  /// Draw a single connection line with gradient effect
  void _drawGradientLine(
    Canvas canvas,
    Offset start,
    Offset end,
    Color startColor,
    Color endColor,
    double distance,
  ) {
    // Calculate line properties
    final direction = (end - start);
    final length = direction.distance;
    if (length < 1) return;

    // Create gradient shader for the line
    // The line is brighter near the parent (source of energy) and dimmer toward the child
    final gradient = ui.Gradient.linear(
      start,
      end,
      [
        startColor.withOpacity(0.5), // Bright at parent (energy source)
        Color.lerp(startColor, endColor, 0.5)!.withOpacity(0.35), // Mid transition
        endColor.withOpacity(0.2), // Dimmer at child end
      ],
      [0.0, 0.5, 1.0],
    );

    // Base stroke width varies with distance (closer = thicker, like blood vessels near heart)
    final baseWidth = 1.5 + (1.0 / (1.0 + distance * 0.005));

    final linePaint = Paint()
      ..shader = gradient
      ..strokeWidth = baseWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawLine(start, end, linePaint);

    // Add subtle glow effect for energy flow feel
    final glowPaint = Paint()
      ..shader = ui.Gradient.linear(
        start,
        end,
        [
          startColor.withOpacity(0.15),
          endColor.withOpacity(0.05),
        ],
      )
      ..strokeWidth = baseWidth * 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);

    canvas.drawLine(start, end, glowPaint);
  }

  /// Draw all nodes
  void _drawNodes(Canvas canvas) {
    final nodePaint = Paint()..style = PaintingStyle.fill;
    final glowPaint = Paint()..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8.0);

    for (var processedNode in _processedNodes) {
      final node = processedNode.node;
      final pos = positions[node.id];
      if (pos == null) continue;

      final color = processedNode.color;
      final radius = processedNode.radius;

      if (node.isUnlocked) {
        // Calculate mastery-based glow intensity
        final masteryFactor = node.masteryScore / 100.0;
        final glowIntensity = 0.3 + masteryFactor * 0.5;

        // Outer glow (soft, large)
        glowPaint.color = color.withOpacity(glowIntensity * 0.4);
        canvas.drawCircle(pos, radius * 3.0, glowPaint);

        // Inner glow (brighter, smaller)
        glowPaint.color = color.withOpacity(glowIntensity * 0.7);
        glowPaint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 4.0);
        canvas.drawCircle(pos, radius * 1.8, glowPaint);
        glowPaint.maskFilter = const MaskFilter.blur(BlurStyle.normal, 8.0);

        // Core fill
        nodePaint.color = color;
        canvas.drawCircle(pos, radius, nodePaint);

        // Bright center highlight (mastery indicator)
        if (masteryFactor > 0.5) {
          final highlightRadius = radius * 0.4 * masteryFactor;
          nodePaint.color = Colors.white.withOpacity(0.6 + masteryFactor * 0.3);
          canvas.drawCircle(pos, highlightRadius, nodePaint);
        }
      } else {
        // Locked: Grey dim with subtle indication
        nodePaint.color = Colors.grey.withOpacity(0.25);
        canvas.drawCircle(pos, radius * 0.8, nodePaint);

        // Very subtle glow for locked nodes
        glowPaint.color = Colors.grey.withOpacity(0.1);
        canvas.drawCircle(pos, radius * 1.5, glowPaint);
      }

      // Text Label (only if zoomed in or important)
      if (scale > 0.8 || node.importance >= 4) {
        _drawText(canvas, node.name, pos, color, node.isUnlocked);
      }
    }
  }

  void _drawText(Canvas canvas, String text, Offset pos, Color color, bool isUnlocked) {
    final textColor = isUnlocked
        ? Colors.white.withOpacity(0.85)
        : Colors.grey.withOpacity(0.5);

    final textSpan = TextSpan(
      text: text,
      style: TextStyle(
        color: textColor,
        fontSize: 10,
        fontWeight: isUnlocked ? FontWeight.w500 : FontWeight.w400,
        shadows: isUnlocked
            ? [
                Shadow(
                  color: color.withOpacity(0.5),
                  blurRadius: 4,
                ),
              ]
            : null,
      ),
    );
    final textPainter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();
    textPainter.paint(canvas, pos + Offset(-textPainter.width / 2, 12));
  }

  @override
  bool shouldRepaint(covariant StarMapPainter oldDelegate) {
    // Only repaint if data actually changed
    return oldDelegate.nodes != nodes ||
        oldDelegate.positions != positions ||
        oldDelegate.scale != scale;
  }
}
