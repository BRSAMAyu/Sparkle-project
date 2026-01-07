import 'dart:async';
import 'dart:collection';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';

/// Service to manage app performance settings with adaptive degradation
class PerformanceService extends ChangeNotifier {
  PerformanceService._();
  static final PerformanceService instance = PerformanceService._();

  // --- State ---
  final ValueNotifier<PerformanceTier> currentTier =
      ValueNotifier(defaultPerformanceTier());
  final ValueNotifier<double> currentDpr =
      ValueNotifier(window.devicePixelRatio);

  // --- Configuration ---
  static const Duration _targetWindowDuration = Duration(seconds: 1);
  static const Duration _downgradeCooldown = Duration(seconds: 10);
  static const Duration _upgradeCooldown = Duration(seconds: 20);
  static const Duration _sustainedHighPerformanceDuration = Duration(seconds: 5);

  // --- Monitoring State ---
  // Store only durations. We sum them to measure the window.
  final Queue<Duration> _frameDurations = Queue();
  Duration _totalRecordedDuration = Duration.zero;
  
  DateTime? _lastStateChangeTime;
  DateTime? _highPerformanceStartTime;
  bool _monitoring = false;
  Timer? _checkTimer;
  
  // Cache refresh rate
  double _deviceRefreshRate = 60.0;

  // --- Getters for Features based on Tier ---
  bool get enableParticles =>
      currentTier.value == PerformanceTier.ultra ||
      currentTier.value == PerformanceTier.high;
  bool get enableGlow => currentTier.value == PerformanceTier.ultra;
  bool get enableBlur =>
      currentTier.value == PerformanceTier.ultra ||
      currentTier.value == PerformanceTier.high;
  bool get enableAntialiasing => currentTier.value != PerformanceTier.low;

  /// Get the current render configuration
  RenderConfig get renderConfig => RenderConfig.forTier(currentTier.value);

  /// Record a frame time for runtime performance monitoring (Manual)
  /// Kept for compatibility, but prefer automatic monitoring via startMonitoring()
  void recordFrameTime(Duration frameTime) {
    // We can integrate this into the automatic queue if needed,
    // but for now we rely on FrameTiming callback.
    // If automatic monitoring is off, we could use this.
    if (!_monitoring) {
       _frameDurations.add(frameTime);
       _totalRecordedDuration += frameTime;
       // Trigger evaluation if we have enough data
       if (_totalRecordedDuration > _targetWindowDuration) {
         _evaluatePerformance();
         // Cleanup
         while (_frameDurations.isNotEmpty && _totalRecordedDuration > _targetWindowDuration) {
            _totalRecordedDuration -= _frameDurations.removeFirst();
         }
       }
    }
  }
  
  // Focus Mode configuration
  int get focusStarCount {
    switch (currentTier.value) {
      case PerformanceTier.ultra: return 200;
      case PerformanceTier.high: return 120;
      case PerformanceTier.medium: return 60;
      case PerformanceTier.low: return 30;
    }
  }

  bool get enableFocusTwinkle => currentTier.value != PerformanceTier.low;

  // Cognitive Prism configuration
  int get prismParticleCount {
     switch (currentTier.value) {
      case PerformanceTier.ultra: return 30;
      case PerformanceTier.high: return 20;
      case PerformanceTier.medium: return 10;
      case PerformanceTier.low: return 5;
    }
  }

  /// Start monitoring FPS
  void startMonitoring() {
    if (_monitoring) return;
    _monitoring = true;
    _deviceRefreshRate = _getDeviceRefreshRate();
    SchedulerBinding.instance.addTimingsCallback(_onFrameTiming);
    _checkTimer = Timer.periodic(const Duration(seconds: 1), (_) => _evaluatePerformance());
  }

  /// Stop monitoring FPS
  void stopMonitoring() {
    if (!_monitoring) return;
    _monitoring = false;
    SchedulerBinding.instance.removeTimingsCallback(_onFrameTiming);
    _checkTimer?.cancel();
    _frameDurations.clear();
    _totalRecordedDuration = Duration.zero;
  }
  
  double _getDeviceRefreshRate() {
    try {
      if (PlatformDispatcher.instance.views.isNotEmpty) {
        return PlatformDispatcher.instance.views.first.display.refreshRate;
      }
      return 60.0;
    } catch (e) {
      return 60.0; // Fallback
    }
  }

  void _onFrameTiming(List<FrameTiming> timings) {
    for (final timing in timings) {
      _frameDurations.add(timing.totalSpan);
      _totalRecordedDuration += timing.totalSpan;
    }
    
    // Maintain window size approx 1s based on actual frame cost
    while (_frameDurations.isNotEmpty && 
           _totalRecordedDuration > _targetWindowDuration) {
      final removed = _frameDurations.removeFirst();
      _totalRecordedDuration -= removed;
    }
  }

  void _evaluatePerformance() {
    if (_frameDurations.isEmpty) return;
    // Require at least 0.5s of data to judge
    if (_totalRecordedDuration < const Duration(milliseconds: 500)) return;

    // Calculate Average FPS: Frame Count / Total Duration (in seconds)
    final durationSeconds = _totalRecordedDuration.inMicroseconds / 1000000.0;
    if (durationSeconds <= 0) return;
    
    final fps = _frameDurations.length / durationSeconds;

    final now = DateTime.now();
    final timeSinceChange =
        now.difference(_lastStateChangeTime ?? DateTime.fromMillisecondsSinceEpoch(0));

    // --- Determine Target & Thresholds ---
    double downgradeThreshold = 20.0;
    double upgradeThreshold = 58.0; // Default for 60Hz
    
    if (_deviceRefreshRate > 90) {
      // 120Hz Target
      downgradeThreshold = 80.0;
      upgradeThreshold = 115.0;
    } else if (_deviceRefreshRate < 45) {
      // 30Hz Target
      downgradeThreshold = 20.0; 
      upgradeThreshold = 28.0; // Hard to upgrade from 30 if device is locked there
    } else {
      // 60Hz Target
      downgradeThreshold = 35.0;
      upgradeThreshold = 58.0;
    }

    // --- Downgrade Logic ---
    if (timeSinceChange > _downgradeCooldown) {
      if (fps < downgradeThreshold) {
        _performDowngrade();
        return; 
      }
    }

    // --- Upgrade Logic ---
    if (timeSinceChange > _upgradeCooldown) {
       // Only upgrade if we are consistently hitting the target cap
       if (fps > upgradeThreshold) {
         if (_highPerformanceStartTime == null) {
           _highPerformanceStartTime = now;
         } else if (now.difference(_highPerformanceStartTime!) >
             _sustainedHighPerformanceDuration) {
           _performUpgrade();
           _highPerformanceStartTime = null; // Reset
         }
       } else {
         _highPerformanceStartTime = null;
       }
    }
  }

  void _performDowngrade() {
    // 1. DPR Downsampling (Simulated or via Widget Scaling)
    // We allow dropping DPR down to 0.5 * Device Ratio or 1.0 absolute, whichever is higher,
    // to prevent complete blurriness.
    final targetDpr = (currentDpr.value * 0.7).clamp(1.0, window.devicePixelRatio);
    
    if (currentDpr.value > targetDpr + 0.1) { // Floating point tolerance
       currentDpr.value = targetDpr;
       notifyListeners();
    } else {
      // 2. Tier Downgrade
      final next = _getNextLowerTier(currentTier.value);
      if (next != currentTier.value) {
        currentTier.value = next;
        // Keep DPR low to ensure stability
        notifyListeners();
      }
    }
    _lastStateChangeTime = DateTime.now();
  }

  void _performUpgrade() {
    // 1. Tier Upgrade
    final next = _getNextHigherTier(currentTier.value);
    if (next != currentTier.value) {
      currentTier.value = next;
      notifyListeners();
    } else {
      // 2. DPR Restoration
      if (currentDpr.value < window.devicePixelRatio) {
        currentDpr.value = window.devicePixelRatio;
        notifyListeners();
      }
    }
    _lastStateChangeTime = DateTime.now();
  }

  PerformanceTier _getNextLowerTier(PerformanceTier current) {
    switch (current) {
      case PerformanceTier.ultra: return PerformanceTier.high;
      case PerformanceTier.high: return PerformanceTier.medium;
      case PerformanceTier.medium: return PerformanceTier.low;
      case PerformanceTier.low: return PerformanceTier.low;
    }
  }

  PerformanceTier _getNextHigherTier(PerformanceTier current) {
    switch (current) {
      case PerformanceTier.low: return PerformanceTier.medium;
      case PerformanceTier.medium: return PerformanceTier.high;
      case PerformanceTier.high: return PerformanceTier.ultra;
      case PerformanceTier.ultra: return PerformanceTier.ultra;
    }
  }
  
  @override
  void dispose() {
    stopMonitoring();
    super.dispose();
  }
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
      case PerformanceTier.ultra:
        return const RenderConfig(
          tier: PerformanceTier.ultra,
          useShaders: true,
          maxParticles: 300,
          enableGlow: true,
          enableBlur: true,
          targetFps: 120,
          lodThreshold: 0.2,
        );
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