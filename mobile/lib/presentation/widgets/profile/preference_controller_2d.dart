import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class PreferenceController2D extends StatefulWidget {
  final double initialDepth; // 0.0 to 1.0 (Top is 1.0)
  final double initialCuriosity; // 0.0 to 1.0 (Right is 1.0)
  final ValueChanged<Offset> onPreferenceChanged;

  const PreferenceController2D({
    required this.onPreferenceChanged, super.key,
    this.initialDepth = 0.5,
    this.initialCuriosity = 0.5,
  });

  @override
  State<PreferenceController2D> createState() => _PreferenceController2DState();
}

class _PreferenceController2DState extends State<PreferenceController2D> {
  Offset _currentPosition = Offset.zero; // Normalized to 0.0-1.0 for x and y

  @override
  void initState() {
    super.initState();
    // Map initial values to normalized coordinates
    // Curiosity (X): 0.0 (Left) -> 1.0 (Right)
    // Depth (Y): 1.0 (Top) -> 0.0 (Bottom) => Inverted for UI Y-axis (0 is Top)
    _currentPosition = Offset(widget.initialCuriosity, 1.0 - widget.initialDepth);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final double size = constraints.biggest.shortestSide;
            const double handleSize = 40; // Size of the draggable flame icon

            // Convert normalized position to local pixel coordinates
            double x = _currentPosition.dx * size;
            double y = _currentPosition.dy * size;

            // Clamp to ensure the center of the handle stays within bounds
            x = x.clamp(handleSize / 2, size - handleSize / 2);
            y = y.clamp(handleSize / 2, size - handleSize / 2);

            return GestureDetector(
              onPanUpdate: (details) {
                final RenderBox renderBox = context.findRenderObject() as RenderBox;
                final Offset localPosition = renderBox.globalToLocal(details.globalPosition);

                // Normalize to 0.0 - 1.0 range
                final double newCuriosity = (localPosition.dx / size).clamp(0.0, 1.0);
                final double newDepth = 1.0 - (localPosition.dy / size).clamp(0.0, 1.0); // Y-axis inverted

                setState(() {
                  _currentPosition = Offset(newCuriosity, 1.0 - newDepth);
                });
                widget.onPreferenceChanged(Offset(newCuriosity, newDepth));
              },
              onTapDown: (details) {
                 final RenderBox renderBox = context.findRenderObject() as RenderBox;
                 final Offset localPosition = renderBox.globalToLocal(details.globalPosition);

                 final double newCuriosity = (localPosition.dx / size).clamp(0.0, 1.0);
                 final double newDepth = 1.0 - (localPosition.dy / size).clamp(0.0, 1.0);

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
                  // Gradient representing the axes
                  gradient: const LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      Color(0xFFE0F2FE), // Light Blue (High Depth/Structure?) - Top
                      Color(0xFFFFF7ED), // Light Orange (Low Depth/Shallow?) - Bottom
                    ],
                  ),
                ),
                child: Stack(
                  children: [
                    // Horizontal Gradient Overlay (Curiosity)
                    Container(
                      decoration: BoxDecoration(
                        borderRadius: AppDesignTokens.borderRadius16,
                        gradient: LinearGradient(
                          begin: Alignment.centerLeft,
                          end: Alignment.centerRight,
                          colors: [
                            Colors.grey.withOpacity(0.1), // Low Curiosity (Focus) - Left
                            Colors.amber.withOpacity(0.3), // High Curiosity - Right
                          ],
                        ),
                      ),
                    ),

                    // Grid lines and axes
                    CustomPaint(
                      size: Size(size, size),
                      painter: _GridAxisPainter(),
                    ),
                    
                    // Labels
                    _buildQuadrantLabels(),

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
                          border: Border.all(color: Colors.white, width: 2),
                        ),
                        child: const Icon(Icons.local_fire_department, color: Colors.white, size: 24),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ],
    );
  }

  Widget _buildQuadrantLabels() {
    const labelPadding = 8.0;
    const textStyle = TextStyle(
      fontSize: 12,
      fontWeight: FontWeight.bold,
      color: AppDesignTokens.neutral600,
    );

    return const Stack(
      children: [
        // Depth Axis (Vertical)
        Align(
          alignment: Alignment.topCenter,
          child: Padding(
            padding: EdgeInsets.only(top: labelPadding),
            child: Text('深度 (High Depth)', style: textStyle),
          ),
        ),
        Align(
          alignment: Alignment.bottomCenter,
          child: Padding(
            padding: EdgeInsets.only(bottom: labelPadding),
            child: Text('浅层 (Shallow)', style: textStyle),
          ),
        ),
        // Curiosity Axis (Horizontal)
        Align(
          alignment: Alignment.centerLeft,
          child: Padding(
            padding: EdgeInsets.only(left: labelPadding),
            child: RotatedBox(
              quarterTurns: 3,
              child: Text('专注 (Focus)', style: textStyle),
            ),
          ),
        ),
        Align(
          alignment: Alignment.centerRight,
          child: Padding(
            padding: EdgeInsets.only(right: labelPadding),
            child: RotatedBox(
              quarterTurns: 1,
              child: Text('好奇 (Curiosity)', style: textStyle),
            ),
          ),
        ),
      ],
    );
  }
}

class _GridAxisPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppDesignTokens.neutral300
      ..strokeWidth = 1;

    final dashPaint = Paint()
      ..color = AppDesignTokens.neutral300.withOpacity(0.5)
      ..strokeWidth = 1
      ..style = PaintingStyle.stroke;

    // Center Cross
    canvas.drawLine(Offset(0, size.height / 2), Offset(size.width, size.height / 2), paint);
    canvas.drawLine(Offset(size.width / 2, 0), Offset(size.width / 2, size.height), paint);

    // Axis Arrows
    _drawArrow(canvas, Offset(size.width / 2, 0), paint, isVertical: true, isStart: true); // Top
    _drawArrow(canvas, Offset(size.width, size.height / 2), paint, isVertical: false, isStart: false); // Right
  }

  void _drawArrow(Canvas canvas, Offset tip, Paint paint, {required bool isVertical, required bool isStart}) {
    const arrowSize = 6.0;
    final path = Path();
    if (isVertical) {
       // Up arrow at Top
       path.moveTo(tip.dx, tip.dy);
       path.lineTo(tip.dx - arrowSize, tip.dy + arrowSize);
       path.lineTo(tip.dx + arrowSize, tip.dy + arrowSize);
    } else {
       // Right arrow
       path.moveTo(tip.dx, tip.dy);
       path.lineTo(tip.dx - arrowSize, tip.dy - arrowSize);
       path.lineTo(tip.dx - arrowSize, tip.dy + arrowSize);
    }
    path.close();
    canvas.drawPath(path, paint..style = PaintingStyle.fill);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
