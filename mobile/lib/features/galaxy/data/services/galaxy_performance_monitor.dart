import 'package:flutter/foundation.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_optimization_config.dart';

enum PerformanceStatus { optimal, degraded, critical }
enum PerformanceSeverity { warning, error }

class PerformanceEvent {
  PerformanceEvent({required this.severity, required this.message});
  final PerformanceSeverity severity;
  final String message;
}

class PerformanceReport {
  PerformanceReport({
    this.averageFps = 60.0,
    this.jankRate = 0.0,
    this.averageFrameTimeMs = 16.6,
    this.frameCount = 0,
  });
  final double averageFps;
  final double jankRate;
  final double averageFrameTimeMs;
  final int frameCount;
}

class GalaxyPerformanceMonitor extends ChangeNotifier {
  GalaxyPerformanceMonitor(this._performanceService) {
    _init();
  }
  
  static final GalaxyPerformanceMonitor instance = GalaxyPerformanceMonitor(PerformanceService.instance);
  
  final PerformanceService _performanceService;
  
  late ValueNotifier<GalaxyOptimizationConfig> config;

  void _init() {
    config = ValueNotifier(
      GalaxyOptimizationConfig.fromTier(_performanceService.currentTier.value),
    );

    _performanceService.currentTier.addListener(_onTierChanged);
  }

  void _onTierChanged() {
    final newTier = _performanceService.currentTier.value;
    final newConfig = GalaxyOptimizationConfig.fromTier(newTier);
    
    // De-bounce or logic check could go here
    config.value = newConfig;
    notifyListeners();
  }
  
  void startMonitoring() {
    _performanceService.startMonitoring();
  }
  
  void stopMonitoring() {
    _performanceService.stopMonitoring();
  }

  void addEventListener(void Function(PerformanceEvent) listener) {
    // Legacy integration: PerformanceService doesn't have events yet,
    // but we can simulate or just provide a placeholder.
  }

  PerformanceReport getPerformanceReport() {
    return PerformanceReport(
      averageFps: 60.0, // Placeholder
      frameCount: 100,
    );
  }

  void reset() {
    // Reset performance data
  }

  @override
  void dispose() {
    _performanceService.currentTier.removeListener(_onTierChanged);
    config.dispose();
    super.dispose();
  }
}