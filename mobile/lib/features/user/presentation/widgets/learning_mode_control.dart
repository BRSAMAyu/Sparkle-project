import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class LearningModeControl extends StatefulWidget {
  const LearningModeControl({
    required this.depth,
    required this.curiosity,
    required this.onChanged,
    super.key,
  });
  final double depth; // 0.0 - 1.0
  final double curiosity; // 0.0 - 1.0
  final void Function(double depth, double curiosity) onChanged;

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

  @override
  void didUpdateWidget(covariant LearningModeControl oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.depth != widget.depth ||
        oldWidget.curiosity != widget.curiosity) {
      _currentDepth = widget.depth;
      _currentCuriosity = widget.curiosity;
    }
  }

  void _updatePosition(Offset localPosition, Size size) {
    final dx = localPosition.dx.clamp(0.0, size.width);
    final dy = localPosition.dy.clamp(0.0, size.height);

    // Curiosity is X axis (0 -> 1)
    final newCuriosity = dx / size.width;

    // Depth is Y axis (1 -> 0, usually "Deep" is top or bottom? Let's say Top is Deep=1, Bottom is Shallow=0?)
    // Actually typically Top-Right is High-High.
    // Let's say Y=0 (top) is Depth=1, Y=Height (bottom) is Depth=0.
    final newDepth = 1.0 - (dy / size.height);

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
    final gridColor = DS.brandPrimary10;
    final glowColor = Color.lerp(
          DS.info,
          DS.semanticSuccess,
          _currentCuriosity.clamp(0.0, 1.0),
        ) ??
        DS.primaryBase;

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
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(16),
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Color.alphaBlend(
                          DS.info
                              .withValues(alpha: 0.12 + (_currentDepth * 0.08)),
                          isDark ? DS.surfaceTertiary : DS.neutral100,
                        ),
                        Color.alphaBlend(
                          DS.semanticSuccess.withValues(
                            alpha: 0.08 + (_currentCuriosity * 0.1),
                          ),
                          isDark ? DS.surfaceSecondary : DS.surfacePrimary,
                        ),
                      ],
                    ),
                    border: Border.all(
                      color: isDark ? DS.neutral700 : DS.neutral300,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: glowColor.withValues(
                          alpha: 0.12 + (0.08 * _currentCuriosity),
                        ),
                        blurRadius: 22,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: GestureDetector(
                    onPanUpdate: (details) {
                      _updatePosition(
                        details.localPosition,
                        Size(maxSize, maxSize),
                      );
                    },
                    onTapDown: (details) {
                      _updatePosition(
                        details.localPosition,
                        Size(maxSize, maxSize),
                      );
                    },
                    child: Stack(
                      children: [
                        // Grid lines
                        _buildGrid(maxSize, maxSize, gridColor),

                        Positioned(
                          left: _currentCuriosity * maxSize - 52,
                          top: (1.0 - _currentDepth) * maxSize - 52,
                          child: IgnorePointer(
                            child: Container(
                              width: 104,
                              height: 104,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                gradient: RadialGradient(
                                  colors: [
                                    glowColor.withValues(alpha: 0.22),
                                    glowColor.withValues(alpha: 0.08),
                                    Colors.transparent,
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),

                        // Labels - positioned at edge centers
                        // Depth+ at top center
                        Positioned(
                          top: 8,
                          left: 0,
                          right: 0,
                          child: Center(
                            child: Text(
                              context.l10n.learningModeDepthHigh,
                              style: TextStyle(
                                color: isDark ? DS.neutral400 : DS.neutral600,
                                fontSize: 11,
                              ),
                            ),
                          ),
                        ),
                        // Depth- at bottom center
                        Positioned(
                          bottom: 8,
                          left: 0,
                          right: 0,
                          child: Center(
                            child: Text(
                              context.l10n.learningModeDepthLow,
                              style: TextStyle(
                                color: isDark ? DS.neutral400 : DS.neutral600,
                                fontSize: 11,
                              ),
                            ),
                          ),
                        ),
                        // Curiosity+ at right center
                        Positioned(
                          right: 8,
                          top: 0,
                          bottom: 0,
                          child: Center(
                            child: RotatedBox(
                              quarterTurns: 1,
                              child: Text(
                                context.l10n.learningModeCuriosityHigh,
                                style: TextStyle(
                                  color: isDark ? DS.neutral400 : DS.neutral600,
                                  fontSize: 11,
                                ),
                              ),
                            ),
                          ),
                        ),
                        // Curiosity- at left center
                        Positioned(
                          left: 8,
                          top: 0,
                          bottom: 0,
                          child: Center(
                            child: RotatedBox(
                              quarterTurns: 3,
                              child: Text(
                                context.l10n.learningModeCuriosityLow,
                                style: TextStyle(
                                  color: isDark ? DS.neutral400 : DS.neutral600,
                                  fontSize: 11,
                                ),
                              ),
                            ),
                          ),
                        ),

                        // The Handle
                        Positioned(
                          left: _currentCuriosity * maxSize - 15,
                          top: (1.0 - _currentDepth) * maxSize - 15,
                          child: Container(
                            width: 30,
                            height: 30,
                            decoration: BoxDecoration(
                              color:
                                  isDark ? DS.neutral0 : DS.brandPrimaryConst,
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: glowColor.withValues(
                                    alpha: isDark ? 0.28 : 0.24,
                                  ),
                                  blurRadius: 14,
                                  spreadRadius: 2,
                                ),
                              ],
                            ),
                            child: Icon(
                              Icons.touch_app,
                              size: 16,
                              color: isDark ? DS.neutral900 : DS.primaryBase,
                            ),
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
            _buildInfoChip(
              context.l10n.learningModeDepthValue(
                (_currentDepth * 100).toInt(),
              ),
            ),
            const SizedBox(width: DS.md),
            _buildInfoChip(
              context.l10n.learningModeCuriosityValue(
                (_currentCuriosity * 100).toInt(),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildGrid(double width, double height, Color gridColor) =>
      CustomPaint(
        size: Size(width, height),
        painter: GridPainter(gridColor: gridColor),
      );

  Widget _buildInfoChip(String label) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: DS.md, vertical: DS.xs),
      decoration: BoxDecoration(
        color:
            isDark ? DS.brandPrimary10 : DS.primaryBase.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: isDark ? DS.brandPrimary : DS.primaryBase,
          fontWeight: FontWeight.w600,
          fontSize: 13,
        ),
      ),
    );
  }
}

class GridPainter extends CustomPainter {
  const GridPainter({required this.gridColor});

  final Color gridColor;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = gridColor
      ..strokeWidth = 1;

    // Vertical lines
    for (var i = 1; i < 5; i++) {
      final x = size.width * (i / 5);
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }

    // Horizontal lines
    for (var i = 1; i < 5; i++) {
      final y = size.height * (i / 5);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant GridPainter oldDelegate) =>
      oldDelegate.gridColor != gridColor;
}
