import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class PreferenceController2D extends StatefulWidget {
  final double initialDepth; // 0.0 to 1.0
  final double initialCuriosity; // 0.0 to 1.0
  final ValueChanged<Offset> onPreferenceChanged;

  const PreferenceController2D({
    super.key,
    this.initialDepth = 0.5,
    this.initialCuriosity = 0.5,
    required this.onPreferenceChanged,
  });

  @override
  State<PreferenceController2D> createState() => _PreferenceController2DState();
}

class _PreferenceController2DState extends State<PreferenceController2D> {
  Offset _currentPosition = Offset.zero; // Normalized to 0.0-1.0 for x and y

  @override
  void initState() {
    super.initState();
    _currentPosition = Offset(widget.initialCuriosity, 1.0 - widget.initialDepth);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final double size = constraints.biggest.shortestSide;
        final double handleSize = 40; // Size of the draggable flame icon

        // Convert normalized position to local pixel coordinates
        double x = _currentPosition.dx * size;
        double y = _currentPosition.dy * size;

        // Clamp to ensure the center of the handle stays within bounds
        x = x.clamp(handleSize / 2, size - handleSize / 2);
        y = y.clamp(handleSize / 2, size - handleSize / 2);

        return GestureDetector(
          onPanUpdate: (details) {
            RenderBox renderBox = context.findRenderObject() as RenderBox;
            Offset localPosition = renderBox.globalToLocal(details.globalPosition);

            // Normalize to 0.0 - 1.0 range
            double newCuriosity = (localPosition.dx / size).clamp(0.0, 1.0);
            double newDepth = 1.0 - (localPosition.dy / size).clamp(0.0, 1.0); // Y-axis inverted for depth

            setState(() {
              _currentPosition = Offset(newCuriosity, 1.0 - newDepth);
            });
            widget.onPreferenceChanged(Offset(newCuriosity, newDepth));
          },
          child: Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              borderRadius: AppDesignTokens.borderRadius16,
              border: Border.all(color: AppDesignTokens.neutral300, width: 2),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Colors.blue.shade50, Colors.purple.shade50,
                  Colors.red.shade50, Colors.amber.shade50,
                ],
              ),
            ),
            child: Stack(
              children: [
                // Grid lines and labels
                _buildQuadrantLabels(size),
                _buildGridLines(size),

                // Draggable Flame Icon
                Positioned(
                  left: x - handleSize / 2,
                  top: y - handleSize / 2,
                  child: Container(
                    width: handleSize,
                    height: handleSize,
                    decoration: BoxDecoration(
                      gradient: AppDesignTokens.primaryGradient,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: AppDesignTokens.primaryBase.withOpacity(0.5),
                          blurRadius: 10,
                          spreadRadius: 2,
                        ),
                      ],
                    ),
                    child: const Icon(Icons.local_fire_department, color: Colors.white, size: 24),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildQuadrantLabels(double size) {
    const textStyle = TextStyle(
      fontSize: 12,
      fontWeight: FontWeight.bold,
      color: AppDesignTokens.neutral800,
      shadows: [Shadow(blurRadius: 2, color: Colors.white)],
    );

    return Column(
      children: [
        Expanded(
          child: Row(
            children: [
              Expanded(child: Center(child: Text('深度专注', style: textStyle))), // Top-left
              Expanded(child: Center(child: Text('深度探索', style: textStyle))), // Top-right
            ],
          ),
        ),
        Expanded(
          child: Row(
            children: [
              Expanded(child: Center(child: Text('快速学习', style: textStyle))), // Bottom-left
              Expanded(child: Center(child: Text('快速浏览', style: textStyle))), // Bottom-right
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildGridLines(double size) {
    return CustomPaint(
      size: Size(size, size),
      painter: _GridPainter(),
    );
  }
}

class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppDesignTokens.neutral300.withOpacity(0.5)
      ..strokeWidth = 1;

    // Horizontal line
    canvas.drawLine(Offset(0, size.height / 2), Offset(size.width, size.height / 2), paint);
    // Vertical line
    canvas.drawLine(Offset(size.width / 2, 0), Offset(size.width / 2, size.height), paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
