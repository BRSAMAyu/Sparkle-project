import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class BonfireWidget extends StatefulWidget {

  const BonfireWidget({
    required this.level, super.key,
    this.size = 120,
  });
  final int level; // 1-5
  final double size;

  @override
  State<BonfireWidget> createState() => _BonfireWidgetState();
}

class _BonfireWidgetState extends State<BonfireWidget> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  
  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color _getFireColor() {
    if (widget.level >= 5) return Colors.purpleAccent;
    if (widget.level >= 4) return DS.errorAccent;
    if (widget.level >= 3) return Colors.deepOrangeAccent;
    if (widget.level >= 2) return AppDesignTokens.warningAccent;
    return Colors.amber;
  }

  @override
  Widget build(BuildContext context) {
    final baseColor = _getFireColor();
    final scaleFactor = 1.0 + (widget.level * 0.1);

    return SizedBox(
      width: widget.size * 1.5,
      height: widget.size * 1.5,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Outer Glow
          AnimatedBuilder(
            animation: _controller,
            builder: (context, child) => Container(
                width: widget.size * scaleFactor,
                height: widget.size * scaleFactor,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      baseColor.withValues(alpha: 0.1 + (_controller.value * 0.1)),
                      Colors.transparent,
                    ],
                    stops: const [0.4, 1.0],
                  ),
                ),
              ),
          ),
          
          // Inner Pulse
          AnimatedBuilder(
            animation: _controller,
            builder: (context, child) => Transform.scale(
                scale: 1.0 + (_controller.value * 0.05),
                child: Container(
                  width: widget.size * 0.8 * scaleFactor,
                  height: widget.size * 0.8 * scaleFactor,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        baseColor.withValues(alpha: 0.2),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              ),
          ),

          // Main Icon with shake effect (optional, maybe just scale)
          // Let's use a Stack of icons to create depth
          
          // Background flame (darker)
          Positioned(
            bottom: widget.size * 0.1,
            child: Icon(
              Icons.local_fire_department,
              size: widget.size * scaleFactor,
              color: baseColor.withValues(alpha: 0.5),
            ),
          ),
          
          // Foreground flame (brighter)
          AnimatedBuilder(
            animation: _controller,
            builder: (context, child) => Positioned(
                bottom: widget.size * 0.1 + (_controller.value * 2),
                child: Icon(
                  Icons.local_fire_department,
                  size: widget.size * 0.95 * scaleFactor,
                  color: baseColor,
                ),
              ),
          ),

          // Level Badge
          Positioned(
            bottom: 0,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.9),
                borderRadius: BorderRadius.circular(20),
                boxShadow: AppDesignTokens.shadowSm,
                border: Border.all(color: baseColor.withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.bolt, size: 14, color: baseColor),
                  const SizedBox(width: DS.xs),
                  Text(
                    'Lv.${widget.level}',
                    style: TextStyle(
                      color: baseColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}