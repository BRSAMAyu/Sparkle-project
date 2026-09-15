import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

class BonfireWidget extends StatefulWidget {
  const BonfireWidget({
    required this.level,
    super.key,
    this.size = 120,
    this.showCrackleToggle = false,
  });
  final int level; // 1-5
  final double size;
  final bool showCrackleToggle;

  @override
  State<BonfireWidget> createState() => _BonfireWidgetState();
}

class _BonfireWidgetState extends State<BonfireWidget>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  var _crackleEnabled = false;

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
    if (widget.level >= 5) return DS.prismPurple;
    if (widget.level >= 4) return DS.errorAccent;
    if (widget.level >= 3) return DS.error;
    if (widget.level >= 2) return DS.warningAccent;
    return DS.warning;
  }

  @override
  Widget build(BuildContext context) {
    final baseColor = _getFireColor();
    final scaleFactor = 1.0 + (widget.level * 0.1);

    return RepaintBoundary(
      child: SizedBox(
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
                    baseColor.withValues(
                      alpha: 0.1 + (_controller.value * 0.1),
                    ),
                    DS.surfacePrimary.withValues(alpha: 0),
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
                      DS.surfacePrimary.withValues(alpha: 0),
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
                boxShadow: DS.shadowSm,
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
                      fontWeight: DS.fontWeightBold,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (widget.showCrackleToggle)
            Positioned(
              top: 4,
              right: 4,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: DS.surfaceOverlay.withValues(alpha: 0.92),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(
                    color: (_crackleEnabled ? baseColor : DS.borderSubtle)
                        .withValues(alpha: 0.35),
                  ),
                ),
                child: InkWell(
                  borderRadius: BorderRadius.circular(999),
                  onTap: () {
                    setState(() {
                      _crackleEnabled = !_crackleEnabled;
                    });
                    unawaited(
                      SensoryFeedbackService.emit(
                        _crackleEnabled
                            ? SensoryFeedbackEvent.selection
                            : SensoryFeedbackEvent.tap,
                      ),
                    );
                  },
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing8,
                      vertical: DS.spacing6,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _crackleEnabled
                              ? Icons.graphic_eq_rounded
                              : Icons.volume_mute_outlined,
                          size: 14,
                          color: baseColor,
                        ),
                        const SizedBox(width: DS.spacing4),
                        Text(
                          _crackleEnabled ? 'Crackle' : 'Silent',
                          style: TextStyle(
                            color: baseColor,
                            fontSize: 11,
                            fontWeight: DS.fontWeightSemibold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
        ),
      ),
    );
  }
}
