import 'dart:async';
import 'dart:collection';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';

@immutable
class RenderConfig {
  const RenderConfig({
    required this.tier,
    required this.enableParticles,
    required this.enableGlow,
    required this.enableBlur,
    required this.enableAntialiasing,
  });

  final PerformanceTier tier;
  final bool enableParticles;
  final bool enableGlow;
  final bool enableBlur;
  final bool enableAntialiasing;
}

@immutable
class BackgroundRenderSettings {
  const BackgroundRenderSettings({
    required this.renderScale,
    required this.renderFps,
    required this.noiseScale,
    required this.fieldStrength,
    required this.maxBursts,
  });

  final double renderScale;
  final int renderFps;
  final double noiseScale;
  final double fieldStrength;
  final int maxBursts;
}

class _FrameSample {
  _FrameSample(this.endTimestamp, this.frameMs);

  final Duration endTimestamp;
  final double frameMs;
}

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

  // --- Monitoring State ---
  // Store frame end timestamps to compute a real-time sliding window.
  final Queue<Duration> _frameTimestamps = Queue();
  final Queue<_FrameSample> _frameSamples = Queue();
  
  DateTime? _lastStateChangeTime;
  bool _monitoring = false;
  Timer? _checkTimer;
  
  // Cache refresh rate
  double _deviceRefreshRate = 60.0;
  int _downgradeStreak = 0;
  int _upgradeStreak = 0;

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

  RenderConfig get renderConfig => RenderConfig(
        tier: currentTier.value,
        enableParticles: enableParticles,
        enableGlow: enableGlow,
        enableBlur: enableBlur,
        enableAntialiasing: enableAntialiasing,
      );

  BackgroundRenderSettings get backgroundRenderSettings {
    switch (currentTier.value) {
      case PerformanceTier.low:
        return const BackgroundRenderSettings(
          renderScale: 0.5,
          renderFps: 20,
          noiseScale: 0.8,
          fieldStrength: 0.6,
          maxBursts: 1,
        );
      case PerformanceTier.medium:
        return const BackgroundRenderSettings(
          renderScale: 0.75,
          renderFps: 30,
          noiseScale: 1.0,
          fieldStrength: 0.8,
          maxBursts: 2,
        );
      case PerformanceTier.high:
        return const BackgroundRenderSettings(
          renderScale: 1.0,
          renderFps: 60,
          noiseScale: 1.2,
          fieldStrength: 1.0,
          maxBursts: 4,
        );
      case PerformanceTier.ultra:
        return const BackgroundRenderSettings(
          renderScale: 1.0,
          renderFps: 60,
          noiseScale: 1.4,
          fieldStrength: 1.2,
          maxBursts: 4,
        );
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
    _frameSamples.clear();
    _downgradeStreak = 0;
    _upgradeStreak = 0;
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
      _frameSamples.add(
        _FrameSample(
          timing.rasterFinish,
          timing.totalSpan.inMicroseconds / 1000.0,
        ),
      );
    }

    // Maintain a real-time window based on timestamps.
    while (_frameTimestamps.length > 1) {
      final window =
          _frameTimestamps.last - _frameTimestamps.first;
      if (window <= _targetWindowDuration) break;
      _frameTimestamps.removeFirst();
    }

    while (_frameSamples.length > 1) {
      final window = _frameSamples.last.endTimestamp -
          _frameSamples.first.endTimestamp;
      if (window <= _targetWindowDuration) break;
      _frameSamples.removeFirst();
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
    final p95FrameMs = _calculateP95FrameMs();

    final now = DateTime.now();
    final timeSinceChange =
        now.difference(_lastStateChangeTime ?? DateTime.fromMillisecondsSinceEpoch(0));

    // --- Determine Target & Thresholds ---
    var downgradeThreshold = 20.0;
    var upgradeThreshold = 58.0; // Default for 60Hz
    var downgradeFrameMs = 40.0;
    var upgradeFrameMs = 20.0;
    
    if (_deviceRefreshRate > 90) {
      // 120Hz Target
      downgradeThreshold = 80.0;
      upgradeThreshold = 115.0;
      final targetMs = 1000 / _deviceRefreshRate;
      downgradeFrameMs = targetMs * 2.5;
      upgradeFrameMs = targetMs * 1.2;
    } else if (_deviceRefreshRate < 45) {
      // 30Hz Target
      downgradeThreshold = 20.0;
      upgradeThreshold = _deviceRefreshRate * 0.93;
      final targetMs = 1000 / _deviceRefreshRate;
      downgradeFrameMs = targetMs * 2.0;
      upgradeFrameMs = targetMs * 1.1;
    } else {
      // 60Hz Target
      downgradeThreshold = 35.0;
      upgradeThreshold = 58.0;
      final targetMs = 1000 / _deviceRefreshRate;
      downgradeFrameMs = targetMs * 2.5;
      upgradeFrameMs = targetMs * 1.2;
    }

    final isBad = fps < downgradeThreshold || p95FrameMs > downgradeFrameMs;
    final isGood = fps > upgradeThreshold && p95FrameMs < upgradeFrameMs;

    if (isBad) {
      _downgradeStreak++;
      _upgradeStreak = 0;
    } else if (isGood) {
      _upgradeStreak++;
      _downgradeStreak = 0;
    } else {
      _downgradeStreak = 0;
      _upgradeStreak = 0;
    }

    // --- Downgrade Logic ---
    if (timeSinceChange > _downgradeCooldown && _downgradeStreak >= 3) {
      _downgradeStreak = 0;
      _performDowngrade();
      return;
    }

    // --- Upgrade Logic ---
    if (timeSinceChange > _upgradeCooldown && _upgradeStreak >= 8) {
      _upgradeStreak = 0;
      _performUpgrade();
      return;
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

  double _calculateP95FrameMs() {
    if (_frameSamples.isEmpty) return 0.0;
    final samples = _frameSamples.map((s) => s.frameMs).toList()..sort();
    final index = (samples.length * 0.95).clamp(0, samples.length - 1).toInt();
    return samples[index];
  }
}
