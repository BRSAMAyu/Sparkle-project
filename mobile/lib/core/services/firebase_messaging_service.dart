import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/push_token_manager.dart';

/// Background message handler (must be top-level function)
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Initialize Firebase for background isolate
  await Firebase.initializeApp();

  final logger = Logger();
  logger.i(
    '📱 Background message received: ${message.messageId}',
  );
  logger.d('Title: ${message.notification?.title}');
  logger.d('Body: ${message.notification?.body}');
  logger.d('Data: ${message.data}');

  // Note: Local notification display is handled automatically by FCM
  // when the app is in background/terminated state
}

/// Firebase Cloud Messaging Service
///
/// Handles push notifications via FCM for both Android and iOS.
/// Supports three message scenarios:
/// 1. Foreground: Shows local notification
/// 2. Background: System notification (handled by FCM)
/// 3. Terminated: System notification, app launch on tap
class FirebaseMessagingService {
  FirebaseMessagingService(this._ref);

  final Ref _ref;
  final Logger _logger = Logger();
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;

  bool _isInitialized = false;
  String? _currentToken;

  /// Whether the service is initialized
  bool get isInitialized => _isInitialized;

  /// Current FCM token
  String? get currentToken => _currentToken;

  /// Initialize Firebase Messaging
  Future<void> initialize() async {
    if (_isInitialized) {
      _logger.w('FirebaseMessagingService already initialized');
      return;
    }

    try {
      // Request permission
      final settings = await _requestPermission();
      _logger.i('Notification permission status: ${settings.authorizationStatus}');

      // Get initial token
      _currentToken = await _messaging.getToken();
      if (_currentToken != null) {
        _logger.i('📱 FCM token obtained: ${_currentToken!.substring(0, 20)}...');
        await _registerToken(_currentToken!);
      }

      // Listen for token refresh
      _messaging.onTokenRefresh.listen((token) {
        _logger.i('📱 FCM token refreshed');
        _currentToken = token;
        unawaited(_registerToken(token));
      });

      // 1. Foreground messages
      FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

      // 2. Background messages (when app is in background but not terminated)
      FirebaseMessaging.onMessageOpenedApp.listen(_handleMessageOpened);

      // 3. Terminated state - check for initial message
      _checkInitialMessage();

      // Register background handler
      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

      _isInitialized = true;
      _logger.i('FirebaseMessagingService initialized successfully');
    } catch (e, stack) {
      _logger.e('Failed to initialize FirebaseMessagingService: $e');
      _logger.d(stack.toString());
    }
  }

  Future<NotificationSettings> _requestPermission() async {
    final settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
      criticalAlert: false,
    );
    return settings;
  }

  Future<void> _checkInitialMessage() async {
    final initialMessage = await _messaging.getInitialMessage();
    if (initialMessage != null) {
      _logger.i('📱 App opened from terminated state via notification');
      _handleMessageOpened(initialMessage);
    }
  }

  /// Handle foreground message (app is visible)
  void _handleForegroundMessage(RemoteMessage message) {
    _logger.i('📱 Foreground message: ${message.messageId}');

    final notification = message.notification;
    final data = message.data;

    if (notification != null) {
      _showLocalNotification(
        title: notification.title ?? 'Sparkle',
        body: notification.body ?? '',
        data: Map<String, dynamic>.from(data),
      );
    }

    // Emit event for analytics/tracking
    _emitNotificationEvent(message);
  }

  /// Handle message opened (from background or terminated)
  void _handleMessageOpened(RemoteMessage message) {
    _logger.i('📱 Message opened: ${message.messageId}');
    _logger.d('Data: ${message.data}');

    // Navigate to deep link if present
    final deepLink = message.data['deep_link'];
    if (deepLink is String && deepLink.isNotEmpty) {
      _navigateToDeepLink(deepLink);
    }

    // Emit event for analytics/tracking
    _emitNotificationEvent(message);
  }

  void _showLocalNotification({
    required String title,
    required String body,
    required Map<String, dynamic> data,
  }) {
    try {
      final notificationService = _ref.read(notificationServiceProvider);
      unawaited(
        notificationService.showSmartPush(
          title: title,
          body: body,
          payload: {
            ...data,
            'source': 'fcm',
          },
        ),
      );
    } catch (e) {
      _logger.e('Failed to show local notification: $e');
    }
  }

  void _navigateToDeepLink(String deepLink) {
    try {
      final context = navigatorKey.currentContext;
      if (context == null) {
        _logger.w('Navigator context not available for deep link navigation');
        return;
      }

      // Parse deep link: sparkle://entity/id
      final uri = Uri.tryParse(deepLink);
      if (uri == null || uri.scheme != 'sparkle') {
        _logger.w('Invalid deep link format: $deepLink');
        return;
      }

      final entityType = uri.host;
      final entityId = uri.pathSegments.isNotEmpty ? uri.pathSegments.first : null;

      _logger.i('Navigating to deep link: $entityType/$entityId');

      switch (entityType) {
        case 'task':
          if (entityId != null) {
            unawaited(
              GoRouter.of(context).pushNamed(
                'taskExecution',
                pathParameters: {'id': entityId},
              ),
            );
          }
        case 'achievement':
          if (entityId != null) {
            unawaited(
              GoRouter.of(context).pushNamed(
                'achievementDetail',
                pathParameters: {'id': entityId},
              ),
            );
          }
        case 'chat':
          if (entityId != null) {
            unawaited(
              GoRouter.of(context).pushNamed(
                'chat',
                queryParameters: {'session_id': entityId},
              ),
            );
          }
        case 'plan':
          if (entityId != null &&
              uri.pathSegments.length > 1 &&
              uri.pathSegments[1] == 'review') {
            unawaited(
              GoRouter.of(context).pushNamed(
                'planReview',
                pathParameters: {'id': entityId},
              ),
            );
          } else if (entityId != null) {
            unawaited(
              GoRouter.of(context).pushNamed(
                'planDetail',
                pathParameters: {'id': entityId},
              ),
            );
          }
        default:
          _logger.w('Unknown deep link entity type: $entityType');
      }
    } catch (e, stack) {
      _logger.e('Failed to navigate to deep link: $e');
      _logger.d(stack.toString());
    }
  }

  void _emitNotificationEvent(RemoteMessage message) {
    // This can be extended to emit to a stream or provider
    // for app-wide notification event handling
    _logger.d('Notification event: ${message.messageId}');
  }

  Future<void> _registerToken(String token) async {
    try {
      final tokenManager = _ref.read(pushTokenManagerProvider.notifier);
      await tokenManager.registerToken(token);
    } catch (e) {
      _logger.e('Failed to register FCM token: $e');
    }
  }

  /// Subscribe to a topic
  Future<void> subscribeToTopic(String topic) async {
    try {
      await _messaging.subscribeToTopic(topic);
      _logger.i('Subscribed to topic: $topic');
    } catch (e) {
      _logger.e('Failed to subscribe to topic $topic: $e');
    }
  }

  /// Unsubscribe from a topic
  Future<void> unsubscribeFromTopic(String topic) async {
    try {
      await _messaging.unsubscribeFromTopic(topic);
      _logger.i('Unsubscribed from topic: $topic');
    } catch (e) {
      _logger.e('Failed to unsubscribe from topic $topic: $e');
    }
  }

  /// Delete the current FCM token
  Future<void> deleteToken() async {
    try {
      await _messaging.deleteToken();
      _currentToken = null;
      _logger.i('FCM token deleted');
    } catch (e) {
      _logger.e('Failed to delete FCM token: $e');
    }
  }
}

/// Provider for FirebaseMessagingService
final firebaseMessagingServiceProvider =
    Provider<FirebaseMessagingService>((ref) {
  return FirebaseMessagingService(ref);
});

/// Provider for FCM initialization state
final fcmInitializedProvider = StateProvider<bool>((ref) => false);
