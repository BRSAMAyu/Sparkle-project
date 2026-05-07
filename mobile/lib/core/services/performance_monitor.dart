/// Performance Monitoring Service with Sentry Integration
///
/// 功能：
/// 1. 应用性能指标监控 (FPS, 内存, 启动时间)
/// 2. 用户交互性能跟踪 (页面加载, 操作响应)
/// 3. 离线同步状态监控
/// 4. 崩溃和错误报告
/// 5. 性能数据聚合和分析
library;

// ignore_for_file: cascade_invocations, discarded_futures, unawaited_futures, unused_field, prefer_expression_function_bodies

import 'dart:async';
import 'dart:developer' as developer;
import 'dart:isolate';
import 'dart:ui' show FrameTiming;

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:sparkle/core/services/client_observability_service.dart';

/// 忽略Future结果的扩展方法
extension FutureIgnore<T> on Future<T> {
  void ignore() {
    // 忽略Future结果
  }
}

class PerformanceMonitor {
  factory PerformanceMonitor() => _instance;
  PerformanceMonitor._internal();
  static final PerformanceMonitor _instance = PerformanceMonitor._internal();

  // 监控状态
  bool _isMonitoring = false;
  Timer? _metricsTimer;
  final List<PerformanceMetric> _metricsBuffer = [];

  // 性能指标
  double _currentFPS = 60.0;
  int _memoryUsageMB = 0;
  DateTime? _appStartTime;
  DateTime? _currentScreenStartTime;

  // 用户交互跟踪
  final Map<String, InteractionRecord> _interactionRecords = {};

  /// 初始化性能监控
  Future<void> initialize({
    required String sentryDsn,
    required String environment,
    required double tracesSampleRate,
    required bool enablePerformanceMonitoring,
    required bool enableCrashReporting,
    String? release,
    bool enableNetworkMonitoring = true,
  }) async {
    if (_isMonitoring) return;

    final normalizedDsn = sentryDsn.trim();
    if (normalizedDsn.isEmpty || !enableCrashReporting) {
      _startMonitoring();
      _isMonitoring = true;
      developer.log(
        'Sentry DSN not configured; local performance monitoring only',
        name: 'PerformanceMonitor',
      );
      return;
    }

    try {
      // 初始化Sentry
      await SentryFlutter.init(
        (options) {
          options.dsn = normalizedDsn;
          options.environment = environment;
          if (release != null && release.trim().isNotEmpty) {
            options.release = release.trim();
          }
          options.tracesSampleRate =
              enablePerformanceMonitoring ? tracesSampleRate : 0.0;
          options.enableAppLifecycleBreadcrumbs = true;
          options.attachScreenshot = true;
          options.sendDefaultPii = false; // 保护用户隐私
          options.debug = kDebugMode;

          // 配置性能监控
          if (enablePerformanceMonitoring) {
            options.enableAutoPerformanceTracing = true;
            // enableOutOfMemoryTracking 在新版本中可能已移除或改名
            // 检查Sentry文档获取最新配置
          }
        },
        appRunner: () {
          _startMonitoring();
        },
      );

      _isMonitoring = true;
      developer.log('性能监控服务已初始化', name: 'PerformanceMonitor');
    } catch (e) {
      developer.log('性能监控初始化失败: $e', name: 'PerformanceMonitor');
    }
  }

  /// 开始监控
  void _startMonitoring() {
    _appStartTime = DateTime.now();

    // 启动定期指标收集
    _metricsTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      // 忽略Future结果，避免警告
      _collectMetrics().ignore();
    });

    // 监听应用生命周期
    WidgetsBinding.instance.addObserver(_LifecycleObserver(this));

    developer.log('性能监控已启动', name: 'PerformanceMonitor');

    // 注册帧回调以获取真实FPS
    WidgetsBinding.instance.addTimingsCallback(_onFrameTimings);
  }

  /// 帧回调，计算真实FPS
  void _onFrameTimings(List<FrameTiming> timings) {
    if (timings.isEmpty) return;
    final avgFrameMicros =
        timings.map((t) => t.totalSpan.inMicroseconds).reduce((a, b) => a + b) /
            timings.length;
    if (avgFrameMicros > 0) {
      _currentFPS = 1000000 / avgFrameMicros;
    }
  }

  /// 收集性能指标
  Future<void> _collectMetrics() async {
    try {
      // 收集FPS (基于FrameTiming回调, 如果不可用则标记-1)
      // 真实FPS通过addTimingsCallback计算, 此处仅记录上次计算值
      // _currentFPS 由 _onFrameTimings 回调更新

      // 收集内存使用 (dart:developer API)
      _memoryUsageMB = _estimateMemoryUsage();

      // 记录指标
      final metric = PerformanceMetric(
        timestamp: DateTime.now(),
        fps: _currentFPS,
        memoryMB: _memoryUsageMB,
        platform: defaultTargetPlatform.toString(),
        connectivity: await _getConnectivityStatus(),
      );

      _metricsBuffer.add(metric);

      // 缓冲满时发送到Sentry
      if (_metricsBuffer.length >= 10) {
        _sendMetricsToSentry();
      }

      // 检查性能异常
      _checkPerformanceAnomalies(metric);
    } catch (e) {
      developer.log('收集性能指标失败: $e', name: 'PerformanceMonitor');
    }
  }

  /// 跟踪页面加载时间
  void trackPageLoad(String pageName) {
    final now = DateTime.now();
    final record = InteractionRecord(
      type: 'page_load',
      name: pageName,
      startTime: now,
      endTime: now,
      duration: Duration.zero,
    );

    _interactionRecords[pageName] = record;
    _currentScreenStartTime = now;

    // 发送页面加载事件到Sentry
    Sentry.addBreadcrumb(
      Breadcrumb(
        message: '页面加载: $pageName',
        category: 'navigation',
        level: SentryLevel.info,
        timestamp: now,
      ),
    );
    ClientObservabilityService.instance.trackScreenView(pageName).ignore();
  }

  /// 跟踪用户操作
  void trackUserInteraction(String interactionName, {String? details}) {
    final now = DateTime.now();
    final key = '$interactionName-${now.millisecondsSinceEpoch}';

    final record = InteractionRecord(
      type: 'user_interaction',
      name: interactionName,
      startTime: now,
      details: details,
    );

    _interactionRecords[key] = record;
    ClientObservabilityService.instance.trackInteraction(
      interactionName,
      status: 'started',
      metadata: <String, dynamic>{'details': details},
    ).ignore();

    // 设置定时器检查操作完成
    Timer(const Duration(seconds: 5), () {
      final completedRecord = _interactionRecords[key];
      if (completedRecord != null && completedRecord.endTime == null) {
        // 操作超时
        completedRecord.endTime = DateTime.now();
        completedRecord.duration =
            completedRecord.endTime!.difference(completedRecord.startTime);

        _reportSlowInteraction(completedRecord);
      }
    });
  }

  /// 标记操作完成
  void markInteractionComplete(String interactionName) {
    final now = DateTime.now();
    final keys = _interactionRecords.keys
        .where(
          (key) => key.startsWith('$interactionName-'),
        )
        .toList();

    for (final key in keys) {
      final record = _interactionRecords[key];
      if (record != null && record.endTime == null) {
        record.endTime = now;
        record.duration = record.endTime!.difference(record.startTime);

        // 记录慢操作
        if (record.duration!.inMilliseconds > 1000) {
          _reportSlowInteraction(record);
        }
        ClientObservabilityService.instance.trackInteraction(
          interactionName,
          status: 'completed',
          durationMs: record.duration!.inMilliseconds,
          metadata: <String, dynamic>{'details': record.details},
        ).ignore();
      }
    }
  }

  /// 跟踪离线同步状态
  void trackOfflineSync({
    required String syncType,
    required int itemCount,
    required bool success,
    String? error,
    int? durationMs,
  }) {
    final breadcrumb = Breadcrumb(
      message: '离线同步: $syncType (${success ? '成功' : '失败'})',
      category: 'offline_sync',
      level: success ? SentryLevel.info : SentryLevel.error,
      data: {
        'item_count': itemCount,
        'duration_ms': durationMs,
        'error': error,
      },
      timestamp: DateTime.now(),
    );

    Sentry.addBreadcrumb(breadcrumb);

    // 记录同步指标
    final transaction = Sentry.startTransaction(
      'offline_sync.$syncType',
      'offline_sync',
      bindToScope: true,
    );

    final span = transaction.startChild(
      'sync_operation',
      description: '同步$itemCount个项目',
    );

    if (!success && error != null) {
      span.status = const SpanStatus.internalError();
      Sentry.captureException(
        Exception('离线同步失败: $error'),
        stackTrace: StackTrace.current,
      );
    }

    span.finish();
    transaction.finish();
    ClientObservabilityService.instance.recordEvent(
      eventType: 'offline_sync',
      category: 'sync',
      status: success ? 'ok' : 'error',
      severity: success ? 'info' : 'warning',
      durationMs: durationMs,
      metadata: <String, dynamic>{
        'sync_type': syncType,
        'item_count': itemCount,
        'error': error,
      },
    ).ignore();
  }

  /// 报告应用崩溃
  void reportCrash(dynamic error, StackTrace stackTrace, {String? context}) {
    final crashObject = error is Object
        ? error
        : Exception(error?.toString() ?? 'Unknown crash');
    Sentry.captureException(
      crashObject,
      stackTrace: stackTrace,
      hint: Hint.withMap({
        'context': context ?? '未指定上下文',
        'app_state': {
          'fps': _currentFPS,
          'memory_mb': _memoryUsageMB,
          'monitoring': _isMonitoring,
        },
      }),
    );
    ClientObservabilityService.instance
        .trackCrash(crashObject, stackTrace, context: context)
        .ignore();
  }

  /// 报告性能异常
  void _reportSlowInteraction(InteractionRecord record) {
    Sentry.addBreadcrumb(
      Breadcrumb(
        message: '慢操作: ${record.name} (${record.duration!.inMilliseconds}ms)',
        category: 'performance',
        level: SentryLevel.warning,
        data: record.toMap(),
        timestamp: DateTime.now(),
      ),
    );
  }

  /// 检查性能异常
  void _checkPerformanceAnomalies(PerformanceMetric metric) {
    // FPS过低警告 (仅当有真实数据时)
    if (metric.fps > 0 && metric.fps < 30) {
      Sentry.addBreadcrumb(
        Breadcrumb(
          message: '低FPS警告: ${metric.fps}fps',
          category: 'performance',
          level: SentryLevel.warning,
          data: metric.toMap(),
          timestamp: DateTime.now(),
        ),
      );
      ClientObservabilityService.instance.recordEvent(
        eventType: 'performance_warning',
        category: 'performance',
        status: 'warning',
        severity: 'warning',
        metadata: <String, dynamic>{
          'warning_type': 'low_fps',
          'fps': metric.fps,
        },
      ).ignore();
    }

    // 内存使用过高警告
    if (metric.memoryMB > 500) {
      // 500MB阈值
      Sentry.addBreadcrumb(
        Breadcrumb(
          message: '高内存使用: ${metric.memoryMB}MB',
          category: 'performance',
          level: SentryLevel.warning,
          data: metric.toMap(),
          timestamp: DateTime.now(),
        ),
      );
      ClientObservabilityService.instance.recordEvent(
        eventType: 'performance_warning',
        category: 'performance',
        status: 'warning',
        severity: 'warning',
        metadata: <String, dynamic>{
          'warning_type': 'high_memory',
          'memory_mb': metric.memoryMB,
        },
      ).ignore();
    }
  }

  /// 发送指标到Sentry
  Future<void> _sendMetricsToSentry() async {
    if (_metricsBuffer.isEmpty) return;

    try {
      // 创建性能事务
      final transaction = Sentry.startTransaction(
        'performance_metrics',
        'metrics_collection',
        bindToScope: true,
      );

      for (final metric in _metricsBuffer) {
        final span = transaction.startChild(
          'metric_sample',
          description: 'FPS: ${metric.fps}, Memory: ${metric.memoryMB}MB',
        );

        // 添加指标数据
        span.setData('fps', metric.fps);
        span.setData('memory_mb', metric.memoryMB);
        span.setData('connectivity', metric.connectivity);
        span.setData('platform', metric.platform);

        span.finish();
      }

      transaction.finish();
      _metricsBuffer.clear();
    } catch (e) {
      developer.log('发送性能指标失败: $e', name: 'PerformanceMonitor');
    }
  }

  /// 估算内存使用 (通过dart:developer API)
  int _estimateMemoryUsage() {
    try {
      final info = developer.Service.getIsolateID(Isolate.current);
      // dart:developer 不直接暴露 heap size, 返回 -1 表示不可用
      // 真实内存需通过 platform channel 获取
      return -1;
    } catch (_) {
      return -1;
    }
  }

  /// 获取网络连接状态
  Future<String> _getConnectivityStatus() async {
    try {
      final connectivityResult = await Connectivity().checkConnectivity();
      return connectivityResult.toString().split('.').last;
    } catch (e) {
      return 'unknown';
    }
  }

  /// 停止监控
  void stopMonitoring() {
    _metricsTimer?.cancel();
    _metricsTimer = null;
    _isMonitoring = false;

    // 发送剩余指标
    if (_metricsBuffer.isNotEmpty) {
      _sendMetricsToSentry();
    }

    developer.log('性能监控已停止', name: 'PerformanceMonitor');
  }

  /// 获取当前性能状态
  Map<String, dynamic> getPerformanceStatus() => {
        'is_monitoring': _isMonitoring,
        'current_fps': _currentFPS,
        'memory_usage_mb': _memoryUsageMB,
        'app_uptime': _appStartTime != null
            ? DateTime.now().difference(_appStartTime!).inSeconds
            : 0,
        'metrics_buffer_size': _metricsBuffer.length,
        'interaction_records': _interactionRecords.length,
      };
}

/// 性能指标数据类
class PerformanceMetric {
  PerformanceMetric({
    required this.timestamp,
    required this.fps,
    required this.memoryMB,
    required this.platform,
    required this.connectivity,
  });
  final DateTime timestamp;
  final double fps;
  final int memoryMB;
  final String platform;
  final String connectivity;

  Map<String, dynamic> toMap() => {
        'timestamp': timestamp.toIso8601String(),
        'fps': fps,
        'memory_mb': memoryMB,
        'platform': platform,
        'connectivity': connectivity,
      };
}

/// 用户交互记录
class InteractionRecord {
  InteractionRecord({
    required this.type,
    required this.name,
    required this.startTime,
    this.endTime,
    this.duration,
    this.details,
  });
  final String type;
  final String name;
  final DateTime startTime;
  DateTime? endTime;
  Duration? duration;
  final String? details;

  Map<String, dynamic> toMap() => {
        'type': type,
        'name': name,
        'start_time': startTime.toIso8601String(),
        'end_time': endTime?.toIso8601String(),
        'duration_ms': duration?.inMilliseconds,
        'details': details,
      };
}

/// 应用生命周期观察者
class _LifecycleObserver extends WidgetsBindingObserver {
  _LifecycleObserver(this._monitor);
  final PerformanceMonitor _monitor;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final breadcrumb = Breadcrumb(
      message: '应用生命周期变化: $state',
      category: 'app_lifecycle',
      level: SentryLevel.info,
      timestamp: DateTime.now(),
    );

    Sentry.addBreadcrumb(breadcrumb);

    switch (state) {
      case AppLifecycleState.resumed:
        _monitor.trackPageLoad('app_resumed');
      case AppLifecycleState.inactive:
      case AppLifecycleState.paused:
      case AppLifecycleState.detached:
      case AppLifecycleState.hidden:
        break;
    }
  }
}
