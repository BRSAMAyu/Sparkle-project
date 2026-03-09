import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class DashboardEntrance extends StatefulWidget {
  const DashboardEntrance({
    required this.child,
    super.key,
    this.index = 0,
    this.delay = Duration.zero,
    this.duration,
    this.slideOffset = const Offset(0, 0.04),
    this.stagger = const Duration(milliseconds: 60),
  });

  final Widget child;
  final int index;
  final Duration delay;
  final Duration? duration;
  final Offset slideOffset;
  final Duration stagger;

  @override
  State<DashboardEntrance> createState() => _DashboardEntranceState();
}

class _DashboardEntranceState extends State<DashboardEntrance>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;
  late final Animation<Offset> _offset;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    final reduceMotion = WidgetsBinding
        .instance.platformDispatcher.accessibilityFeatures.disableAnimations;
    _controller = AnimationController(
      vsync: this,
      duration: widget.duration ?? DS.durationNormal,
      value: reduceMotion ? 1 : 0,
    );
    final curve = CurvedAnimation(
      parent: _controller,
      curve: DS.motionCurve(SparkleMotionToken.standard),
    );
    _opacity = Tween<double>(begin: 0, end: 1).animate(curve);
    _offset = Tween<Offset>(
      begin: widget.slideOffset,
      end: Offset.zero,
    ).animate(curve);

    if (!reduceMotion) {
      _timer = Timer(
        widget.delay + (widget.stagger * widget.index),
        _controller.forward,
      );
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (context.reduceMotion) {
      return widget.child;
    }

    return FadeTransition(
      opacity: _opacity,
      child: SlideTransition(
        position: _offset,
        child: widget.child,
      ),
    );
  }
}

class DashboardPressable extends StatefulWidget {
  const DashboardPressable({
    required this.child,
    super.key,
    this.onTap,
    this.borderRadius,
    this.pressedScale = 0.98,
  });

  final Widget child;
  final VoidCallback? onTap;
  final BorderRadius? borderRadius;
  final double pressedScale;

  @override
  State<DashboardPressable> createState() => _DashboardPressableState();
}

class _DashboardPressableState extends State<DashboardPressable> {
  bool _pressed = false;

  void _setPressed(bool value) {
    if (_pressed == value) return;
    setState(() {
      _pressed = value;
    });
  }

  @override
  Widget build(BuildContext context) {
    final duration = DS.motionDuration(
      SparkleMotionToken.micro,
      reduceMotion: context.reduceMotion,
    );

    return AnimatedScale(
      scale: _pressed && !context.reduceMotion ? widget.pressedScale : 1,
      duration: duration,
      curve: DS.motionCurve(SparkleMotionToken.micro),
      child: InkWell(
        onTap: widget.onTap,
        onTapDown: (_) => _setPressed(true),
        onTapCancel: () => _setPressed(false),
        onTapUp: (_) => _setPressed(false),
        borderRadius: widget.borderRadius,
        child: widget.child,
      ),
    );
  }
}
