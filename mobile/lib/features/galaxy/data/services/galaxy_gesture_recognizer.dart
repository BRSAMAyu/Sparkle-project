import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

// ignore: unused_import
export 'package:flutter/services.dart' show HapticFeedback;

/// Advanced gesture recognition for Galaxy star map
///
/// Features:
/// 1. Double-tap to zoom in/out
/// 2. Pinch to zoom with momentum
/// 3. Two-finger rotation
/// 4. Long press for context menu
/// 5. Velocity-based pan with inertia
/// 6. Edge pan for continuous scrolling
/// 7. Fling gesture detection
class GalaxyGestureRecognizer {
  GalaxyGestureRecognizer({
    this.onPan,
    this.onScale,
    this.onRotate,
    this.onDoubleTap,
    this.onLongPress,
    this.onFling,
    this.onNodeTap,
    this.onNodeLongPress,
    this.onEdgePan,
    this.enableHaptics = true,
    this.enableInertia = true,
    this.inertiaDecay = 0.95,
    this.minScale = 0.1,
    this.maxScale = 5.0,
    this.doubleTapZoomFactor = 2.0,
    this.edgePanThreshold = 50.0,
    this.longPressMinDuration = const Duration(milliseconds: 500),
  });

  // Callbacks
  final void Function(Offset delta)? onPan;
  final void Function(double scale, Offset focalPoint)? onScale;
  final void Function(double rotation, Offset focalPoint)? onRotate;
  final void Function(Offset position)? onDoubleTap;
  final void Function(Offset position)? onLongPress;
  final void Function(Velocity velocity)? onFling;
  final void Function(String nodeId, Offset position)? onNodeTap;
  final void Function(String nodeId, Offset position)? onNodeLongPress;
  final void Function(EdgePanDirection direction, double intensity)? onEdgePan;

  // Configuration
  final bool enableHaptics;
  final bool enableInertia;
  final double inertiaDecay;
  final double minScale;
  final double maxScale;
  final double doubleTapZoomFactor;
  final double edgePanThreshold;
  final Duration longPressMinDuration;

  // Internal state
  double _currentScale = 1.0;
  double _currentRotation = 0.0;
  Offset _lastFocalPoint = Offset.zero;
  DateTime? _lastTapTime;
  Offset? _lastTapPosition;

  // Velocity tracking
  final VelocityTracker _velocityTracker = VelocityTracker.withKind(
    PointerDeviceKind.touch,
  );

  // Inertia animation
  Timer? _inertiaTimer;
  Velocity _currentVelocity = Velocity.zero;

  // Long press tracking
  Timer? _longPressTimer;
  Offset? _longPressPosition;
  bool _isLongPressActive = false;

  // Gesture state
  GesturePhase _currentPhase = GesturePhase.none;
  int _pointerCount = 0;

  // Edge pan tracking
  Timer? _edgePanTimer;
  EdgePanDirection? _activeEdgePan;

  /// Handle pointer down event
  void handlePointerDown(PointerDownEvent event) {
    _pointerCount++;
    _velocityTracker.addPosition(event.timeStamp, event.position);

    // Start long press timer
    _longPressPosition = event.position;
    _longPressTimer?.cancel();
    _longPressTimer = Timer(longPressMinDuration, () {
      _isLongPressActive = true;
      if (enableHaptics) {
        unawaited(HapticFeedback.mediumImpact());
      }
      onLongPress?.call(_longPressPosition!);
    });

    // Cancel inertia
    _stopInertia();

    _currentPhase = GesturePhase.started;
  }

  /// Handle pointer move event
  void handlePointerMove(PointerMoveEvent event, {Size? viewportSize}) {
    _velocityTracker.addPosition(event.timeStamp, event.position);

    // Cancel long press if moved too far
    if (_longPressPosition != null) {
      final distance = (event.position - _longPressPosition!).distance;
      if (distance > 10) {
        _cancelLongPress();
      }
    }

    // Check for edge pan
    if (viewportSize != null) {
      _checkEdgePan(event.position, viewportSize);
    }

    _currentPhase = GesturePhase.updated;
  }

  /// Handle pointer up event
  void handlePointerUp(PointerUpEvent event) {
    _pointerCount = math.max(0, _pointerCount - 1);
    _cancelLongPress();

    // Check for double tap
    final now = DateTime.now();
    if (_lastTapTime != null && _lastTapPosition != null) {
      final timeDiff = now.difference(_lastTapTime!);
      final distance = (event.position - _lastTapPosition!).distance;

      if (timeDiff.inMilliseconds < 300 && distance < 30) {
        _handleDoubleTap(event.position);
        _lastTapTime = null;
        _lastTapPosition = null;
        _currentPhase = GesturePhase.completed;
        return;
      }
    }

    _lastTapTime = now;
    _lastTapPosition = event.position;

    // Apply inertia if enabled
    if (enableInertia && _pointerCount == 0) {
      final velocity = _velocityTracker.getVelocity();
      if (velocity.pixelsPerSecond.distance > 100) {
        _startInertia(velocity);
        onFling?.call(velocity);
      }
    }

    // Stop edge pan
    _stopEdgePan();

    _currentPhase = GesturePhase.completed;
  }

  /// Handle scale start
  void handleScaleStart(ScaleStartDetails details) {
    _lastFocalPoint = details.focalPoint;
    _currentPhase = GesturePhase.started;
  }

  /// Handle scale update
  void handleScaleUpdate(ScaleUpdateDetails details) {
    final delta = details.focalPoint - _lastFocalPoint;

    // Handle pan
    if (details.pointerCount == 1) {
      onPan?.call(delta);
    }

    // Handle scale
    if (details.pointerCount >= 2) {
      final newScale =
          (_currentScale * details.scale).clamp(minScale, maxScale);
      if ((newScale - _currentScale).abs() > 0.001) {
        _currentScale = newScale;
        onScale?.call(newScale, details.focalPoint);

        // Haptic feedback at scale boundaries
        if (enableHaptics) {
          if (newScale <= minScale || newScale >= maxScale) {
            unawaited(HapticFeedback.lightImpact());
          }
        }
      }

      // Handle rotation
      if (details.rotation.abs() > 0.01) {
        _currentRotation = details.rotation;
        onRotate?.call(details.rotation, details.focalPoint);
      }
    }

    _lastFocalPoint = details.focalPoint;
    _currentPhase = GesturePhase.updated;
  }

  /// Handle scale end
  void handleScaleEnd(ScaleEndDetails details) {
    if (enableInertia) {
      final velocity = details.velocity;
      if (velocity.pixelsPerSecond.distance > 100) {
        _startInertia(velocity);
      }
    }

    _currentPhase = GesturePhase.completed;
  }

  void _handleDoubleTap(Offset position) {
    if (enableHaptics) {
      unawaited(HapticFeedback.lightImpact());
    }

    // Toggle zoom level
    final newScale = _currentScale < 1.5
        ? _currentScale * doubleTapZoomFactor
        : _currentScale / doubleTapZoomFactor;

    _currentScale = newScale.clamp(minScale, maxScale);
    onDoubleTap?.call(position);
    onScale?.call(_currentScale, position);
  }

  void _startInertia(Velocity velocity) {
    _stopInertia();
    _currentVelocity = velocity;

    _inertiaTimer = Timer.periodic(
      const Duration(milliseconds: 16),
      (_) => _updateInertia(),
    );
  }

  void _updateInertia() {
    final speed = _currentVelocity.pixelsPerSecond.distance;
    if (speed < 10) {
      _stopInertia();
      return;
    }

    // Apply velocity
    final delta = _currentVelocity.pixelsPerSecond * 0.016;
    onPan?.call(delta);

    // Decay velocity
    _currentVelocity = Velocity(
      pixelsPerSecond: _currentVelocity.pixelsPerSecond * inertiaDecay,
    );
  }

  void _stopInertia() {
    _inertiaTimer?.cancel();
    _inertiaTimer = null;
    _currentVelocity = Velocity.zero;
  }

  void _cancelLongPress() {
    _longPressTimer?.cancel();
    _longPressTimer = null;
    _isLongPressActive = false;
    _longPressPosition = null;
  }

  void _checkEdgePan(Offset position, Size viewportSize) {
    EdgePanDirection? direction;
    double intensity = 0;

    if (position.dx < edgePanThreshold) {
      direction = EdgePanDirection.left;
      intensity = 1 - (position.dx / edgePanThreshold);
    } else if (position.dx > viewportSize.width - edgePanThreshold) {
      direction = EdgePanDirection.right;
      intensity = 1 - ((viewportSize.width - position.dx) / edgePanThreshold);
    } else if (position.dy < edgePanThreshold) {
      direction = EdgePanDirection.up;
      intensity = 1 - (position.dy / edgePanThreshold);
    } else if (position.dy > viewportSize.height - edgePanThreshold) {
      direction = EdgePanDirection.down;
      intensity = 1 - ((viewportSize.height - position.dy) / edgePanThreshold);
    }

    if (direction != null && direction != _activeEdgePan) {
      _startEdgePan(direction, intensity);
    } else if (direction == null && _activeEdgePan != null) {
      _stopEdgePan();
    } else if (direction != null) {
      _activeEdgePan = direction;
      onEdgePan?.call(direction, intensity.clamp(0.0, 1.0));
    }
  }

  void _startEdgePan(EdgePanDirection direction, double intensity) {
    _activeEdgePan = direction;

    _edgePanTimer?.cancel();
    _edgePanTimer = Timer.periodic(
      const Duration(milliseconds: 16),
      (_) {
        if (_activeEdgePan != null) {
          onEdgePan?.call(_activeEdgePan!, intensity);
        }
      },
    );

    if (enableHaptics) {
      unawaited(HapticFeedback.selectionClick());
    }
  }

  void _stopEdgePan() {
    _edgePanTimer?.cancel();
    _edgePanTimer = null;
    _activeEdgePan = null;
  }

  /// Check if a node was tapped at the given position
  void checkNodeTap(
    Offset tapPosition,
    Map<String, Offset> nodePositions,
    double nodeRadius,
  ) {
    for (final entry in nodePositions.entries) {
      final distance = (tapPosition - entry.value).distance;
      if (distance <= nodeRadius) {
        if (enableHaptics) {
          unawaited(HapticFeedback.selectionClick());
        }
        onNodeTap?.call(entry.key, entry.value);
        return;
      }
    }
  }

  /// Check if a node was long-pressed
  void checkNodeLongPress(
    Offset tapPosition,
    Map<String, Offset> nodePositions,
    double nodeRadius,
  ) {
    for (final entry in nodePositions.entries) {
      final distance = (tapPosition - entry.value).distance;
      if (distance <= nodeRadius) {
        if (enableHaptics) {
          unawaited(HapticFeedback.heavyImpact());
        }
        onNodeLongPress?.call(entry.key, entry.value);
        return;
      }
    }
  }

  /// Reset gesture state
  void reset() {
    _stopInertia();
    _cancelLongPress();
    _stopEdgePan();
    _currentScale = 1.0;
    _currentRotation = 0.0;
    _pointerCount = 0;
    _currentPhase = GesturePhase.none;
  }

  /// Dispose resources
  void dispose() {
    _stopInertia();
    _cancelLongPress();
    _stopEdgePan();
  }

  /// Current gesture phase
  GesturePhase get currentPhase => _currentPhase;

  /// Current scale
  double get currentScale => _currentScale;

  /// Current rotation
  double get currentRotation => _currentRotation;

  /// Whether long press is active
  bool get isLongPressActive => _isLongPressActive;

  /// Number of active pointers
  int get pointerCount => _pointerCount;
}

/// Direction of edge pan
enum EdgePanDirection {
  left,
  right,
  up,
  down,
}

/// Gesture phase
enum GesturePhase {
  none,
  started,
  updated,
  completed,
}

/// Galaxy gesture detector widget
class GalaxyGestureDetector extends StatefulWidget {
  const GalaxyGestureDetector({
    required this.child,
    this.onPan,
    this.onScale,
    this.onRotate,
    this.onDoubleTap,
    this.onLongPress,
    this.onFling,
    this.onNodeTap,
    this.onNodeLongPress,
    this.onEdgePan,
    this.nodePositions = const {},
    this.nodeRadius = 20.0,
    this.enableHaptics = true,
    this.enableInertia = true,
    super.key,
  });

  final Widget child;
  final void Function(Offset delta)? onPan;
  final void Function(double scale, Offset focalPoint)? onScale;
  final void Function(double rotation, Offset focalPoint)? onRotate;
  final void Function(Offset position)? onDoubleTap;
  final void Function(Offset position)? onLongPress;
  final void Function(Velocity velocity)? onFling;
  final void Function(String nodeId, Offset position)? onNodeTap;
  final void Function(String nodeId, Offset position)? onNodeLongPress;
  final void Function(EdgePanDirection direction, double intensity)? onEdgePan;
  final Map<String, Offset> nodePositions;
  final double nodeRadius;
  final bool enableHaptics;
  final bool enableInertia;

  @override
  State<GalaxyGestureDetector> createState() => _GalaxyGestureDetectorState();
}

class _GalaxyGestureDetectorState extends State<GalaxyGestureDetector> {
  late GalaxyGestureRecognizer _recognizer;

  @override
  void initState() {
    super.initState();
    _recognizer = GalaxyGestureRecognizer(
      onPan: widget.onPan,
      onScale: widget.onScale,
      onRotate: widget.onRotate,
      onDoubleTap: widget.onDoubleTap,
      onLongPress: (pos) {
        _recognizer.checkNodeLongPress(
          pos,
          widget.nodePositions,
          widget.nodeRadius,
        );
        widget.onLongPress?.call(pos);
      },
      onFling: widget.onFling,
      onEdgePan: widget.onEdgePan,
      enableHaptics: widget.enableHaptics,
      enableInertia: widget.enableInertia,
    );
  }

  @override
  void dispose() {
    _recognizer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Listener(
        onPointerDown: _recognizer.handlePointerDown,
        onPointerMove: (event) => _recognizer.handlePointerMove(
          event,
          viewportSize: MediaQuery.of(context).size,
        ),
        onPointerUp: _recognizer.handlePointerUp,
        child: GestureDetector(
          onScaleStart: _recognizer.handleScaleStart,
          onScaleUpdate: _recognizer.handleScaleUpdate,
          onScaleEnd: _recognizer.handleScaleEnd,
          onTapUp: (details) {
            _recognizer.checkNodeTap(
              details.localPosition,
              widget.nodePositions,
              widget.nodeRadius,
            );
          },
          child: widget.child,
        ),
      );
}

/// Gesture configuration
class GalaxyGestureConfig {
  const GalaxyGestureConfig({
    this.enableDoubleTapZoom = true,
    this.enablePinchZoom = true,
    this.enableRotation = false,
    this.enableInertia = true,
    this.enableEdgePan = true,
    this.enableLongPress = true,
    this.enableHaptics = true,
    this.doubleTapZoomFactor = 2.0,
    this.minScale = 0.1,
    this.maxScale = 5.0,
    this.inertiaDecay = 0.95,
    this.edgePanThreshold = 50.0,
  });

  final bool enableDoubleTapZoom;
  final bool enablePinchZoom;
  final bool enableRotation;
  final bool enableInertia;
  final bool enableEdgePan;
  final bool enableLongPress;
  final bool enableHaptics;
  final double doubleTapZoomFactor;
  final double minScale;
  final double maxScale;
  final double inertiaDecay;
  final double edgePanThreshold;

  GalaxyGestureConfig copyWith({
    bool? enableDoubleTapZoom,
    bool? enablePinchZoom,
    bool? enableRotation,
    bool? enableInertia,
    bool? enableEdgePan,
    bool? enableLongPress,
    bool? enableHaptics,
    double? doubleTapZoomFactor,
    double? minScale,
    double? maxScale,
    double? inertiaDecay,
    double? edgePanThreshold,
  }) =>
      GalaxyGestureConfig(
        enableDoubleTapZoom: enableDoubleTapZoom ?? this.enableDoubleTapZoom,
        enablePinchZoom: enablePinchZoom ?? this.enablePinchZoom,
        enableRotation: enableRotation ?? this.enableRotation,
        enableInertia: enableInertia ?? this.enableInertia,
        enableEdgePan: enableEdgePan ?? this.enableEdgePan,
        enableLongPress: enableLongPress ?? this.enableLongPress,
        enableHaptics: enableHaptics ?? this.enableHaptics,
        doubleTapZoomFactor: doubleTapZoomFactor ?? this.doubleTapZoomFactor,
        minScale: minScale ?? this.minScale,
        maxScale: maxScale ?? this.maxScale,
        inertiaDecay: inertiaDecay ?? this.inertiaDecay,
        edgePanThreshold: edgePanThreshold ?? this.edgePanThreshold,
      );
}
