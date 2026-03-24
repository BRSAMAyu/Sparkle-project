/// Stub implementation for Firebase services
///
/// This file is used when Google services are disabled (ENABLE_GOOGLE_SERVICES=false)
/// to provide no-op implementations that allow the app to build and run
/// without Firebase dependencies.

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';

/// Stub Firebase Messaging Service
///
/// Provides no-op implementation when Firebase is disabled.
class FirebaseMessagingService {
  FirebaseMessagingService(this._ref);

  final Ref _ref;
  final Logger _logger = Logger();

  bool _isInitialized = false;
  String? _currentToken;

  /// Whether the service is initialized
  bool get isInitialized => _isInitialized;

  /// Current FCM token (always null when disabled)
  String? get currentToken => _currentToken;

  /// Initialize Firebase Messaging (no-op when disabled)
  Future<void> initialize() async {
    if (_isInitialized) {
      _logger.w('FirebaseMessagingService already initialized');
      return;
    }

    _logger.i('Firebase services disabled - skipping FCM initialization');
    _isInitialized = true;
    _ref.read(fcmInitializedProvider.notifier).state = true;
  }

  /// Subscribe to a topic (no-op when disabled)
  Future<void> subscribeToTopic(String topic) async {
    _logger.d('FCM disabled - skipping topic subscription: $topic');
  }

  /// Unsubscribe from a topic (no-op when disabled)
  Future<void> unsubscribeFromTopic(String topic) async {
    _logger.d('FCM disabled - skipping topic unsubscription: $topic');
  }

  /// Delete the current FCM token (no-op when disabled)
  Future<void> deleteToken() async {
    _currentToken = null;
    _ref.read(fcmInitializedProvider.notifier).state = false;
    _logger.d('FCM disabled - token deletion skipped');
  }
}

/// Provider for FirebaseMessagingService
final firebaseMessagingServiceProvider =
    Provider<FirebaseMessagingService>((ref) => FirebaseMessagingService(ref));

/// Provider for FCM initialization state
final fcmInitializedProvider = StateProvider<bool>((ref) => false);

/// Stub background message handler (no-op when disabled)
Future<void> firebaseMessagingBackgroundHandler(dynamic message) async {
  // No-op when Firebase is disabled
}
