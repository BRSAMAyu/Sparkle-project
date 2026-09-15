import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

class ScrollEdgeHaptics extends StatefulWidget {
  const ScrollEdgeHaptics({
    required this.child,
    super.key,
    this.cooldown = const Duration(milliseconds: 420),
    this.enableSound = false,
  });

  final Widget child;
  final Duration cooldown;
  final bool enableSound;

  @override
  State<ScrollEdgeHaptics> createState() => _ScrollEdgeHapticsState();
}

class _ScrollEdgeHapticsState extends State<ScrollEdgeHaptics> {
  DateTime? _lastTriggerAt;
  bool _topTriggered = false;
  bool _bottomTriggered = false;

  bool _canTrigger() {
    final lastTriggerAt = _lastTriggerAt;
    if (lastTriggerAt == null) {
      return true;
    }
    return DateTime.now().difference(lastTriggerAt) >= widget.cooldown;
  }

  bool _onScrollNotification(ScrollNotification notification) {
    if (notification.depth != 0) {
      return false;
    }
    final metrics = notification.metrics;
    if (!metrics.hasPixels || !metrics.hasContentDimensions) {
      return false;
    }

    final isTop = metrics.atEdge && metrics.pixels <= metrics.minScrollExtent;
    final isBottom =
        metrics.atEdge && metrics.pixels >= metrics.maxScrollExtent;

    if (!metrics.atEdge) {
      _topTriggered = false;
      _bottomTriggered = false;
      return false;
    }

    if (isTop && !_topTriggered && _canTrigger()) {
      _topTriggered = true;
      _bottomTriggered = false;
      _lastTriggerAt = DateTime.now();
      unawaited(
        SensoryFeedbackService.emit(
          SensoryFeedbackEvent.selection,
          enableSound: widget.enableSound,
        ),
      );
      return false;
    }

    if (isBottom && !_bottomTriggered && _canTrigger()) {
      _bottomTriggered = true;
      _topTriggered = false;
      _lastTriggerAt = DateTime.now();
      unawaited(
        SensoryFeedbackService.emit(
          SensoryFeedbackEvent.selection,
          enableSound: widget.enableSound,
        ),
      );
    }

    return false;
  }

  @override
  Widget build(BuildContext context) => NotificationListener<ScrollNotification>(
        onNotification: _onScrollNotification,
        child: widget.child,
      );
}
