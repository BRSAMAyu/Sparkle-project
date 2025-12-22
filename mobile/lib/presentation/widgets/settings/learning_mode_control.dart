import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class LearningModeControl extends StatefulWidget {
  final double depth; // 0.0 - 1.0
  final double curiosity; // 0.0 - 1.0
  final Function(double depth, double curiosity) onChanged;

  const LearningModeControl({
    required this.depth, required this.curiosity, required this.onChanged, super.key,
  });

  @override
  State<LearningModeControl> createState() => _LearningModeControlState();
}

class _LearningModeControlState extends State<LearningModeControl> {
  late double _currentDepth;
  late double _currentCuriosity;

  @override
  void initState() {
    super.initState();
    _currentDepth = widget.depth;
    _currentCuriosity = widget.curiosity;
  }

  void _updatePosition(Offset localPosition, Size size) {
    final double dx = localPosition.dx.clamp(0.0, size.width);
    final double dy = localPosition.dy.clamp(0.0, size.height);

    // Curiosity is X axis (0 -> 1)
    final double newCuriosity = dx / size.width;

    // Depth is Y axis (1 -> 0, usually "Deep" is top or bottom? Let's say Top is Deep=1, Bottom is Shallow=0?)
    // Actually typically Top-Right is High-High.
    // Let's say Y=0 (top) is Depth=1, Y=Height (bottom) is Depth=0.
    final double newDepth = 1.0 - (dy / size.height);

    setState(() {
      _currentCuriosity = newCuriosity;
      _currentDepth = newDepth;
    });

    widget.onChanged(_currentDepth, _currentCuriosity);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        AspectRatio(
          aspectRatio: 1.0,
          child: LayoutBuilder(
            builder: (context, constraints) {
              return Container(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  color: Colors.grey.shade900,
                  border: Border.all(color: Colors.white24),
                  boxShadow: [
                     BoxShadow(
                        color: Colors.blue.withOpacity(0.2 * _currentCuriosity),
                        blurRadius: 20,
                        spreadRadius: 5,
                     ),
                  ],
                ),
                child: GestureDetector(
                  onPanUpdate: (details) {
                    _updatePosition(details.localPosition, constraints.biggest);
                  },
                  onTapDown: (details) {
                    _updatePosition(details.localPosition, constraints.biggest);
                  },
                  child: Stack(
                    children: [
                      // Grid lines
                      _buildGrid(constraints.maxWidth, constraints.maxHeight),
                      
                      // Labels
                      const Positioned(left: 10, top: 10, child: Text('深度+', style: TextStyle(color: Colors.white54))),
                      const Positioned(left: 10, bottom: 10, child: Text('深度-', style: TextStyle(color: Colors.white54))),
                      const Positioned(right: 10, bottom: 10, child: Text('好奇+', style: TextStyle(color: Colors.white54))),
                      const Positioned(left: 10, bottom: 10, child: Padding(padding: EdgeInsets.only(left: 40), child: Text('好奇-', style: TextStyle(color: Colors.white54)))),

                      // The Handle
                      Positioned(
                        left: _currentCuriosity * constraints.maxWidth - 15,
                        top: (1.0 - _currentDepth) * constraints.maxHeight - 15,
                        child: Container(
                          width: 30,
                          height: 30,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: Colors.blue.withOpacity(0.8),
                                blurRadius: 10,
                                spreadRadius: 2,
                              ),
                            ],
                          ),
                          child: const Icon(Icons.touch_app, size: 16, color: Colors.blue),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 16),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            _buildInfoChip('深度: ${(_currentDepth * 100).toInt()}%'),
            _buildInfoChip('好奇: ${(_currentCuriosity * 100).toInt()}%'),
          ],
        ),
      ],
    );
  }

  Widget _buildGrid(double width, double height) {
    return CustomPaint(
      size: Size(width, height),
      painter: GridPainter(),
    );
  }

  Widget _buildInfoChip(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white10,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
      ),
    );
  }
}

class GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white10
      ..strokeWidth = 1;

    // Vertical lines
    for (int i = 1; i < 5; i++) {
      final double x = size.width * (i / 5);
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }

    // Horizontal lines
    for (int i = 1; i < 5; i++) {
      final double y = size.height * (i / 5);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
