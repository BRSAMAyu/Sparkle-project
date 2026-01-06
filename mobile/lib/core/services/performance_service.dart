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
  // Store frame end timestamps to compute a real-time sliding window.
  final Queue<Duration> _frameTimestamps = Queue();
  
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
  
  // Focus Mode configuration
  int get focusStarCount {
    switch (currentTier.value) {
      case PerformanceTier.ultra: return 200;
      case PerformanceTier.high: return 120;
      case PerformanceTier.medium: return 60;
      case PerformanceTier.low: return 30;
    }
  }

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
    _frameTimestamps.clear();
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
      _frameTimestamps.add(timing.rasterFinish);
    }

    // Maintain a real-time window based on timestamps.
    while (_frameTimestamps.length > 1) {
      final window =
          _frameTimestamps.last - _frameTimestamps.first;
      if (window <= _targetWindowDuration) break;
      _frameTimestamps.removeFirst();
    }
  }

  void _evaluatePerformance() {
    if (_frameTimestamps.length < 2) return;
    final window = _frameTimestamps.last - _frameTimestamps.first;
    // Require at least 0.5s of data to judge
    if (window < const Duration(milliseconds: 500)) return;

    // Calculate FPS based on real-time window.
    final durationSeconds = window.inMicroseconds / 1000000.0;
    if (durationSeconds <= 0) return;

    final fps = (_frameTimestamps.length - 1) / durationSeconds;

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
      upgradeThreshold = _deviceRefreshRate * 0.93;
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
