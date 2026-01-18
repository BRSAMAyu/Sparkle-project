import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// App category classification
enum AppCategory {
  productivity,
  study,
  entertainment,
  social,
  utility,
  unknown,
}

/// App usage event
class AppUsageEvent {
  final String packageName;
  final AppCategory category;
  final DateTime timestamp;
  final bool isForeground;

  AppUsageEvent({
    required this.packageName,
    required this.category,
    required this.timestamp,
    required this.isForeground,
  });
}

/// Service for tracking app usage and detecting user activity patterns
class AppUsageService {
  static const _channel = MethodChannel('com.sparkle/app_usage');

  final List<String> _productivityApps = [
    'com.apple.mobilenotes',
    'com.microsoft.office.word',
    'com.google.android.apps.docs',
    'com.notion.id',
  ];

  final List<String> _studyApps = [
    'com.duolingo',
    'com.khanacademy.android',
    'com.wolfram.android.alpha',
  ];

  DateTime? _lastTouchEvent;
  final _usageEventController = StreamController<AppUsageEvent>.broadcast();
  Timer? _monitoringTimer;

  Stream<AppUsageEvent> get usageEvents => _usageEventController.stream;

  /// Get the currently active foreground app
  Future<String?> getCurrentForegroundApp() async {
    try {
      final result = await _channel.invokeMethod<String>('getForegroundApp');
      return result;
    } on PlatformException catch (e) {
      print('Error getting foreground app: ${e.message}');
      return null;
    }
  }

  /// Classify an app by its package name
  Future<AppCategory> classifyApp(String packageName) async {
    if (_productivityApps.contains(packageName)) {
      return AppCategory.productivity;
    }
    if (_studyApps.contains(packageName)) {
      return AppCategory.study;
    }

    // Check for social/entertainment keywords
    if (packageName.contains('facebook') ||
        packageName.contains('instagram') ||
        packageName.contains('twitter') ||
        packageName.contains('tiktok')) {
      return AppCategory.social;
    }

    if (packageName.contains('youtube') ||
        packageName.contains('netflix') ||
        packageName.contains('game')) {
      return AppCategory.entertainment;
    }

    return AppCategory.unknown;
  }

  /// Check if current activity is whitelisted (should not interrupt)
  bool isActivityWhitelisted(AppCategory category) {
    return category == AppCategory.productivity ||
           category == AppCategory.study;
  }

  /// Detect continuous read pattern (no touch for >30s)
  bool detectsContinuousRead() {
    if (_lastTouchEvent == null) return false;

    final duration = DateTime.now().difference(_lastTouchEvent!);
    return duration.inSeconds > 30;
  }

  /// Record touch event
  void recordTouchEvent() {
    _lastTouchEvent = DateTime.now();
  }

  /// Start monitoring app usage
  void startMonitoring({Duration interval = const Duration(seconds: 10)}) {
    _monitoringTimer?.cancel();
    _monitoringTimer = Timer.periodic(interval, (_) async {
      final packageName = await getCurrentForegroundApp();
      if (packageName != null) {
        final category = await classifyApp(packageName);
        _usageEventController.add(AppUsageEvent(
          packageName: packageName,
          category: category,
          timestamp: DateTime.now(),
          isForeground: true,
        ));
      }
    });
  }

  /// Stop monitoring
  void stopMonitoring() {
    _monitoringTimer?.cancel();
  }

  void dispose() {
    stopMonitoring();
    _usageEventController.close();
  }
}

/// Provider for AppUsageService
final appUsageServiceProvider = Provider<AppUsageService>((ref) {
  final service = AppUsageService();
  ref.onDispose(() => service.dispose());
  return service;
});
