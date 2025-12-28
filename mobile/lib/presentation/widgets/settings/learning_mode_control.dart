import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
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
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Column(
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            // Limit the size to be reasonable on all screens
            final maxSize = constraints.maxWidth.clamp(200.0, 280.0);

            return Center(
              child: SizedBox(
                width: maxSize,
                height: maxSize,
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    color: isDark ? DS.brandPrimary.shade900 : DS.brandPrimary.shade100,
                    border: Border.all(color: isDark ? DS.brandPrimary24 : DS.brandPrimary.shade300),
                    boxShadow: [
                       BoxShadow(
                          color: AppDesignTokens.primaryBase.withValues(alpha: 0.15 * _currentCuriosity),
                          blurRadius: 16,
                          spreadRadius: 2,
                       ),
                    ],
                  ),
                  child: GestureDetector(
                    onPanUpdate: (details) {
                      _updatePosition(details.localPosition, Size(maxSize, maxSize));
                    },
                    onTapDown: (details) {
                      _updatePosition(details.localPosition, Size(maxSize, maxSize));
                    },
                    child: Stack(
                      children: [
                        // Grid lines
                        _buildGrid(maxSize, maxSize),

                        // Labels - positioned at corners
                        Positioned(
                          left: 8,
                          top: 8,
                          child: Text('深度+', style: TextStyle(color: isDark ? DS.brandPrimary54 : DS.brandPrimary.shade600, fontSize: 11)),
                        ),
                        Positioned(
                          left: 8,
                          bottom: 8,
                          child: Text('深度-', style: TextStyle(color: isDark ? DS.brandPrimary54 : DS.brandPrimary.shade600, fontSize: 11)),
                        ),
                        Positioned(
                          right: 8,
                          bottom: 8,
                          child: Text('好奇+', style: TextStyle(color: isDark ? DS.brandPrimary54 : DS.brandPrimary.shade600, fontSize: 11)),
                        ),
                        Positioned(
                          right: 8,
                          top: 8,
                          child: Text('好奇-', style: TextStyle(color: isDark ? DS.brandPrimary54 : DS.brandPrimary.shade600, fontSize: 11)),
                        ),

                        // The Handle
                        Positioned(
                          left: _currentCuriosity * maxSize - 15,
                          top: (1.0 - _currentDepth) * maxSize - 15,
                          child: Container(
                            width: 30,
                            height: 30,
                            decoration: BoxDecoration(
                              color: DS.brandPrimary,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: AppDesignTokens.primaryBase.withValues(alpha: 0.6),
                                  blurRadius: 8,
                                  spreadRadius: 1,
                                ),
                              ],
                            ),
                            child: const Icon(Icons.touch_app, size: 16, color: AppDesignTokens.primaryBase),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          },
        ),
        const SizedBox(height: DS.md),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _buildInfoChip('深度: ${(_currentDepth * 100).toInt()}%'),
            const SizedBox(width: DS.md),
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
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
      decoration: BoxDecoration(
        color: isDark ? DS.brandPrimary10 : AppDesignTokens.primaryBase.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isDark ? DS.brandPrimary : AppDesignTokens.primaryBase,
          fontWeight: FontWeight.w600,
          fontSize: 13,
        ),
      ),
    );
  }
}

class GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = DS.brandPrimary10
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
