import 'package:flutter/material.dart';

class GalaxyScreen extends StatelessWidget {
  const GalaxyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A), // Dark galaxy background
      body: Stack(
        children: [
          // Background stars placeholder
          Positioned.fill(
            child: CustomPaint(
              painter: _StarPainter(),
            ),
          ),
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.auto_awesome_rounded, size: 80, color: Colors.amber),
                const SizedBox(height: 20),
                Text(
                  '知识星图',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  '可视化你的知识连接',
                  style: TextStyle(color: Colors.white70),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StarPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    // Simple placeholder for stars
    final paint = Paint()..color = Colors.white.withOpacity(0.5);
    canvas.drawCircle(Offset(size.width * 0.2, size.height * 0.3), 2, paint);
    canvas.drawCircle(Offset(size.width * 0.8, size.height * 0.2), 3, paint);
    canvas.drawCircle(Offset(size.width * 0.5, size.height * 0.5), 1.5, paint);
    canvas.drawCircle(Offset(size.width * 0.3, size.height * 0.7), 2.5, paint);
    canvas.drawCircle(Offset(size.width * 0.7, size.height * 0.8), 2, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
