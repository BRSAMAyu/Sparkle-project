import 'dart:async';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:jpush_flutter/jpush_flutter.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/constants/push_config.dart';
import 'package:sparkle/core/services/push_token_manager.dart';

/// JPush notification message
class JPushMessage {
  final String? title;
  final String? body;
  final Map<String, dynamic>? extras;
  final String? messageId;

  JPushMessage({
    this.title,
    this.body,
    this.extras,
    this.messageId,
  });

  factory JPushMessage.fromMap(Map<dynamic, dynamic> map) => JPushMessage(
        title: map['title']?.toString(),
        body: map['body']?.toString() ?? map['alert']?.toString(),
        extras: map['extras'] != null
            ? Map<String, dynamic>.from(map['extras'] as Map)
            : null,
        messageId: map['msgId']?.toString(),
      );
}

/// JPush service for handling push notifications via JPush SDK.
///
/// This service provides an alternative push channel for Chinese domestic
/// users where Google Play Services (FCM) may not be available.
///
/// Features:
/// - JPush SDK initialization
/// - Token registration with backend
/// - Foreground/background message handling
/// - Deep link navigation
class JPushService extends AsyncNotifier<void> {
  final Logger _logger = Logger();
  final JPush _jpush = JPush();

  String? _registrationId;
  bool _isInitialized = false;
  bool _isStopped = false;

  // Callbacks
  void Function(JPushMessage message)? onMessageReceived;
  void Function(JPushMessage message)? onNotificationOpened;
  void Function(String token)? onTokenRefresh;

  @override
  Future<void> build() async {
    try {
      // Service is built on demand.
      return;
    } catch (error, stackTrace) {
      _logger.e('Failed to build JPush service', error: error);
      Error.throwWithStackTrace(error, stackTrace);
    }
  }

  /// Initialize JPush SDK
  ///
  /// Returns true if initialization was successful
  Future<bool> initialize({
    bool production = false,
    bool debug = false,
  }) async {
    if (_isInitialized) {
      _logger.d('JPush already initialized');
      return true;
    }

    if (!Platform.isAndroid && !Platform.isIOS) {
      _logger.w('JPush only supports Android and iOS platforms');
      return false;
    }

    if (!PushConfig.jpushEnabled) {
      _logger.i('JPush is disabled via configuration');
      return false;
    }

    try {
      // Configure JPush
      _jpush.addEventHandler(
        onReceiveNotification: (Map<String, dynamic> message) async {
          _logger.i('JPush onReceiveNotification: $message');
          final jpushMessage = JPushMessage.fromMap(message);
          onMessageReceived?.call(jpushMessage);
        },
        onOpenNotification: (Map<String, dynamic> message) async {
          _logger.i('JPush onOpenNotification: $message');
          final jpushMessage = JPushMessage.fromMap(message);
          onNotificationOpened?.call(jpushMessage);
        },
        onReceiveMessage: (Map<String, dynamic> message) async {
          _logger.i('JPush onReceiveMessage: $message');
          // Custom message (not notification)
          final jpushMessage = JPushMessage.fromMap(message);
          onMessageReceived?.call(jpushMessage);
        },
        onReceiveNotificationAuthorization:
            (Map<String, dynamic> message) async {
          _logger.i('JPush onReceiveNotificationAuthorization: $message');
        },
      );

      // Initialize JPush
      _jpush.setup(
        appKey: PushConfig.jpushAppKey,
        channel: PushConfig.jpushChannel,
        production: production,
        debug: debug,
      );

      // Get registration ID
      _jpush.getRegistrationID().then((rid) {
        if (rid.isNotEmpty) {
          _registrationId = rid;
          _logger.i('JPush Registration ID: $rid');
          _registerTokenWithBackend(rid);
          onTokenRefresh?.call(rid);
        }
      });

      // Apply for notification permission (iOS)
      if (Platform.isIOS) {
        _jpush.applyPushAuthority();
      }

      _isInitialized = true;
      _logger.i('JPush initialized successfully');
      return true;
    } catch (e, stack) {
      _logger.e('Failed to initialize JPush: $e');
      _logger.d(stack.toString());
      return false;
    }
  }

  /// Register JPush token with backend
  Future<void> _registerTokenWithBackend(String registrationId) async {
    try {
      final tokenManager = ref.read(pushTokenManagerProvider.notifier);
      await tokenManager.registerToken(
        registrationId,
        tokenType: PushConfig.tokenTypeJpush,
        metadata: {
          'channel': PushConfig.jpushChannel,
          'provider': 'jpush',
        },
      );
      _logger.i('JPush token registered with backend');
    } catch (e) {
      _logger.e('Failed to register JPush token with backend: $e');
    }
  }

  /// Get current JPush registration ID
  Future<String?> getRegistrationId() async {
    if (!_isInitialized) {
      _logger.w('JPush not initialized');
      return null;
    }

    try {
      final rid = await _jpush.getRegistrationID();
      _registrationId = rid;
      return rid;
    } catch (e) {
      _logger.e('Failed to get JPush registration ID: $e');
      return null;
    }
  }

  /// Set alias for the device (typically user ID)
  ///
  /// This allows sending push notifications to specific users
  Future<bool> setAlias(String alias) async {
    if (!_isInitialized) {
      _logger.w('JPush not initialized');
      return false;
    }

    try {
      await _jpush.setAlias(alias);
      _logger.i('JPush alias set: $alias');
      return true;
    } catch (e) {
      _logger.e('Failed to set JPush alias: $e');
      return false;
    }
  }

  /// Remove alias
  Future<bool> deleteAlias() async {
    if (!_isInitialized) {
      _logger.w('JPush not initialized');
      return false;
    }

    try {
      await _jpush.deleteAlias();
      _logger.i('JPush alias deleted');
      return true;
    } catch (e) {
      _logger.e('Failed to delete JPush alias: $e');
      return false;
    }
  }

  /// Add tags for the device
  ///
  /// Tags can be used for audience segmentation
  Future<bool> addTags(List<String> tags) async {
    if (!_isInitialized) {
      _logger.w('JPush not initialized');
      return false;
    }

    try {
      await _jpush.addTags(tags);
      _logger.i('JPush tags added: $tags');
      return true;
    } catch (e) {
      _logger.e('Failed to add JPush tags: $e');
      return false;
    }
  }

  /// Delete tags
  Future<bool> deleteTags(List<String> tags) async {
    if (!_isInitialized) {
      _logger.w('JPush not initialized');
      return false;
    }

    try {
      await _jpush.deleteTags(tags);
      _logger.i('JPush tags deleted: $tags');
      return true;
    } catch (e) {
      _logger.e('Failed to delete JPush tags: $e');
      return false;
    }
  }

  /// Clean all tags
  Future<bool> cleanTags() async {
    if (!_isInitialized) {
      _logger.w('JPush not initialized');
      return false;
    }

    try {
      await _jpush.cleanTags();
      _logger.i('JPush tags cleaned');
      return true;
    } catch (e) {
      _logger.e('Failed to clean JPush tags: $e');
      return false;
    }
  }

  /// Set badge number (iOS only)
  Future<bool> setBadge(int badge) async {
    if (!Platform.isIOS) {
      return true; // Badge is iOS only
    }

    if (!_isInitialized) {
      _logger.w('JPush not initialized');
      return false;
    }

    try {
      _jpush.setBadge(badge);
      _logger.d('JPush badge set: $badge');
      return true;
    } catch (e) {
      _logger.e('Failed to set JPush badge: $e');
      return false;
    }
  }

  /// Stop push service
  Future<void> stopPush() async {
    if (!_isInitialized) return;

    try {
      _jpush.stopPush();
      _isStopped = true;
      _logger.i('JPush stopped');
    } catch (e) {
      _logger.e('Failed to stop JPush: $e');
    }
  }

  /// Resume push service
  Future<void> resumePush() async {
    if (!_isInitialized) return;

    try {
      _jpush.resumePush();
      _isStopped = false;
      _logger.i('JPush resumed');
    } catch (e) {
      _logger.e('Failed to resume JPush: $e');
    }
  }

  /// Check if push service is stopped
  Future<bool> isPushStopped() async {
    if (!_isInitialized) return false;

    try {
      return _isStopped;
    } catch (e) {
      _logger.e('Failed to check JPush status: $e');
      return false;
    }
  }

  /// Clear all notifications
  Future<void> clearAllNotifications() async {
    if (!_isInitialized) return;

    try {
      _jpush.clearAllNotifications();
      _logger.i('All JPush notifications cleared');
    } catch (e) {
      _logger.e('Failed to clear JPush notifications: $e');
    }
  }

  /// Get current registration ID (cached)
  String? get currentRegistrationId => _registrationId;

  /// Check if JPush is initialized
  bool get isInitialized => _isInitialized;

  /// Dispose resources
  void dispose() {
    onMessageReceived = null;
    onNotificationOpened = null;
    onTokenRefresh = null;
  }
}

/// Provider for JPushService
final jpushServiceProvider =
    AsyncNotifierProvider<JPushService, void>(JPushService.new);
