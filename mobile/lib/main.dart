import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/app.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:sparkle/features/chat/chat.dart';

void main() async {
  try {
    WidgetsFlutterBinding.ensureInitialized();

    // Initialize Performance Monitoring
    PerformanceService.instance.startMonitoring();

    // Initialize Hive for local storage
    await Hive.initFlutter();

    // Register Chat Adapters
    ChatCacheService.registerAdapters();

    // Initialize Local Database (Isar)
    await LocalDatabase().init();

    // Initialize SharedPrefs
    await SharedPreferences.getInstance();

    // Initialize ThemeManager
    await ThemeManager().initialize();

    // Initialize OpenTelemetry Tracing
    const otelEndpoint = String.fromEnvironment('OTEL_EXPORTER_OTLP_ENDPOINT');
    final collectorUri = otelEndpoint.isNotEmpty ? Uri.parse(otelEndpoint) : null;
    await TracingService.instance.initialize(collectorUri: collectorUri);

    // Enable Demo Mode via --dart-define=DEMO_MODE=true
    const isDemoMode = bool.fromEnvironment('DEMO_MODE');
    DemoDataService.isDemoMode = isDemoMode;

    // TODO: Open Hive boxes
    await Hive.openBox('settings');
    await Hive.openBox('user');

    runApp(
      const ProviderScope(
        child: SparkleApp(),
      ),
    );
  } catch (e, stack) {
    debugPrint('❌ FATAL ERROR DURING STARTUP: $e');
    debugPrint(stack.toString());
    
    // Show a minimal error app instead of just crashing
    runApp(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: SelectableText('App failed to start:\n\n$e\n\n$stack'),
            ),
          ),
        ),
      ),
    );
  }
}
