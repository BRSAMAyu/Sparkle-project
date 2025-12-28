import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

/// Device performance tier for adaptive rendering
enum PerformanceTier {
  /// High-end devices: Full shaders, all effects enabled
  high,

  /// Mid-range devices: Simplified shaders, reduced particle counts
  medium,

  /// Low-end devices: Canvas API fallback, minimal effects
  low,
}

/// Configuration for rendering based on performance tier
class RenderConfig {
  const RenderConfig({
    required this.tier,
    required this.useShaders,
    required this.maxParticles,
    required this.enableGlow,
    required this.enableBlur,
    required this.targetFps,
    required this.lodThreshold,
  });

  factory RenderConfig.forTier(PerformanceTier tier) {
    switch (tier) {
      case PerformanceTier.high:
        return const RenderConfig(
          tier: PerformanceTier.high,
          useShaders: true,
          maxParticles: 200,
          enableGlow: true,
          enableBlur: true,
          targetFps: 60,
          lodThreshold: 0.3,
        );
      case PerformanceTier.medium:
        return const RenderConfig(
          tier: PerformanceTier.medium,
          useShaders: true,
          maxParticles: 80,
          enableGlow: true,
          enableBlur: false,
          targetFps: 45,
          lodThreshold: 0.5,
        );
      case PerformanceTier.low:
        return const RenderConfig(
          tier: PerformanceTier.low,
          useShaders: false,
          maxParticles: 30,
          enableGlow: false,
          enableBlur: false,
          targetFps: 30,
          lodThreshold: 0.7,
        );
    }
  }

  final PerformanceTier tier;
  final bool useShaders;
  final int maxParticles;
  final bool enableGlow;
  final bool enableBlur;
  final int targetFps;
  final double lodThreshold;
}

/// P2: Device performance detection and adaptive rendering service
/// Automatically detects device capability and provides appropriate render config
class DevicePerformanceService {
  DevicePerformanceService._();

  static final DevicePerformanceService instance = DevicePerformanceService._();

  PerformanceTier? _cachedTier;
  RenderConfig? _cachedConfig;
  final List<double> _frameTimeSamples = [];
  static const int _maxSamples = 60;

  /// Get the current render configuration
  RenderConfig get renderConfig {
    _cachedConfig ??= RenderConfig.forTier(performanceTier);
    return _cachedConfig!;
  }

  /// Get the detected performance tier
  PerformanceTier get performanceTier {
    _cachedTier ??= _detectPerformanceTier();
    return _cachedTier!;
  }

  /// Force a specific performance tier (for user settings)
  void setPerformanceTier(PerformanceTier tier) {
    _cachedTier = tier;
    _cachedConfig = RenderConfig.forTier(tier);
  }

  /// Record a frame time for runtime performance monitoring
  void recordFrameTime(Duration frameTime) {
    _frameTimeSamples.add(frameTime.inMicroseconds / 1000.0);
    if (_frameTimeSamples.length > _maxSamples) {
      _frameTimeSamples.removeAt(0);
    }

    // Auto-downgrade if consistently dropping frames
    if (_frameTimeSamples.length >= _maxSamples) {
      final avgFrameTime =
          _frameTimeSamples.reduce((a, b) => a + b) / _frameTimeSamples.length;
      if (avgFrameTime > 25 && _cachedTier == PerformanceTier.high) {
        // Downgrade from high to medium
        setPerformanceTier(PerformanceTier.medium);
        debugPrint(
          '[DevicePerformance] Auto-downgraded to MEDIUM (avg frame: ${avgFrameTime.toStringAsFixed(1)}ms)',
        );
      } else if (avgFrameTime > 40 && _cachedTier == PerformanceTier.medium) {
        // Downgrade from medium to low
        setPerformanceTier(PerformanceTier.low);
        debugPrint(
          '[DevicePerformance] Auto-downgraded to LOW (avg frame: ${avgFrameTime.toStringAsFixed(1)}ms)',
        );
      }
    }
  }

  /// Detect device performance tier based on device characteristics
  PerformanceTier _detectPerformanceTier() {
    // Web always uses medium for compatibility
    if (kIsWeb) {
      return PerformanceTier.medium;
    }

    // Check physical device characteristics
    final devicePixelRatio = ui.PlatformDispatcher.instance.views.first.devicePixelRatio;
    final physicalSize = ui.PlatformDispatcher.instance.views.first.physicalSize;
    final totalPixels = physicalSize.width * physicalSize.height;

    // iOS devices are generally well-optimized
    if (Platform.isIOS) {
      // iPhone 12 and later have good GPU
      if (totalPixels > 2000000 && devicePixelRatio >= 3.0) {
        return PerformanceTier.high;
      }
      return PerformanceTier.medium;
    }

    // Android device detection
    if (Platform.isAndroid) {
      // High-end: High resolution + High DPI (flagship devices)
      if (totalPixels > 3000000 && devicePixelRatio >= 3.0) {
        return PerformanceTier.high;
      }
      // Medium: Standard resolution
      if (totalPixels > 1500000 && devicePixelRatio >= 2.0) {
        return PerformanceTier.medium;
      }
      // Low-end: Everything else
      return PerformanceTier.low;
    }

    // Desktop platforms default to high
    if (Platform.isMacOS || Platform.isWindows || Platform.isLinux) {
      return PerformanceTier.high;
    }

    // Default fallback
    return PerformanceTier.medium;
  }

  /// Check if shaders are supported and should be used
  bool get shouldUseShaders => renderConfig.useShaders;

  /// Get maximum particle count for current tier
  int get maxParticles => renderConfig.maxParticles;

  /// Check if glow effects should be enabled
  bool get enableGlow => renderConfig.enableGlow;

  /// Check if blur effects should be enabled
  bool get enableBlur => renderConfig.enableBlur;

  /// Get LOD threshold for current tier (higher = more aggressive culling)
  double get lodThreshold => renderConfig.lodThreshold;
}

/// Mixin for widgets that need performance-aware rendering
mixin PerformanceAwareStateMixin<T extends StatefulWidget> on State<T> {
  late final RenderConfig renderConfig;
  Ticker? _performanceTicker;
  DateTime? _lastFrameTime;

  @override
  void initState() {
    super.initState();
    renderConfig = DevicePerformanceService.instance.renderConfig;

    // Setup frame time monitoring in debug mode
    if (kDebugMode) {
      _performanceTicker = Ticker(_onTick);
      _performanceTicker?.start();
    }
  }

  void _onTick(Duration elapsed) {
    final now = DateTime.now();
    if (_lastFrameTime != null) {
      final frameTime = now.difference(_lastFrameTime!);
      DevicePerformanceService.instance.recordFrameTime(frameTime);
    }
    _lastFrameTime = now;
  }

  @override
  void dispose() {
    _performanceTicker?.dispose();
    super.dispose();
  }
}
