import 'dart:async';
import 'dart:collection';

import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';

/// Galaxy性能监控服务
///
/// 功能:
/// 1. 帧率监控
/// 2. 内存使用跟踪
/// 3. 渲染性能指标
/// 4. 自动问题检测
class GalaxyPerformanceMonitor {
  GalaxyPerformanceMonitor._();

  static final GalaxyPerformanceMonitor instance = GalaxyPerformanceMonitor._();

  bool _isMonitoring = false;
  Timer? _reportTimer;

  // 帧率数据
  final Queue<FrameTimingData> _frameTimings = Queue();
  static const int _maxFrameTimings = 120; // 保留2秒的数据

  // 性能指标
  final Map<String, PerformanceMetric> _metrics = {};

  // 渲染计数
  int _renderCount = 0;
  int _repaintCount = 0;
  DateTime? _lastRenderTime;

  // 事件监听
  final List<void Function(PerformanceEvent)> _eventListeners = [];

  // 阈值配置
  final PerformanceThresholds thresholds = const PerformanceThresholds();

  /// 是否正在监控
  bool get isMonitoring => _isMonitoring;

  /// 开始监控
  void startMonitoring({
    Duration reportInterval = const Duration(seconds: 5),
  }) {
    if (_isMonitoring) return;

    _isMonitoring = true;
    _setupFrameCallback();

    // 定期报告
    _reportTimer = Timer.periodic(reportInterval, (_) {
      _generateReport();
    });

    debugPrint('GalaxyPerformanceMonitor: Started monitoring');
  }

  /// 停止监控
  void stopMonitoring() {
    _isMonitoring = false;
    _reportTimer?.cancel();
    _reportTimer = null;
    _frameTimings.clear();

    debugPrint('GalaxyPerformanceMonitor: Stopped monitoring');
  }

  void _setupFrameCallback() {
    SchedulerBinding.instance.addPostFrameCallback(_onFrame);
  }

  void _onFrame(Duration timestamp) {
    if (!_isMonitoring) return;

    final now = DateTime.now();
    final frameDuration = _lastRenderTime != null
        ? now.difference(_lastRenderTime!)
        : Duration.zero;

    _frameTimings.add(
      FrameTimingData(
        timestamp: now,
        duration: frameDuration,
        renderCount: _renderCount,
        repaintCount: _repaintCount,
      ),
    );

    // 保持队列大小
    while (_frameTimings.length > _maxFrameTimings) {
      _frameTimings.removeFirst();
    }

    _lastRenderTime = now;
    _renderCount = 0;
    _repaintCount = 0;

    // 检测性能问题
    _checkPerformanceIssues(frameDuration);

    // 继续监听
    SchedulerBinding.instance.addPostFrameCallback(_onFrame);
  }

  /// 记录渲染
  void recordRender() {
    _renderCount++;
  }

  /// 记录重绘
  void recordRepaint() {
    _repaintCount++;
  }

  /// 记录自定义指标
  void recordMetric(String name, double value, {String unit = ''}) {
    _metrics.putIfAbsent(name, () => PerformanceMetric(name: name, unit: unit));
    _metrics[name]!.addValue(value);
  }

  /// 开始计时
  Stopwatch startTiming(String name) {
    final stopwatch = Stopwatch()..start();
    return stopwatch;
  }

  /// 结束计时并记录
  void endTiming(String name, Stopwatch stopwatch) {
    stopwatch.stop();
    recordMetric(name, stopwatch.elapsedMicroseconds / 1000, unit: 'ms');
  }

  /// 检测性能问题
  void _checkPerformanceIssues(Duration frameDuration) {
    // 检测帧率下降
    if (frameDuration.inMilliseconds > thresholds.maxFrameDurationMs) {
      _emitEvent(
        PerformanceEvent(
          type: PerformanceEventType.frameDrop,
          message:
              'Frame took ${frameDuration.inMilliseconds}ms (>${thresholds.maxFrameDurationMs}ms)',
          severity: PerformanceSeverity.warning,
        ),
      );
    }

    // 检测连续卡顿
    if (_frameTimings.length >= 3) {
      final recentFrames = _frameTimings.toList().reversed.take(3);
      final allSlow = recentFrames.every(
        (f) => f.duration.inMilliseconds > thresholds.maxFrameDurationMs,
      );

      if (allSlow) {
        _emitEvent(
          const PerformanceEvent(
            type: PerformanceEventType.jank,
            message: 'Detected jank: 3+ consecutive slow frames',
            severity: PerformanceSeverity.error,
          ),
        );
      }
    }
  }

  void _emitEvent(PerformanceEvent event) {
    debugPrint(
        'GalaxyPerformanceMonitor: ${event.severity.name} - ${event.message}',);
    for (final listener in _eventListeners) {
      listener(event);
    }
  }

  /// 添加事件监听
  void addEventListener(void Function(PerformanceEvent) listener) {
    _eventListeners.add(listener);
  }

  /// 移除事件监听
  void removeEventListener(void Function(PerformanceEvent) listener) {
    _eventListeners.remove(listener);
  }

  /// 生成性能报告
  void _generateReport() {
    final report = getPerformanceReport();
    debugPrint('GalaxyPerformanceMonitor Report:');
    debugPrint('  FPS: ${report.averageFps.toStringAsFixed(1)}');
    debugPrint(
        '  Frame Time: ${report.averageFrameTimeMs.toStringAsFixed(2)}ms',);
    debugPrint('  Jank Rate: ${(report.jankRate * 100).toStringAsFixed(1)}%');

    for (final metric in report.metrics.values) {
      debugPrint(
          '  ${metric.name}: ${metric.average.toStringAsFixed(2)}${metric.unit}',);
    }
  }

  /// 获取性能报告
  PerformanceReport getPerformanceReport() {
    final frames = _frameTimings.toList();

    double avgFrameTime = 0;
    var jankCount = 0;

    if (frames.isNotEmpty) {
      var totalTime = 0.0;
      for (final frame in frames) {
        totalTime += frame.duration.inMicroseconds / 1000;
        if (frame.duration.inMilliseconds > thresholds.maxFrameDurationMs) {
          jankCount++;
        }
      }
      avgFrameTime = totalTime / frames.length;
    }

    final avgFps = avgFrameTime > 0 ? 1000 / avgFrameTime : 0.0;
    final jankRate = frames.isNotEmpty ? jankCount / frames.length : 0.0;

    return PerformanceReport(
      averageFps: avgFps,
      averageFrameTimeMs: avgFrameTime,
      jankRate: jankRate,
      frameCount: frames.length,
      metrics: Map.from(_metrics),
    );
  }

  /// 重置所有指标
  void reset() {
    _frameTimings.clear();
    _metrics.clear();
    _renderCount = 0;
    _repaintCount = 0;
    _lastRenderTime = null;
  }
}

/// 帧时间数据
class FrameTimingData {
  const FrameTimingData({
    required this.timestamp,
    required this.duration,
    required this.renderCount,
    required this.repaintCount,
  });

  final DateTime timestamp;
  final Duration duration;
  final int renderCount;
  final int repaintCount;
}

/// 性能指标
class PerformanceMetric {
  PerformanceMetric({
    required this.name,
    this.unit = '',
    this.maxSamples = 100,
  });

  final String name;
  final String unit;
  final int maxSamples;

  final Queue<double> _values = Queue();

  void addValue(double value) {
    _values.add(value);
    while (_values.length > maxSamples) {
      _values.removeFirst();
    }
  }

  double get average {
    if (_values.isEmpty) return 0;
    return _values.reduce((a, b) => a + b) / _values.length;
  }

  double get min =>
      _values.isEmpty ? 0 : _values.reduce((a, b) => a < b ? a : b);
  double get max =>
      _values.isEmpty ? 0 : _values.reduce((a, b) => a > b ? a : b);
  int get count => _values.length;
}

/// 性能报告
class PerformanceReport {
  const PerformanceReport({
    required this.averageFps,
    required this.averageFrameTimeMs,
    required this.jankRate,
    required this.frameCount,
    required this.metrics,
  });

  final double averageFps;
  final double averageFrameTimeMs;
  final double jankRate;
  final int frameCount;
  final Map<String, PerformanceMetric> metrics;

  bool get isHealthy => averageFps >= 55 && jankRate < 0.05;

  @override
  String toString() => 'PerformanceReport('
      'fps: ${averageFps.toStringAsFixed(1)}, '
      'frameTime: ${averageFrameTimeMs.toStringAsFixed(2)}ms, '
      'jankRate: ${(jankRate * 100).toStringAsFixed(1)}%)';
}

/// 性能事件
class PerformanceEvent {
  const PerformanceEvent({
    required this.type,
    required this.message,
    required this.severity,
  });

  final PerformanceEventType type;
  final String message;
  final PerformanceSeverity severity;
}

enum PerformanceEventType {
  frameDrop,
  jank,
  memoryWarning,
  layoutSlow,
  renderSlow,
}

enum PerformanceSeverity {
  info,
  warning,
  error,
}

/// 性能阈值配置
class PerformanceThresholds {
  const PerformanceThresholds({
    this.maxFrameDurationMs = 16,
    this.targetFps = 60,
    this.maxMemoryMb = 100,
    this.maxLayoutTimeMs = 5,
    this.maxRenderTimeMs = 10,
  });

  final int maxFrameDurationMs;
  final int targetFps;
  final int maxMemoryMb;
  final int maxLayoutTimeMs;
  final int maxRenderTimeMs;
}

/// 性能监控Mixin - 用于Widget
mixin PerformanceMonitorMixin {
  Stopwatch? _layoutStopwatch;
  Stopwatch? _renderStopwatch;

  void startLayoutTiming() {
    _layoutStopwatch = GalaxyPerformanceMonitor.instance.startTiming('layout');
  }

  void endLayoutTiming() {
    if (_layoutStopwatch != null) {
      GalaxyPerformanceMonitor.instance.endTiming('layout', _layoutStopwatch!);
      _layoutStopwatch = null;
    }
  }

  void startRenderTiming() {
    _renderStopwatch = GalaxyPerformanceMonitor.instance.startTiming('render');
    GalaxyPerformanceMonitor.instance.recordRender();
  }

  void endRenderTiming() {
    if (_renderStopwatch != null) {
      GalaxyPerformanceMonitor.instance.endTiming('render', _renderStopwatch!);
      _renderStopwatch = null;
    }
  }

  void recordRepaint() {
    GalaxyPerformanceMonitor.instance.recordRepaint();
  }
}

/// Galaxy性能指标数据
class GalaxyPerformanceMetrics {
  const GalaxyPerformanceMetrics({
    required this.averageFps,
    required this.minFps,
    required this.maxFps,
    required this.averageFrameTime,
    required this.jankFrameCount,
    required this.frameCount,
  });

  final double averageFps;
  final double minFps;
  final double maxFps;
  final double averageFrameTime;
  final int jankFrameCount;
  final int frameCount;

  @override
  String toString() => 'GalaxyPerformanceMetrics('
      'avgFps: ${averageFps.toStringAsFixed(1)}, '
      'frameTime: ${averageFrameTime.toStringAsFixed(2)}ms, '
      'jank: $jankFrameCount/$frameCount)';
}
