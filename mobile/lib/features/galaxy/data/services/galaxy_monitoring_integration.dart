import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/galaxy/data/services/galaxy_performance_monitor.dart';

/// Galaxy监控集成服务
/// 将性能监控与Galaxy Provider集成，提供实时性能反馈
class GalaxyMonitoringIntegration {
  GalaxyMonitoringIntegration({
    required this.ref,
    this.enableAdaptiveQuality = true,
    this.performanceThresholds = const PerformanceThresholds(),
  }) {
    _initialize();
  }

  final Ref ref;
  final bool enableAdaptiveQuality;
  final PerformanceThresholds performanceThresholds;

  late final GalaxyPerformanceMonitor _performanceMonitor;
  Timer? _qualityAdjustmentTimer;

  /// 当前渲染质量级别 (0.0 - 1.0)
  double _currentQuality = 1.0;
  double get currentQuality => _currentQuality;

  /// 性能状态
  PerformanceStatus _performanceStatus = PerformanceStatus.optimal;
  PerformanceStatus get performanceStatus => _performanceStatus;

  /// 性能警告回调
  final _warningController = StreamController<PerformanceWarning>.broadcast();
  Stream<PerformanceWarning> get warnings => _warningController.stream;

  void _initialize() {
    _performanceMonitor = GalaxyPerformanceMonitor.instance;

    // 开始监控
    _performanceMonitor.startMonitoring();

    // 添加事件监听
    _performanceMonitor.addEventListener(_handlePerformanceEvent);

    // 定期调整质量
    if (enableAdaptiveQuality) {
      _qualityAdjustmentTimer = Timer.periodic(
        const Duration(seconds: 2),
        (_) => _adjustQuality(),
      );
    }
  }

  void _handlePerformanceEvent(PerformanceEvent event) {
    // 基于事件更新性能状态
    if (event.severity == PerformanceSeverity.error) {
      _performanceStatus = PerformanceStatus.critical;
      _warningController.add(
        PerformanceWarning(
          type: WarningType.jank,
          message: event.message,
          severity: WarningSeverity.critical,
        ),
      );
    } else if (event.severity == PerformanceSeverity.warning) {
      _performanceStatus = PerformanceStatus.degraded;
      _warningController.add(
        PerformanceWarning(
          type: WarningType.slowRender,
          message: event.message,
          severity: WarningSeverity.warning,
        ),
      );
    }
  }

  PerformanceStatus _evaluatePerformance() {
    final report = _performanceMonitor.getPerformanceReport();

    if (report.averageFps < performanceThresholds.criticalFps) {
      return PerformanceStatus.critical;
    } else if (report.averageFps < performanceThresholds.warningFps) {
      return PerformanceStatus.degraded;
    } else if (report.jankRate > 0.1) {
      return PerformanceStatus.degraded;
    }
    return PerformanceStatus.optimal;
  }

  void _checkForWarnings(PerformanceReport report) {
    // FPS过低警告
    if (report.averageFps < performanceThresholds.criticalFps) {
      _warningController.add(
        PerformanceWarning(
          type: WarningType.lowFps,
          message: 'FPS严重不足: ${report.averageFps.toStringAsFixed(1)}',
          severity: WarningSeverity.critical,
          report: report,
        ),
      );
    } else if (report.averageFps < performanceThresholds.warningFps) {
      _warningController.add(
        PerformanceWarning(
          type: WarningType.lowFps,
          message: 'FPS偏低: ${report.averageFps.toStringAsFixed(1)}',
          severity: WarningSeverity.warning,
          report: report,
        ),
      );
    }

    // Jank警告
    if (report.jankRate > 0.1) {
      _warningController.add(
        PerformanceWarning(
          type: WarningType.jank,
          message: '卡顿率过高: ${(report.jankRate * 100).toStringAsFixed(1)}%',
          severity: WarningSeverity.warning,
          report: report,
        ),
      );
    }

    // 渲染时间警告
    if (report.averageFrameTimeMs > 32) {
      // 超过32ms表示可能严重
      _warningController.add(
        PerformanceWarning(
          type: WarningType.slowRender,
          message: '渲染时间过长: ${report.averageFrameTimeMs.toStringAsFixed(1)}ms',
          severity: report.averageFrameTimeMs > 50
              ? WarningSeverity.critical
              : WarningSeverity.warning,
          report: report,
        ),
      );
    }
  }

  void _adjustQuality() {
    if (!enableAdaptiveQuality) return;

    // 获取最新性能报告
    final report = _performanceMonitor.getPerformanceReport();
    if (report.frameCount == 0) return;

    // 评估当前性能状态
    _performanceStatus = _evaluatePerformance();

    // 检查警告
    _checkForWarnings(report);

    var targetQuality = _currentQuality;

    switch (_performanceStatus) {
      case PerformanceStatus.optimal:
        // 逐步提升质量
        targetQuality = (_currentQuality + 0.1).clamp(0.0, 1.0);

      case PerformanceStatus.degraded:
        // 保持或轻微降低
        targetQuality = (_currentQuality - 0.05).clamp(0.3, 1.0);

      case PerformanceStatus.critical:
        // 快速降低质量
        targetQuality = (_currentQuality - 0.2).clamp(0.2, 1.0);
    }

    if ((targetQuality - _currentQuality).abs() > 0.01) {
      _currentQuality = targetQuality;
      _onQualityChanged();
    }
  }

  void _onQualityChanged() {
    // 质量变化时的回调
    debugPrint(
        'Galaxy quality adjusted to: ${(_currentQuality * 100).toStringAsFixed(0)}%',);
  }

  /// 获取当前性能摘要
  PerformanceSummary getSummary() {
    final report = _performanceMonitor.getPerformanceReport();

    // 重新评估性能状态
    _performanceStatus = _evaluatePerformance();

    return PerformanceSummary(
      status: _performanceStatus,
      quality: _currentQuality,
      report: report,
      recommendations: _generateRecommendations(report),
    );
  }

  List<String> _generateRecommendations(PerformanceReport report) {
    final recommendations = <String>[];

    if (report.averageFps < 30) {
      recommendations.add('建议减少可见节点数量');
      recommendations.add('考虑禁用粒子效果');
    }

    if (report.jankRate > 0.1) {
      recommendations.add('检测到频繁卡顿，建议优化布局计算');
    }

    if (_currentQuality < 0.5) {
      recommendations.add('当前处于低质量模式，性能可能不足');
    }

    return recommendations;
  }

  /// 重置监控
  void reset() {
    _performanceMonitor.reset();
    _currentQuality = 1.0;
    _performanceStatus = PerformanceStatus.optimal;
  }

  void dispose() {
    _qualityAdjustmentTimer?.cancel();
    _performanceMonitor.stopMonitoring();
    unawaited(_warningController.close());
  }
}

/// 性能阈值配置
class PerformanceThresholds {
  const PerformanceThresholds({
    this.targetFps = 60.0,
    this.warningFps = 45.0,
    this.criticalFps = 30.0,
    this.maxJankFrames = 5,
    this.maxFrameTimeMs = 16.67,
  });

  final double targetFps;
  final double warningFps;
  final double criticalFps;
  final int maxJankFrames;
  final double maxFrameTimeMs;
}

/// 性能状态
enum PerformanceStatus {
  optimal, // 性能良好
  degraded, // 性能下降
  critical, // 性能严重不足
}

/// 性能警告类型
enum WarningType {
  lowFps,
  jank,
  slowRender,
  highMemory,
  layoutSlow,
}

/// 警告严重程度
enum WarningSeverity {
  info,
  warning,
  critical,
}

/// 性能警告
class PerformanceWarning {
  PerformanceWarning({
    required this.type,
    required this.message,
    required this.severity,
    this.report,
  }) : timestamp = DateTime.now();

  final WarningType type;
  final String message;
  final WarningSeverity severity;
  final PerformanceReport? report;
  final DateTime timestamp;
}

/// 性能摘要
class PerformanceSummary {
  const PerformanceSummary({
    required this.status,
    required this.quality,
    required this.report,
    required this.recommendations,
  });

  final PerformanceStatus status;
  final double quality;
  final PerformanceReport report;
  final List<String> recommendations;

  String get statusText {
    switch (status) {
      case PerformanceStatus.optimal:
        return '性能良好';
      case PerformanceStatus.degraded:
        return '性能下降';
      case PerformanceStatus.critical:
        return '性能严重不足';
    }
  }

  Color get statusColor {
    switch (status) {
      case PerformanceStatus.optimal:
        return const Color(0xFF4CAF50);
      case PerformanceStatus.degraded:
        return const Color(0xFFFFA726);
      case PerformanceStatus.critical:
        return const Color(0xFFF44336);
    }
  }

  /// Convenience getters for performance metrics
  double get fps => report.averageFps;
  double get frameTime => report.averageFrameTimeMs;
  double get jankRate => report.jankRate;
  int get frameCount => report.frameCount;
}

/// Galaxy监控集成Provider
final galaxyMonitoringProvider =
    Provider.autoDispose<GalaxyMonitoringIntegration>((ref) {
  final integration = GalaxyMonitoringIntegration(ref: ref);
  ref.onDispose(integration.dispose);
  return integration;
});

/// 性能指标Widget
class GalaxyPerformanceOverlay extends StatelessWidget {
  const GalaxyPerformanceOverlay({
    required this.child,
    super.key,
    this.showOverlay = true,
  });

  final Widget child;
  final bool showOverlay;

  @override
  Widget build(BuildContext context) {
    if (!showOverlay) return child;

    return Stack(
      children: [
        child,
        const Positioned(
          top: 50,
          right: 16,
          child: _PerformanceIndicator(),
        ),
      ],
    );
  }
}

class _PerformanceIndicator extends ConsumerWidget {
  const _PerformanceIndicator();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 获取监控服务
    final monitoring = ref.watch(galaxyMonitoringProvider);
    final summary = monitoring.getSummary();

    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: summary.statusColor.withValues(alpha: 0.5),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: summary.statusColor,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                summary.statusText,
                style: TextStyle(
                  color: summary.statusColor,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            'FPS: ${summary.report.averageFps.toStringAsFixed(1)}',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 10,
            ),
          ),
          Text(
            'Quality: ${(summary.quality * 100).toStringAsFixed(0)}%',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 10,
            ),
          ),
        ],
      ),
    );
  }
}

/// 性能调试面板
class GalaxyPerformanceDebugPanel extends ConsumerStatefulWidget {
  const GalaxyPerformanceDebugPanel({super.key});

  @override
  ConsumerState<GalaxyPerformanceDebugPanel> createState() =>
      _GalaxyPerformanceDebugPanelState();
}

class _GalaxyPerformanceDebugPanelState
    extends ConsumerState<GalaxyPerformanceDebugPanel> {
  final List<PerformanceWarning> _recentWarnings = [];
  StreamSubscription<PerformanceWarning>? _warningSubscription;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final monitoring = ref.read(galaxyMonitoringProvider);
      _warningSubscription = monitoring.warnings.listen((warning) {
        setState(() {
          _recentWarnings.insert(0, warning);
          if (_recentWarnings.length > 10) {
            _recentWarnings.removeLast();
          }
        });
      });
    });
  }

  @override
  void dispose() {
    unawaited(_warningSubscription?.cancel());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final monitoring = ref.watch(galaxyMonitoringProvider);
    final summary = monitoring.getSummary();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.black87,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // 标题
          Row(
            children: [
              const Icon(Icons.speed, color: Colors.white, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Galaxy Performance',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: summary.statusColor.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: summary.statusColor),
                ),
                child: Text(
                  summary.statusText,
                  style: TextStyle(
                    color: summary.statusColor,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // 指标
          _buildMetricRow(
              'Average FPS', summary.report.averageFps.toStringAsFixed(1),),
          _buildMetricRow('Avg Frame Time',
              '${summary.report.averageFrameTimeMs.toStringAsFixed(2)}ms',),
          _buildMetricRow('Jank Rate',
              '${(summary.report.jankRate * 100).toStringAsFixed(1)}%',),
          _buildMetricRow('Total Frames', summary.report.frameCount.toString()),
          const SizedBox(height: 8),
          _buildMetricRow('Quality Level',
              '${(summary.quality * 100).toStringAsFixed(0)}%',),

          // 建议
          if (summary.recommendations.isNotEmpty) ...[
            const Divider(color: Colors.white24),
            const Text(
              'Recommendations',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            ...summary.recommendations.map(
              (r) => Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Row(
                  children: [
                    const Icon(
                      Icons.lightbulb_outline,
                      color: Colors.amber,
                      size: 12,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        r,
                        style: const TextStyle(
                          color: Colors.white60,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],

          // 警告历史
          if (_recentWarnings.isNotEmpty) ...[
            const Divider(color: Colors.white24),
            const Text(
              'Recent Warnings',
              style: TextStyle(
                color: Colors.white70,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            ...(_recentWarnings.take(5).map(
                  (w) => Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Row(
                      children: [
                        Icon(
                          w.severity == WarningSeverity.critical
                              ? Icons.error
                              : Icons.warning,
                          color: w.severity == WarningSeverity.critical
                              ? Colors.red
                              : Colors.orange,
                          size: 12,
                        ),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Text(
                            w.message,
                            style: const TextStyle(
                              color: Colors.white60,
                              fontSize: 11,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                )),
          ],
        ],
      ),
    );
  }

  Widget _buildMetricRow(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: const TextStyle(
                color: Colors.white60,
                fontSize: 12,
              ),
            ),
            Text(
              value,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
}
