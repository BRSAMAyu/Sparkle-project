import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/app.dart';
import 'package:sparkle/core/design/tokens_v2/theme_manager.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/client_observability_service.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/performance_monitor.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/social_auth_service.dart';
import 'package:sparkle/core/services/user_preferences_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/cognitive/data/repositories/local_cognitive_repository.dart';

const _startupErrorPadding = 24.0;

void main() async {
  final startupStopwatch = Stopwatch()..start();
  try {
    WidgetsFlutterBinding.ensureInitialized();

    FlutterError.onError = (details) {
      FlutterError.presentError(details);
      PerformanceMonitor().reportCrash(
        details.exception,
        details.stack ?? StackTrace.current,
        context: 'flutter_error',
      );
    };
    PlatformDispatcher.instance.onError = (error, stack) {
      PerformanceMonitor().reportCrash(
        error,
        stack,
        context: 'platform_dispatcher',
      );
      return true;
    };

    // Initialize Hive for local storage
    await Hive.initFlutter();

    // Register Chat Adapters
    ChatCacheService.registerAdapters();

    // Initialize Local Database (Isar)
    await LocalDatabase().init();

    // Migrate legacy Hive cognitive queue into Outbox
    await LocalCognitiveRepository(localDb: LocalDatabase())
        .migrateToOutboxIfNeeded();

    // Initialize SharedPrefs
    final prefs = await SharedPreferences.getInstance();
    await PerformanceService.instance.hydratePreferences(prefs);
    PerformanceService.instance.startMonitoring();

    // Initialize critical services required before the first meaningful frame.
    const otelEndpoint = String.fromEnvironment('OTEL_EXPORTER_OTLP_ENDPOINT');
    final collectorUri =
        otelEndpoint.isNotEmpty ? Uri.parse(otelEndpoint) : null;
    await Future.wait(<Future<void>>[
      ViewStorageService.ensureInitialized(),
      ThemeManager().initialize(),
      TracingService.instance.initialize(collectorUri: collectorUri),
    ]);

    // Enable Demo Mode via --dart-define=DEMO_MODE=true
    const isDemoMode = bool.fromEnvironment('DEMO_MODE');
    DemoDataService.isDemoMode =
        isDemoMode || (prefs.getBool('demo_guest_mode_enabled') ?? false);

    // Initialize unified push service (FCM + JPush)
    // This will be called after app starts, as it needs ProviderScope
    // The actual initialization happens in SparkleApp

    runApp(
      ProviderScope(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          userPreferencesServiceProvider.overrideWithValue(
            UserPreferencesService(prefs),
          ),
        ],
        child: const SparkleApp(),
      ),
    );

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final firstFrameMs = startupStopwatch.elapsedMilliseconds;
      unawaited(
        ClientObservabilityService.instance.recordEvent(
          eventType: 'app_first_frame',
          category: 'lifecycle',
          route: 'bootstrap',
          metadata: <String, dynamic>{
            'startup_ms': firstFrameMs,
            'demo_mode': DemoDataService.isDemoMode,
          },
        ),
      );
    });

    unawaited(_runDeferredStartupWarmups());

    unawaited(
      ClientObservabilityService.instance.recordEvent(
        eventType: 'app_launch',
        category: 'lifecycle',
        route: 'bootstrap',
        metadata: <String, dynamic>{
          'demo_mode': DemoDataService.isDemoMode,
        },
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
              padding: const EdgeInsets.all(_startupErrorPadding),
              child: SelectableText('App failed to start:\n\n$e\n\n$stack'),
            ),
          ),
        ),
      ),
    );
  }
}

Future<void> _runDeferredStartupWarmups() async {
  try {
    await Future.wait(<Future<void>>[
      Hive.openBox<dynamic>('settings'),
      Hive.openBox<dynamic>('user'),
      SensoryFeedbackService.init(),
      BgmService.init(),
      SocialAuthService().initWeChat(),
      _initializeFirebase(),
    ]);
  } catch (e, stack) {
    debugPrint('⚠️ Deferred startup warmup failed: $e');
    PerformanceMonitor().reportCrash(
      e,
      stack,
      context: 'deferred_startup_warmup',
    );
  }
}

/// Initialize Firebase and FCM
///
/// This initializes Firebase Core and Firebase Cloud Messaging.
/// Requires:
/// - Android: google-services.json in android/app/
/// - iOS: GoogleService-Info.plist in ios/Runner/
Future<void> _initializeFirebase() async {
  try {
    // Check if Firebase is already initialized (by native plugins)
    // If using FlutterFire CLI generated options, use:
    // await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

    // For now, let native plugins handle initialization
    // Firebase will be initialized when FirebaseMessagingService.initialize() is called
    debugPrint('🔥 Firebase will be initialized on demand');
  } catch (e) {
    // Firebase initialization failure should not crash the app
    // Push notifications will simply be unavailable
    debugPrint('⚠️ Firebase initialization skipped: $e');
  }
}
