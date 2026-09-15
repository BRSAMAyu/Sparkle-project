import 'dart:async';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

/// Edge animation system for galaxy connections
///
/// Features:
/// 1. Flowing energy particles along edges
/// 2. Pulse animations for active connections
/// 3. Fade in/out transitions
/// 4. Bezier curve rendering
/// 5. Gradient color based on connection strength
class GalaxyEdgeAnimator {
  GalaxyEdgeAnimator({
    this.particleSpeed = 100.0,
    this.particleSpacing = 30.0,
    this.particleSize = 3.0,
    this.pulseSpeed = 1.5,
    this.flowEnabled = true,
    this.pulseEnabled = true,
    this.curveFactor = 0.2,
  });

  /// Speed of flowing particles (pixels per second)
  final double particleSpeed;

  /// Spacing between particles
  final double particleSpacing;

  /// Size of particles
  final double particleSize;

  /// Speed of pulse animation
  final double pulseSpeed;

  /// Whether flow animation is enabled
  final bool flowEnabled;

  /// Whether pulse animation is enabled
  final bool pulseEnabled;

  /// Bezier curve factor (0 = straight, 1 = very curved)
  final double curveFactor;

  // Animation state
  double _time = 0.0;
  final Map<String, EdgeAnimationState> _edgeStates = {};

  /// Update animation time
  void update(double deltaTime) {
    _time += deltaTime;

    // Update all edge states
    for (final state in _edgeStates.values) {
      state.update(deltaTime, pulseSpeed);
    }
  }

  /// Get or create animation state for an edge
  EdgeAnimationState getEdgeState(String edgeId) {
    _edgeStates.putIfAbsent(edgeId, EdgeAnimationState.new);
    return _edgeStates[edgeId]!;
  }

  /// Activate edge animation (e.g., when selected)
  void activateEdge(String edgeId) {
    getEdgeState(edgeId).activate();
  }

  /// Deactivate edge animation
  void deactivateEdge(String edgeId) {
    getEdgeState(edgeId).deactivate();
  }

  /// Calculate Bezier control point for curved edges
  Offset calculateControlPoint(Offset start, Offset end,
      {double factor = 0.2,}) {
    final midPoint = (start + end) / 2;
    final perpendicular = Offset(
      -(end.dy - start.dy),
      end.dx - start.dx,
    ).normalized();

    final distance = (end - start).distance;
    return midPoint + perpendicular * distance * factor;
  }

  /// Draw an animated edge
  void drawEdge(
    Canvas canvas,
    GalaxyEdgeModel edge,
    Offset start,
    Offset end,
    Color baseColor, {
    double opacity = 1.0,
    bool isActive = false,
    bool isHighlighted = false,
  }) {
    final state = getEdgeState(edge.id);
    final effectiveOpacity = opacity * state.opacity;

    if (effectiveOpacity <= 0.01) return;

    // Calculate control point for bezier curve
    final controlPoint = calculateControlPoint(start, end, factor: curveFactor);

    // Draw main edge line
    _drawEdgeLine(
      canvas,
      start,
      end,
      controlPoint,
      baseColor.withAlpha((effectiveOpacity * 255).round()),
      edge.strength,
      isHighlighted,
    );

    // Draw flow particles if enabled
    if (flowEnabled && (isActive || isHighlighted)) {
      _drawFlowParticles(
        canvas,
        start,
        end,
        controlPoint,
        baseColor,
        effectiveOpacity,
      );
    }

    // Draw pulse effect if enabled and active
    if (pulseEnabled && state.isActive) {
      _drawPulseEffect(
        canvas,
        start,
        end,
        controlPoint,
        baseColor,
        state.pulseProgress,
      );
    }
  }

  void _drawEdgeLine(
    Canvas canvas,
    Offset start,
    Offset end,
    Offset controlPoint,
    Color color,
    double strength,
    bool isHighlighted,
  ) {
    final path = Path()
      ..moveTo(start.dx, start.dy)
      ..quadraticBezierTo(controlPoint.dx, controlPoint.dy, end.dx, end.dy);

    // Create gradient for edge
    final gradient = ui.Gradient.linear(
      start,
      end,
      [
        color.withValues(alpha: color.a * 0.3),
        color,
        color.withValues(alpha: color.a * 0.3),
      ],
      [0.0, 0.5, 1.0],
    );

    final paint = Paint()
      ..shader = gradient
      ..style = PaintingStyle.stroke
      ..strokeWidth = isHighlighted ? 3.0 + strength * 2 : 1.0 + strength * 1.5
      ..strokeCap = StrokeCap.round;

    canvas.drawPath(path, paint);

    // Draw glow for highlighted edges
    if (isHighlighted) {
      final glowPaint = Paint()
        ..shader = gradient
        ..style = PaintingStyle.stroke
        ..strokeWidth = 8.0 + strength * 3
        ..strokeCap = StrokeCap.round
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);

      canvas.drawPath(path, glowPaint);
    }
  }

  void _drawFlowParticles(
    Canvas canvas,
    Offset start,
    Offset end,
    Offset controlPoint,
    Color color,
    double opacity,
  ) {
    final pathLength = _approximatePathLength(start, end, controlPoint);
    final particleCount = (pathLength / particleSpacing).floor();

    for (var i = 0; i < particleCount; i++) {
      // Calculate particle position along path
      final baseT = i / particleCount;
      final animatedT = (baseT + _time * particleSpeed / pathLength) % 1.0;

      final pos = _getPointOnBezier(start, end, controlPoint, animatedT);

      // Fade particles at ends
      final edgeFade = (animatedT * (1 - animatedT) * 4).clamp(0.0, 1.0);

      final particlePaint = Paint()
        ..color = color.withValues(alpha: opacity * edgeFade * 0.8)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(pos, particleSize * edgeFade, particlePaint);
    }
  }

  void _drawPulseEffect(
    Canvas canvas,
    Offset start,
    Offset end,
    Offset controlPoint,
    Color color,
    double progress,
  ) {
    // Draw expanding pulse along the edge
    final pulsePos = _getPointOnBezier(start, end, controlPoint, progress);
    final pulseSize = 10.0 * (1 - progress) + 5.0;
    final pulseOpacity = (1 - progress) * 0.6;

    final pulsePaint = Paint()
      ..color = color.withValues(alpha: pulseOpacity)
      ..style = PaintingStyle.fill
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);

    canvas.drawCircle(pulsePos, pulseSize, pulsePaint);
  }

  Offset _getPointOnBezier(Offset start, Offset end, Offset control, double t) {
    final mt = 1 - t;
    return Offset(
      mt * mt * start.dx + 2 * mt * t * control.dx + t * t * end.dx,
      mt * mt * start.dy + 2 * mt * t * control.dy + t * t * end.dy,
    );
  }

  double _approximatePathLength(Offset start, Offset end, Offset control) {
    // Approximate bezier length using chord + control polygon
    final chord = (end - start).distance;
    final controlPolygon =
        (control - start).distance + (end - control).distance;
    return (chord + controlPolygon) / 2;
  }

  /// Reset all animation states
  void reset() {
    _time = 0.0;
    _edgeStates.clear();
  }

  /// Dispose resources
  void dispose() {
    _edgeStates.clear();
  }
}

/// Animation state for a single edge
class EdgeAnimationState {
  double _opacity = 0.0;
  double _pulseProgress = 0.0;
  bool _isActive = false;
  bool _isFadingIn = false;
  bool _isFadingOut = false;

  /// Current opacity (0.0 to 1.0)
  double get opacity => _opacity;

  /// Current pulse progress (0.0 to 1.0)
  double get pulseProgress => _pulseProgress;

  /// Whether the edge is currently active
  bool get isActive => _isActive;

  /// Activate the edge
  void activate() {
    _isActive = true;
    _isFadingIn = true;
    _isFadingOut = false;
  }

  /// Deactivate the edge
  void deactivate() {
    _isActive = false;
    _isFadingIn = false;
    _isFadingOut = true;
  }

  /// Update animation state
  void update(double deltaTime, double pulseSpeed) {
    // Update fade animation
    if (_isFadingIn) {
      _opacity = (_opacity + deltaTime * 3).clamp(0.0, 1.0);
      if (_opacity >= 1.0) _isFadingIn = false;
    } else if (_isFadingOut) {
      _opacity = (_opacity - deltaTime * 2).clamp(0.0, 1.0);
      if (_opacity <= 0.0) _isFadingOut = false;
    }

    // Update pulse animation
    if (_isActive) {
      _pulseProgress = (_pulseProgress + deltaTime * pulseSpeed) % 1.0;
    }
  }

  /// Set opacity directly (for immediate fade)
  void setOpacity(double opacity) {
    _opacity = opacity.clamp(0.0, 1.0);
    _isFadingIn = false;
    _isFadingOut = false;
  }
}

/// Extension for Offset to get normalized vector
extension OffsetNormalized on Offset {
  Offset normalized() {
    final len = distance;
    if (len == 0) return Offset.zero;
    return Offset(dx / len, dy / len);
  }
}

/// Edge drawing configuration
class EdgeDrawConfig {
  const EdgeDrawConfig({
    this.strokeWidth = 2.0,
    this.glowRadius = 4.0,
    this.particleCount = 5,
    this.animationDuration = const Duration(milliseconds: 1000),
    this.curveIntensity = 0.2,
    this.enableGlow = true,
    this.enableParticles = true,
    this.enablePulse = true,
  });

  final double strokeWidth;
  final double glowRadius;
  final int particleCount;
  final Duration animationDuration;
  final double curveIntensity;
  final bool enableGlow;
  final bool enableParticles;
  final bool enablePulse;

  EdgeDrawConfig copyWith({
    double? strokeWidth,
    double? glowRadius,
    int? particleCount,
    Duration? animationDuration,
    double? curveIntensity,
    bool? enableGlow,
    bool? enableParticles,
    bool? enablePulse,
  }) =>
      EdgeDrawConfig(
        strokeWidth: strokeWidth ?? this.strokeWidth,
        glowRadius: glowRadius ?? this.glowRadius,
        particleCount: particleCount ?? this.particleCount,
        animationDuration: animationDuration ?? this.animationDuration,
        curveIntensity: curveIntensity ?? this.curveIntensity,
        enableGlow: enableGlow ?? this.enableGlow,
        enableParticles: enableParticles ?? this.enableParticles,
        enablePulse: enablePulse ?? this.enablePulse,
      );
}

/// Animated edge painter for use with CustomPainter
class AnimatedEdgePainter extends CustomPainter {
  AnimatedEdgePainter({
    required this.edges,
    required this.nodePositions,
    required this.animator,
    required this.baseColor,
    this.selectedNodeId,
    this.expandedNodeIds = const {},
    this.config = const EdgeDrawConfig(),
  }) : super(repaint: null);

  final List<GalaxyEdgeModel> edges;
  final Map<String, Offset> nodePositions;
  final GalaxyEdgeAnimator animator;
  final Color baseColor;
  final String? selectedNodeId;
  final Set<String> expandedNodeIds;
  final EdgeDrawConfig config;

  @override
  void paint(Canvas canvas, Size size) {
    for (final edge in edges) {
      final start = nodePositions[edge.sourceId];
      final end = nodePositions[edge.targetId];

      if (start == null || end == null) continue;

      final isHighlighted = selectedNodeId != null &&
          (edge.sourceId == selectedNodeId || edge.targetId == selectedNodeId);

      final isActive = expandedNodeIds.contains(edge.sourceId) ||
          expandedNodeIds.contains(edge.targetId);

      animator.drawEdge(
        canvas,
        edge,
        start,
        end,
        baseColor,
        isActive: isActive,
        isHighlighted: isHighlighted,
      );
    }
  }

  @override
  bool shouldRepaint(covariant AnimatedEdgePainter oldDelegate) =>
      edges != oldDelegate.edges ||
      nodePositions != oldDelegate.nodePositions ||
      selectedNodeId != oldDelegate.selectedNodeId ||
      expandedNodeIds != oldDelegate.expandedNodeIds;
}

/// Edge animation controller for managing animation lifecycle
class EdgeAnimationController with ChangeNotifier {
  EdgeAnimationController({
    required TickerProvider vsync,
    Duration duration = const Duration(seconds: 2),
  }) {
    _controller = AnimationController(vsync: vsync, duration: duration)
      ..addListener(_onTick);
  }

  late final AnimationController _controller;

  final GalaxyEdgeAnimator _animator = GalaxyEdgeAnimator();
  DateTime _lastUpdate = DateTime.now();

  /// Get the edge animator
  GalaxyEdgeAnimator get animator => _animator;

  /// Start animation
  void start() {
    _lastUpdate = DateTime.now();
    unawaited(_controller.repeat());
  }

  /// Stop animation
  void stop() {
    _controller.stop();
  }

  /// Pause animation
  void pause() {
    _controller.stop();
  }

  /// Resume animation
  void resume() {
    _lastUpdate = DateTime.now();
    unawaited(_controller.repeat());
  }

  void _onTick() {
    final now = DateTime.now();
    final deltaTime = now.difference(_lastUpdate).inMilliseconds / 1000.0;
    _lastUpdate = now;

    _animator.update(deltaTime);
    notifyListeners();
  }

  @override
  void dispose() {
    _controller.dispose();
    _animator.dispose();
    super.dispose();
  }
}
