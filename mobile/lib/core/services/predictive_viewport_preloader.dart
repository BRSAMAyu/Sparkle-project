import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/services/quad_tree.dart';
import 'package:sparkle/data/models/galaxy_model.dart';

/// Predictive viewport preloader for galaxy nodes
///
/// This service predicts which nodes will be needed based on:
/// 1. User pan/scroll velocity and direction
/// 2. Zoom intent detection
/// 3. Historical navigation patterns
///
/// Benefits:
/// - Reduces visual pop-in when scrolling
/// - Preloads node details before they're visible
/// - Smoother user experience
class PredictiveViewportPreloader {
  PredictiveViewportPreloader({
    this.lookAheadTime = const Duration(milliseconds: 300),
    this.predictionRadius = 200.0,
    this.velocityDecay = 0.95,
    this.maxPredictionDistance = 500.0,
    this.preloadMargin = 1.5,
  });

  /// How far ahead to predict (in time)
  final Duration lookAheadTime;

  /// Base radius for preload area
  final double predictionRadius;

  /// Velocity decay factor for prediction
  final double velocityDecay;

  /// Maximum distance to predict
  final double maxPredictionDistance;

  /// Margin multiplier for viewport preloading (1.5 = 50% extra on each side)
  final double preloadMargin;

  // Velocity tracking
  Offset _lastPosition = Offset.zero;
  DateTime _lastUpdateTime = DateTime.now();
  Offset _currentVelocity = Offset.zero;

  // Scale tracking for zoom prediction
  double _lastScale = 1.0;
  double _scaleVelocity = 0.0;

  // Navigation pattern tracking
  final List<NavigationSample> _navigationHistory = [];
  static const int _maxHistorySamples = 50;

  // Preload callbacks
  final List<void Function(Set<String> nodeIds)> _preloadListeners = [];

  // Quad tree for spatial queries
  QuadTree<SimpleQuadTreeItem>? _spatialIndex;

  /// Update spatial index with current node positions
  void updateSpatialIndex(Map<String, Offset> nodePositions) {
    if (nodePositions.isEmpty) {
      _spatialIndex = null;
      return;
    }

    // Calculate bounds
    var minX = double.infinity;
    var minY = double.infinity;
    var maxX = double.negativeInfinity;
    var maxY = double.negativeInfinity;

    for (final pos in nodePositions.values) {
      minX = math.min(minX, pos.dx);
      minY = math.min(minY, pos.dy);
      maxX = math.max(maxX, pos.dx);
      maxY = math.max(maxY, pos.dy);
    }

    // Add padding
    const padding = 100.0;
    final bounds = Rect.fromLTRB(
      minX - padding,
      minY - padding,
      maxX + padding,
      maxY + padding,
    );

    _spatialIndex = QuadTree<SimpleQuadTreeItem>(bounds: bounds);

    for (final entry in nodePositions.entries) {
      _spatialIndex!.insert(
        SimpleQuadTreeItem(id: entry.key, position: entry.value),
      );
    }
  }

  /// Update current viewport position and velocity
  void updateViewportPosition(Offset position, {double? scale}) {
    final now = DateTime.now();
    final dt = now.difference(_lastUpdateTime).inMilliseconds / 1000.0;

    if (dt > 0 && dt < 1.0) {
      // Calculate velocity
      final dx = position.dx - _lastPosition.dx;
      final dy = position.dy - _lastPosition.dy;

      // Smooth velocity with exponential moving average
      const smoothing = 0.3;
      _currentVelocity = Offset(
        _currentVelocity.dx * (1 - smoothing) + (dx / dt) * smoothing,
        _currentVelocity.dy * (1 - smoothing) + (dy / dt) * smoothing,
      );

      // Track scale velocity
      if (scale != null) {
        final dScale = scale - _lastScale;
        _scaleVelocity = _scaleVelocity * (1 - smoothing) + (dScale / dt) * smoothing;
        _lastScale = scale;
      }

      // Record navigation sample
      _recordNavigationSample(position, _currentVelocity, scale ?? _lastScale);
    }

    _lastPosition = position;
    _lastUpdateTime = now;
  }

  void _recordNavigationSample(Offset position, Offset velocity, double scale) {
    _navigationHistory.add(NavigationSample(
      position: position,
      velocity: velocity,
      scale: scale,
      timestamp: DateTime.now(),
    ),);

    // Trim history
    while (_navigationHistory.length > _maxHistorySamples) {
      _navigationHistory.removeAt(0);
    }
  }

  /// Get predicted viewport center based on current velocity
  Offset getPredictedPosition({Duration? lookAhead}) {
    final time = lookAhead ?? lookAheadTime;
    final seconds = time.inMilliseconds / 1000.0;

    // Apply velocity decay for prediction
    var predictedVelocity = _currentVelocity;
    var totalOffset = Offset.zero;
    var remainingTime = seconds;
    const timeStep = 0.016; // ~60fps

    while (remainingTime > 0) {
      final dt = math.min(timeStep, remainingTime);
      totalOffset += predictedVelocity * dt;
      predictedVelocity = predictedVelocity * velocityDecay;
      remainingTime -= dt;
    }

    // Clamp to max prediction distance
    if (totalOffset.distance > maxPredictionDistance) {
      totalOffset = Offset.fromDirection(
        totalOffset.direction,
        maxPredictionDistance,
      );
    }

    return _lastPosition + totalOffset;
  }

  /// Get predicted scale based on zoom velocity
  double getPredictedScale({Duration? lookAhead}) {
    final time = lookAhead ?? lookAheadTime;
    final seconds = time.inMilliseconds / 1000.0;

    return (_lastScale + _scaleVelocity * seconds).clamp(0.1, 5.0);
  }

  /// Get expanded viewport rect for preloading
  Rect getPreloadViewport(Rect currentViewport) {
    final predictedCenter = getPredictedPosition();

    // Calculate direction of movement
    final moveDirection = predictedCenter - currentViewport.center;

    // Expand viewport more in the direction of movement
    final expandedWidth = currentViewport.width * preloadMargin;
    final expandedHeight = currentViewport.height * preloadMargin;

    // Bias expansion towards movement direction
    final extraWidth = moveDirection.dx.abs().clamp(0.0, expandedWidth * 0.3);
    final extraHeight = moveDirection.dy.abs().clamp(0.0, expandedHeight * 0.3);

    // Create expanded viewport centered between current and predicted position
    final centerX = (currentViewport.center.dx + predictedCenter.dx) / 2;
    final centerY = (currentViewport.center.dy + predictedCenter.dy) / 2;

    return Rect.fromCenter(
      center: Offset(centerX, centerY),
      width: expandedWidth + extraWidth,
      height: expandedHeight + extraHeight,
    );
  }

  /// Query nodes that should be preloaded
  Set<String> getPreloadNodeIds(
    Rect currentViewport,
    Map<String, Offset> nodePositions,
  ) {
    if (_spatialIndex == null) {
      updateSpatialIndex(nodePositions);
    }

    if (_spatialIndex == null) return {};

    final preloadViewport = getPreloadViewport(currentViewport);
    final items = _spatialIndex!.queryRange(preloadViewport);

    return items.map((SimpleQuadTreeItem item) => item.id).toSet();
  }

  /// Predict which nodes will likely be needed based on navigation patterns
  Set<String> predictLikelyNodes(
    List<GalaxyNodeModel> nodes,
    Map<String, Offset> nodePositions,
    String? currentSelectedNodeId,
  ) {
    final likelyNodes = <String>{};

    // 1. Add nodes in predicted viewport area
    if (_spatialIndex != null) {
      final predictedCenter = getPredictedPosition();
      final items = _spatialIndex!.queryCircle(
        predictedCenter,
        predictionRadius,
      );
      likelyNodes.addAll(items.map((item) => item.id));
    }

    // 2. If a node is selected, add its neighbors
    if (currentSelectedNodeId != null) {
      final selectedPos = nodePositions[currentSelectedNodeId];
      if (selectedPos != null && _spatialIndex != null) {
        final nearbyItems = _spatialIndex!.queryCircle(
          selectedPos,
          predictionRadius * 1.5,
        );
        likelyNodes.addAll(nearbyItems.map((item) => item.id));
      }
    }

    // 3. Use navigation history to predict common destinations
    likelyNodes.addAll(_predictFromHistory(nodePositions));

    return likelyNodes;
  }

  Set<String> _predictFromHistory(Map<String, Offset> nodePositions) {
    if (_navigationHistory.length < 5) return {};
    if (_spatialIndex == null) return {};

    // Analyze recent movement patterns
    final recent = _navigationHistory.take(10).toList();

    // Calculate average velocity direction
    var avgVelocityX = 0.0;
    var avgVelocityY = 0.0;
    for (final sample in recent) {
      avgVelocityX += sample.velocity.dx;
      avgVelocityY += sample.velocity.dy;
    }
    avgVelocityX /= recent.length;
    avgVelocityY /= recent.length;

    final avgVelocity = Offset(avgVelocityX, avgVelocityY);

    // Project ahead based on average velocity
    if (avgVelocity.distance < 10) return {};

    final projectedPosition = _lastPosition + avgVelocity * 0.5;
    final items = _spatialIndex!.queryCircle(projectedPosition, predictionRadius);

    return items.map((item) => item.id).toSet();
  }

  /// Add preload listener
  void addPreloadListener(void Function(Set<String> nodeIds) listener) {
    _preloadListeners.add(listener);
  }

  /// Remove preload listener
  void removePreloadListener(void Function(Set<String> nodeIds) listener) {
    _preloadListeners.remove(listener);
  }

  /// Notify listeners of nodes to preload
  void notifyPreload(Set<String> nodeIds) {
    for (final listener in _preloadListeners) {
      listener(nodeIds);
    }
  }

  /// Reset all tracking state
  void reset() {
    _currentVelocity = Offset.zero;
    _scaleVelocity = 0.0;
    _navigationHistory.clear();
    _spatialIndex = null;
  }

  /// Get current movement direction (normalized)
  Offset get movementDirection {
    if (_currentVelocity.distance < 1) return Offset.zero;
    return Offset.fromDirection(_currentVelocity.direction);
  }

  /// Get current speed (pixels per second)
  double get currentSpeed => _currentVelocity.distance;

  /// Check if user is actively scrolling
  bool get isScrolling => currentSpeed > 50;

  /// Check if user is zooming
  bool get isZooming => _scaleVelocity.abs() > 0.05;
}

/// Navigation sample for pattern tracking
class NavigationSample {
  const NavigationSample({
    required this.position,
    required this.velocity,
    required this.scale,
    required this.timestamp,
  });

  final Offset position;
  final Offset velocity;
  final double scale;
  final DateTime timestamp;
}

/// Preloader integration mixin for Galaxy widgets
mixin PredictivePreloaderMixin<T extends StatefulWidget> on State<T> {
  late final PredictiveViewportPreloader _preloader;
  Timer? _preloadTimer;

  PredictiveViewportPreloader get preloader => _preloader;

  @protected
  void initPreloader({
    Duration lookAheadTime = const Duration(milliseconds: 300),
    double predictionRadius = 200.0,
  }) {
    _preloader = PredictiveViewportPreloader(
      lookAheadTime: lookAheadTime,
      predictionRadius: predictionRadius,
    );

    // Start periodic preload check
    _preloadTimer = Timer.periodic(
      const Duration(milliseconds: 100),
      (_) => _checkPreload(),
    );
  }

  @protected
  void disposePreloader() {
    _preloadTimer?.cancel();
    _preloader.reset();
  }

  /// Override to provide current viewport
  Rect? get currentViewport;

  /// Override to provide node positions
  Map<String, Offset> get nodePositions;

  /// Override to handle preload notification
  void onPreloadNodes(Set<String> nodeIds);

  void _checkPreload() {
    final viewport = currentViewport;
    if (viewport == null) return;

    final nodeIds = _preloader.getPreloadNodeIds(viewport, nodePositions);
    if (nodeIds.isNotEmpty) {
      onPreloadNodes(nodeIds);
    }
  }

  /// Call when viewport changes
  void onViewportChanged(Offset position, {double? scale}) {
    _preloader.updateViewportPosition(position, scale: scale);
  }
}

/// Viewport preload strategy
enum PreloadStrategy {
  /// No preloading
  none,

  /// Preload based on movement direction only
  directional,

  /// Preload in an expanded area around viewport
  expanded,

  /// Full predictive preloading with velocity and history
  predictive,
}

/// Preload configuration
class PreloadConfig {
  const PreloadConfig({
    this.strategy = PreloadStrategy.predictive,
    this.lookAheadTime = const Duration(milliseconds: 300),
    this.predictionRadius = 200.0,
    this.preloadMargin = 1.5,
    this.maxPreloadNodes = 100,
    this.debounceInterval = const Duration(milliseconds: 50),
  });

  final PreloadStrategy strategy;
  final Duration lookAheadTime;
  final double predictionRadius;
  final double preloadMargin;
  final int maxPreloadNodes;
  final Duration debounceInterval;
}
