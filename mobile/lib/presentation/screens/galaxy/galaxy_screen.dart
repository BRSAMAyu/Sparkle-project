import 'package:flutter/material.dart';
import 'dart:math' as math;

class GalaxyScreen extends StatelessWidget {
  const GalaxyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Dark galaxy background
      body: Stack(
        children: [
          // Background stars and domains
          Positioned.fill(
            child: CustomPaint(
              painter: _GalaxyDomainPainter(),
            ),
          ),
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.black.withOpacity(0.5),
                    boxShadow: [
                      BoxShadow(color: Colors.amber.withOpacity(0.2), blurRadius: 30, spreadRadius: 10),
                    ],
                  ),
                  child: const Icon(Icons.auto_awesome_rounded, size: 60, color: Colors.amber),
                ),
                const SizedBox(height: 20),
                Text(
                  '知识星图',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    shadows: [const Shadow(color: Colors.black, blurRadius: 10)],
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  '探索你的知识疆域',
                  style: TextStyle(color: Colors.white70, shadows: [Shadow(color: Colors.black, blurRadius: 5)]),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GalaxyDomainPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final paint = Paint();

    // 1. Draw Background Stars (Noise)
    // We use a deterministic pseudo-random visual for static UI
    for (int i = 0; i < 100; i++) {
      final x = (i * 137.5) % size.width;
      final y = (i * 293.7) % size.height;
      paint.color = Colors.white.withOpacity(((i % 5) + 1) * 0.1);
      canvas.drawCircle(Offset(x, y), ((i % 3) + 1) * 0.5, paint);
    }

    // 2. Draw Knowledge Domains (Orbits/Regions)
    final domains = [
      _DomainSpec("人工智能", 0, Colors.blue),
      _DomainSpec("计算机科学", 72, Colors.cyan),
      _DomainSpec("数学基础", 144, Colors.purple),
      _DomainSpec("人文社科", 216, Colors.orange),
      _DomainSpec("自然科学", 288, Colors.green),
    ];

    final radius = size.width * 0.35;

    for (var domain in domains) {
      final angle = domain.angle * math.pi / 180;
      final dx = center.dx + radius * 0.8 * math.cos(angle);
      final dy = center.dy + radius * 0.8 * math.sin(angle);

      // Draw connection line to center
      paint.color = domain.color.withOpacity(0.2);
      paint.strokeWidth = 1;
      canvas.drawLine(center, Offset(dx, dy), paint);

      // Draw Domain Circle
      paint.style = PaintingStyle.fill;
      paint.color = domain.color.withOpacity(0.15);
      canvas.drawCircle(Offset(dx, dy), 40, paint);

      paint.style = PaintingStyle.stroke;
      paint.strokeWidth = 2;
      paint.color = domain.color.withOpacity(0.6);
      canvas.drawCircle(Offset(dx, dy), 40, paint);

      // Draw Text
      final textSpan = TextSpan(
        text: domain.name,
        style: TextStyle(
          color: domain.color.withOpacity(0.9),
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
      );
      final textPainter = TextPainter(
        text: textSpan,
        textDirection: TextDirection.ltr,
      )..layout();
      textPainter.paint(canvas, Offset(dx - textPainter.width / 2, dy - textPainter.height / 2));
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _DomainSpec {
  final String name;
  final double angle;
  final Color color;
  _DomainSpec(this.name, this.angle, this.color);
}