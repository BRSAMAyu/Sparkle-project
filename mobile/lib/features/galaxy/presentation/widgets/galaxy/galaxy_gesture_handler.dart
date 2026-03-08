import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_spatial_index.dart';

abstract class GalaxyGestureCommand {
  const GalaxyGestureCommand();
}

class PanCommand extends GalaxyGestureCommand {
  const PanCommand(this.delta);

  final Offset delta;
}

class ZoomCommand extends GalaxyGestureCommand {
  const ZoomCommand({
    required this.scaleDelta,
    required this.focalPoint,
  });

  final double scaleDelta;
  final Offset focalPoint;
}

class TapCommand extends GalaxyGestureCommand {
  const TapCommand({
    required this.screenPosition,
    required this.worldPosition,
    this.hit,
  });

  final Offset screenPosition;
  final Offset worldPosition;
  final GalaxyNodeHit? hit;
}

class LongPressCommand extends GalaxyGestureCommand {
  const LongPressCommand({
    required this.screenPosition,
    required this.worldPosition,
    this.hit,
  });

  final Offset screenPosition;
  final Offset worldPosition;
  final GalaxyNodeHit? hit;
}

class DragNodeCommand extends GalaxyGestureCommand {
  const DragNodeCommand({
    required this.nodeId,
    required this.screenDelta,
  });

  final String nodeId;
  final Offset screenDelta;
}

class FlingCommand extends GalaxyGestureCommand {
  const FlingCommand(this.velocity);

  final Velocity velocity;
}

typedef ScreenToWorld = Offset Function(Offset screenPoint);
typedef NodeHitTest = GalaxyNodeHit? Function(Offset worldPoint);
typedef CommandSink = void Function(GalaxyGestureCommand command);

enum _GestureMode {
  idle,
  pending,
  panning,
  pinching,
  longPress,
}

class GalaxyGestureHandler {
  GalaxyGestureHandler({
    required ScreenToWorld screenToWorld,
    required NodeHitTest hitTestNode,
    required CommandSink onCommand,
    this.tapSlop = 8,
    this.dragCommitWindow = const Duration(milliseconds: 150),
    this.longPressDelay = const Duration(milliseconds: 500),
    this.longPressDragWindow = const Duration(milliseconds: 200),
    this.dragSlop = 12,
    this.minFlingVelocity = 450,
  })  : _screenToWorld = screenToWorld,
        _hitTestNode = hitTestNode,
        _onCommand = onCommand;

  final ScreenToWorld _screenToWorld;
  final NodeHitTest _hitTestNode;
  final CommandSink _onCommand;
  final double tapSlop;
  final Duration dragCommitWindow;
  final Duration longPressDelay;
  final Duration longPressDragWindow;
  final double dragSlop;
  final double minFlingVelocity;

  final Map<int, Offset> _pointerPositions = <int, Offset>{};
  _GestureMode _mode = _GestureMode.idle;
  int? _primaryPointer;
  Offset? _primaryDownPosition;
  Offset? _lastPrimaryPosition;
  Duration? _primaryDownTime;
  Duration? _longPressActivatedAt;
  VelocityTracker? _velocityTracker;
  Timer? _longPressTimer;
  GalaxyNodeHit? _longPressHit;
  bool _isDraggingNode = false;

  void dispose() {
    _cancelTimers();
    _pointerPositions.clear();
  }

  void handlePointerDown(PointerDownEvent event) {
    _pointerPositions[event.pointer] = event.localPosition;

    if (_mode == _GestureMode.idle) {
      _mode = _GestureMode.pending;
      _primaryPointer = event.pointer;
      _primaryDownPosition = event.localPosition;
      _lastPrimaryPosition = event.localPosition;
      _primaryDownTime = event.timeStamp;
      _velocityTracker = VelocityTracker.withKind(event.kind)
        ..addPosition(event.timeStamp, event.localPosition);
      _scheduleLongPress();
      return;
    }

    if (_pointerPositions.length == 2) {
      _cancelTimers();
      _mode = _GestureMode.pinching;
      _longPressHit = null;
      _isDraggingNode = false;
    }
  }

  void handlePointerMove(PointerMoveEvent event) {
    final previousPositions = Map<int, Offset>.from(_pointerPositions);
    _pointerPositions[event.pointer] = event.localPosition;

    if (event.pointer == _primaryPointer) {
      _velocityTracker?.addPosition(event.timeStamp, event.localPosition);
    }

    switch (_mode) {
      case _GestureMode.idle:
        return;
      case _GestureMode.pending:
        _handlePendingMove(event);
      case _GestureMode.panning:
        _handlePanMove(event);
      case _GestureMode.pinching:
        _handlePinchMove(previousPositions);
      case _GestureMode.longPress:
        _handleLongPressMove(event);
    }
  }

  void handlePointerUp(PointerUpEvent event) {
    final upPosition = _pointerPositions[event.pointer] ?? event.localPosition;
    _pointerPositions.remove(event.pointer);

    switch (_mode) {
      case _GestureMode.idle:
        _reset();
      case _GestureMode.pending:
        _finishTapIfNeeded(event.timeStamp, upPosition);
      case _GestureMode.panning:
        _finishPan(event);
      case _GestureMode.pinching:
        if (_pointerPositions.isEmpty) {
          _reset();
        }
      case _GestureMode.longPress:
        _reset();
    }
  }

  void handlePointerCancel(PointerCancelEvent event) {
    _pointerPositions.remove(event.pointer);
    if (_pointerPositions.isEmpty) {
      _reset();
    }
  }

  void handlePointerSignal(PointerSignalEvent event) {
    if (event is! PointerScrollEvent) {
      return;
    }

    final scrollScale = math.exp(-event.scrollDelta.dy * 0.0015);
    _onCommand(
      ZoomCommand(
        scaleDelta: scrollScale,
        focalPoint: event.localPosition,
      ),
    );
  }

  void _handlePendingMove(PointerMoveEvent event) {
    if (event.pointer != _primaryPointer) {
      return;
    }

    final downPosition = _primaryDownPosition;
    final lastPosition = _lastPrimaryPosition;
    final downTime = _primaryDownTime;
    if (downPosition == null || lastPosition == null || downTime == null) {
      return;
    }

    final totalDistance = (event.localPosition - downPosition).distance;
    final elapsed = event.timeStamp - downTime;
    if (totalDistance <= tapSlop) {
      _lastPrimaryPosition = event.localPosition;
      return;
    }

    if (elapsed <= dragCommitWindow || totalDistance > tapSlop) {
      _cancelTimers();
      _mode = _GestureMode.panning;

      final delta = event.localPosition - lastPosition;
      if (delta.distanceSquared > 0) {
        _onCommand(PanCommand(delta));
      }

      _lastPrimaryPosition = event.localPosition;
    }
  }

  void _handlePanMove(PointerMoveEvent event) {
    if (event.pointer != _primaryPointer) {
      return;
    }

    final previous = _lastPrimaryPosition;
    if (previous == null) {
      _lastPrimaryPosition = event.localPosition;
      return;
    }

    final delta = event.localPosition - previous;
    if (delta.distanceSquared > 0) {
      _onCommand(PanCommand(delta));
    }

    _lastPrimaryPosition = event.localPosition;
  }

  void _handlePinchMove(Map<int, Offset> previousPositions) {
    if (_pointerPositions.length < 2 || previousPositions.length < 2) {
      return;
    }

    final previousSample = _buildPinchSample(previousPositions);
    final currentSample = _buildPinchSample(_pointerPositions);
    if (previousSample == null || currentSample == null) {
      return;
    }

    final focalDelta = currentSample.focalPoint - previousSample.focalPoint;
    if (focalDelta.distanceSquared > 0) {
      _onCommand(PanCommand(focalDelta));
    }

    if (previousSample.distance <= 0.0001) {
      return;
    }

    final scaleDelta = currentSample.distance / previousSample.distance;
    if ((scaleDelta - 1).abs() > 0.0001) {
      _onCommand(
        ZoomCommand(
          scaleDelta: scaleDelta,
          focalPoint: currentSample.focalPoint,
        ),
      );
    }
  }

  void _handleLongPressMove(PointerMoveEvent event) {
    if (event.pointer != _primaryPointer) {
      return;
    }

    final lastPosition = _lastPrimaryPosition;
    final longPressHit = _longPressHit;
    final activatedAt = _longPressActivatedAt;
    if (lastPosition == null) {
      _lastPrimaryPosition = event.localPosition;
      return;
    }

    if (longPressHit == null || activatedAt == null) {
      _lastPrimaryPosition = event.localPosition;
      return;
    }

    final screenDelta = event.localPosition - lastPosition;
    if (_isDraggingNode) {
      if (screenDelta.distanceSquared > 0) {
        _onCommand(
          DragNodeCommand(
            nodeId: longPressHit.nodeId,
            screenDelta: screenDelta,
          ),
        );
      }
      _lastPrimaryPosition = event.localPosition;
      return;
    }

    final elapsedSinceLongPress = event.timeStamp - activatedAt;
    final downPosition = _primaryDownPosition ?? event.localPosition;
    final totalDistance = (event.localPosition - downPosition).distance;
    if (elapsedSinceLongPress <= longPressDragWindow &&
        totalDistance > dragSlop) {
      _isDraggingNode = true;
      if (screenDelta.distanceSquared > 0) {
        _onCommand(
          DragNodeCommand(
            nodeId: longPressHit.nodeId,
            screenDelta: screenDelta,
          ),
        );
      }
    }

    _lastPrimaryPosition = event.localPosition;
  }

  void _finishTapIfNeeded(Duration upTime, Offset upPosition) {
    final downPosition = _primaryDownPosition;
    final downTime = _primaryDownTime;
    if (downPosition == null || downTime == null) {
      _reset();
      return;
    }

    final totalDistance = (upPosition - downPosition).distance;
    final elapsed = upTime - downTime;
    if (totalDistance < tapSlop && elapsed < longPressDelay) {
      final worldPoint = _screenToWorld(upPosition);
      _onCommand(
        TapCommand(
          screenPosition: upPosition,
          worldPosition: worldPoint,
          hit: _hitTestNode(worldPoint),
        ),
      );
    }

    _reset();
  }

  void _finishPan(PointerUpEvent event) {
    if (event.pointer == _primaryPointer) {
      final velocity = _velocityTracker?.getVelocity();
      if (velocity != null &&
          velocity.pixelsPerSecond.distance >= minFlingVelocity) {
        _onCommand(FlingCommand(velocity));
      }
    }

    _reset();
  }

  void _scheduleLongPress() {
    _longPressTimer?.cancel();
    _longPressTimer = Timer(longPressDelay, () {
      if (_mode != _GestureMode.pending || _primaryDownPosition == null) {
        return;
      }

      _mode = _GestureMode.longPress;
      _isDraggingNode = false;
      _longPressActivatedAt =
          _primaryDownTime == null ? null : _primaryDownTime! + longPressDelay;
      final screenPosition = _primaryDownPosition!;
      final worldPosition = _screenToWorld(screenPosition);
      final hit = _hitTestNode(worldPosition);
      _longPressHit = hit;
      _onCommand(
        LongPressCommand(
          screenPosition: screenPosition,
          worldPosition: worldPosition,
          hit: hit,
        ),
      );
    });
  }

  void _cancelTimers() {
    _longPressTimer?.cancel();
    _longPressTimer = null;
  }

  void _reset() {
    _cancelTimers();
    _mode = _GestureMode.idle;
    _primaryPointer = null;
    _primaryDownPosition = null;
    _lastPrimaryPosition = null;
    _primaryDownTime = null;
    _longPressActivatedAt = null;
    _velocityTracker = null;
    _pointerPositions.clear();
    _longPressHit = null;
    _isDraggingNode = false;
  }

  _PinchSample? _buildPinchSample(Map<int, Offset> positions) {
    if (positions.length < 2) {
      return null;
    }

    final values = positions.values.take(2).toList(growable: false);
    final first = values[0];
    final second = values[1];
    final focalPoint = Offset(
      (first.dx + second.dx) / 2,
      (first.dy + second.dy) / 2,
    );

    return _PinchSample(
      focalPoint: focalPoint,
      distance: (second - first).distance,
    );
  }
}

class _PinchSample {
  const _PinchSample({
    required this.focalPoint,
    required this.distance,
  });

  final Offset focalPoint;
  final double distance;
}
