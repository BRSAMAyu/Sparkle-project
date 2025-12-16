import 'package:flutter/material.dart';
import 'package:sparkle/data/models/galaxy_model.dart';

class StarMapPainter extends CustomPainter {
  final List<GalaxyNodeModel> nodes;
  final Map<String, Offset> positions;
  final double scale;

  StarMapPainter({
    required this.nodes,
    required this.positions,
    this.scale = 1.0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Draw Connections
    final linePaint = Paint()
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    for (var node in nodes) {
      if (node.parentId != null) {
        final start = positions[node.parentId];
        final end = positions[node.id];
        
        if (start != null && end != null) {
          final color = _parseColor(node.baseColor).withOpacity(0.3);
          linePaint.color = color;
          canvas.drawLine(start, end, linePaint);
        }
      }
    }

    // Draw Nodes
    final nodePaint = Paint()..style = PaintingStyle.fill;
    final glowPaint = Paint()..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8.0);

    for (var node in nodes) {
      final pos = positions[node.id];
      if (pos == null) continue;

      final color = _parseColor(node.baseColor);
      final radius = 3.0 + node.importance * 2.0;

      if (node.isUnlocked) {
        // Glow
        glowPaint.color = color.withOpacity(0.6 * (node.masteryScore / 100.0 + 0.2));
        canvas.drawCircle(pos, radius * 2.5, glowPaint);
        
        // Core
        nodePaint.color = color;
        canvas.drawCircle(pos, radius, nodePaint);
      } else {
        // Locked: Grey dim
        nodePaint.color = Colors.grey.withOpacity(0.3);
        canvas.drawCircle(pos, radius * 0.8, nodePaint);
      }
      
      // Text Label (only if zoomed in or important)
      if (scale > 0.8 || node.importance >= 4) {
        _drawText(canvas, node.name, pos, color);
      }
    }
  }

  void _drawText(Canvas canvas, String text, Offset pos, Color color) {
    final textSpan = TextSpan(
      text: text,
      style: TextStyle(
        color: Colors.white.withOpacity(0.8),
        fontSize: 10,
      ),
    );
    final textPainter = TextPainter(
      text: textSpan,
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();
    textPainter.paint(canvas, pos + Offset(-textPainter.width / 2, 10));
  }

  Color _parseColor(String? hex) {
    if (hex == null || hex.isEmpty) return Colors.white;
    try {
      return Color(int.parse(hex.replaceFirst('#', '0xFF')));
    } catch (e) {
      return Colors.white;
    }
  }

  @override
  bool shouldRepaint(covariant StarMapPainter oldDelegate) {
    return oldDelegate.nodes != nodes || oldDelegate.positions != positions || oldDelegate.scale != scale;
  }
}
