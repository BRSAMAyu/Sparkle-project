import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

class SparkleTappable extends StatefulWidget {
  const SparkleTappable({
    required this.child,
    super.key,
    this.onTap,
    this.pressScale = 0.967,
    this.pressDuration = const Duration(milliseconds: 80),
    this.hapticEvent = SensoryFeedbackEvent.tap,
    this.enableHaptic = true,
    this.borderRadius = BorderRadius.zero,
    this.onLongPress,
    this.behavior = HitTestBehavior.deferToChild,
  });

  final Widget child;
  final VoidCallback? onTap;
  final double pressScale;
  final Duration pressDuration;
  final SensoryFeedbackEvent hapticEvent;
  final bool enableHaptic;
  final BorderRadius borderRadius;
  final VoidCallback? onLongPress;
  final HitTestBehavior behavior;

  @override
  State<SparkleTappable> createState() => _SparkleTappableState();
}

class _SparkleTappableState extends State<SparkleTappable> {
  bool _pressed = false;

  void _setPressed(bool value) {
    if (_pressed == value || !mounted) {
      return;
    }
    setState(() => _pressed = value);
  }

  void _handleTap() {
    if (widget.enableHaptic) {
      unawaited(SensoryFeedbackService.emit(widget.hapticEvent));
    }
    widget.onTap?.call();
  }

  void _handleLongPress() {
    if (widget.enableHaptic) {
      unawaited(
        SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
      );
    }
    widget.onLongPress?.call();
  }

  @override
  Widget build(BuildContext context) => ClipRRect(
        borderRadius: widget.borderRadius,
        child: GestureDetector(
          behavior: widget.behavior,
          onTapDown: widget.onTap != null ? (_) => _setPressed(true) : null,
          onTapUp: widget.onTap != null ? (_) => _setPressed(false) : null,
          onTapCancel: widget.onTap != null ? () => _setPressed(false) : null,
          onTap: widget.onTap != null ? _handleTap : null,
          onLongPress: widget.onLongPress != null ? _handleLongPress : null,
          child: AnimatedScale(
            scale: _pressed ? widget.pressScale : 1,
            duration: widget.pressDuration,
            curve: Curves.easeOut,
            child: widget.child,
          ),
        ),
      );
}
