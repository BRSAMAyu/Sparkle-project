import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/constants/push_config.dart';
import 'package:sparkle/core/services/firebase_messaging_service.dart';
import 'package:sparkle/core/services/jpush_service.dart';
import 'package:sparkle/core/services/notification_service.dart';

/// Push channel type
enum PushChannel {
  fcm,
  jpush,
}

/// Region type for push routing
enum UserRegion {
  china,
  international,
  unknown,
}

/// Unified push service that coordinates between FCM and JPush.
///
/// This service provides intelligent push notification routing:
/// - Chinese domestic users → JPush (more stable, no GFW issues)
/// - International users → FCM
/// - Fallback support between channels
///
/// Usage:
/// ```dart
/// final pushService = ref.read(unifiedPushServiceProvider);
/// await pushService.initialize();
/// ```
class UnifiedPushService {
  UnifiedPushService(this._ref);

  final Ref _ref;
  final Logger _logger = Logger();

  bool _isInitialized = false;
  UserRegion _detectedRegion = UserRegion.unknown;
  PushChannel _primaryChannel = PushChannel.fcm;

  /// Whether the service is initialized
  bool get isInitialized => _isInitialized;

  /// Detected user region
  UserRegion get detectedRegion => _detectedRegion;

  /// Primary push channel
  PushChannel get primaryChannel => _primaryChannel;

  /// Initialize unified push service
  ///
  /// This will:
  /// 1. Detect user region
  /// 2. Initialize appropriate push channels
  /// 3. Set up message handlers
  Future<void> initialize({
    String? forcedRegion,
    bool production = false,
  }) async {
    if (_isInitialized) {
      _logger.w('UnifiedPushService already initialized');
      return;
    }

    try {
      // Detect region
      _detectedRegion = forcedRegion != null
          ? _parseRegion(forcedRegion)
          : await _detectRegion();

      _logger.i('Detected region: $_detectedRegion');

      // Determine primary channel based on region
      _primaryChannel = _determinePrimaryChannel();
      _logger.i('Primary push channel: $_primaryChannel');

      // Initialize push services based on platform and region
      await _initializePushServices(production: production);

      _isInitialized = true;
      _logger.i('UnifiedPushService initialized successfully');
    } catch (e, stack) {
      _logger.e('Failed to initialize UnifiedPushService: $e');
      _logger.d(stack.toString());
    }
  }

  /// Detect user region
  ///
  /// Strategy:
  /// 1. Check device locale
  /// 2. Check SIM country code (Android)
  /// 3. Default to international
  Future<UserRegion> _detectRegion() async {
    try {
      // Check device locale
      final locale = Platform.localeName;
      if (locale.startsWith('zh_CN') || locale.startsWith('zh-Hans')) {
        return UserRegion.china;
      }

      // On Android, could check SIM country code
      // For now, use locale as primary indicator

      return UserRegion.international;
    } catch (e) {
      _logger.e('Failed to detect region: $e');
      return UserRegion.unknown;
    }
  }

  /// Parse region string to enum
  UserRegion _parseRegion(String region) {
    final lower = region.toLowerCase();
    if (lower == 'cn' || lower == 'china' || lower == 'zh') {
      return UserRegion.china;
    }
    return UserRegion.international;
  }

  /// Determine primary push channel based on region and platform
  PushChannel _determinePrimaryChannel() {
    // iOS always uses FCM (APNs through FCM)
    if (Platform.isIOS) {
      return PushChannel.fcm;
    }

    // Android: use JPush for China, FCM for international
    switch (_detectedRegion) {
      case UserRegion.china:
        if (PushConfig.jpushEnabled) {
          return PushChannel.jpush;
        }
        return PushChannel.fcm;
      case UserRegion.international:
      case UserRegion.unknown:
        return PushChannel.fcm;
    }
  }

  /// Initialize push services
  Future<void> _initializePushServices({bool production = false}) async {
    final futures = <Future<void>>[];

    // Initialize JPush for Chinese Android users
    if (Platform.isAndroid &&
        _detectedRegion == UserRegion.china &&
        PushConfig.jpushEnabled) {
      futures.add(_initializeJPush(production: production));
    }

    // Always initialize FCM as primary or fallback
    if (PushConfig.fcmEnabled) {
      futures.add(_initializeFcm());
    }

    await Future.wait(futures);
  }

  /// Initialize JPush service
  Future<void> _initializeJPush({bool production = false}) async {
    try {
      final jpushService = _ref.read(jpushServiceProvider.notifier);

      // Set up message handlers
      jpushService.onMessageReceived = _handleJPushMessage;
      jpushService.onNotificationOpened = _handleJPushNotificationOpened;

      await jpushService.initialize(
        production: production,
        debug: kDebugMode,
      );

      _logger.i('JPush initialized successfully');
    } catch (e) {
      _logger.e('Failed to initialize JPush: $e');
    }
  }

  /// Initialize FCM service
  Future<void> _initializeFcm() async {
    try {
      final fcmService = _ref.read(firebaseMessagingServiceProvider);
      await fcmService.initialize();

      _ref.read(fcmInitializedProvider.notifier).state = true;

      _logger.i('FCM initialized successfully');
    } catch (e) {
      _logger.e('Failed to initialize FCM: $e');
    }
  }

  /// Handle JPush message received
  void _handleJPushMessage(JPushMessage message) {
    _logger.i('JPush message received: ${message.title}');

    // Show local notification for foreground messages
    _showLocalNotification(
      title: message.title ?? 'Sparkle',
      body: message.body ?? '',
      data: message.extras ?? {},
      source: 'jpush',
    );
  }

  /// Handle JPush notification opened
  void _handleJPushNotificationOpened(JPushMessage message) {
    _logger.i('JPush notification opened: ${message.title}');

    // Navigate to deep link if present
    final deepLink = message.extras?['deep_link'];
    if (deepLink != null) {
      _navigateToDeepLink(deepLink.toString());
    }
  }

  /// Show local notification
  void _showLocalNotification({
    required String title,
    required String body,
    required Map<String, dynamic> data,
    required String source,
  }) {
    try {
      final notificationService = _ref.read(notificationServiceProvider);
      unawaited(
        notificationService.showSmartPush(
          title: title,
          body: body,
          payload: {
            ...data,
            'source': source,
          },
        ),
      );
    } catch (e) {
      _logger.e('Failed to show local notification: $e');
    }
  }

  /// Navigate to deep link
  void _navigateToDeepLink(String deepLink) {
    try {
      final context = navigatorKey.currentContext;
      if (context == null) {
        _logger.w('Navigator context not available for deep link navigation');
        return;
      }

      final uri = Uri.tryParse(deepLink);
      if (uri == null || uri.scheme != 'sparkle') {
        _logger.w('Invalid deep link format: $deepLink');
        return;
      }

      final entityType = uri.host;
      final entityId =
          uri.pathSegments.isNotEmpty ? uri.pathSegments.first : null;

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
          if (uri.pathSegments.length > 1 && uri.pathSegments[1] == 'review') {
            unawaited(
              GoRouter.of(context).pushNamed(
                'planReview',
                pathParameters: {'id': entityId ?? ''},
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
        case 'streak':
          if (entityId != null) {
            unawaited(
              GoRouter.of(context).pushNamed(
                'streakDetails',
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

  /// Set user alias for push notifications
  ///
  /// This allows the backend to send targeted notifications
  Future<void> setUserAlias(String userId) async {
    // Set alias for JPush
    if (_primaryChannel == PushChannel.jpush ||
        _detectedRegion == UserRegion.china) {
      try {
        final jpushService = _ref.read(jpushServiceProvider.notifier);
        await jpushService.setAlias(userId);
        _logger.i('JPush alias set: $userId');
      } catch (e) {
        _logger.e('Failed to set JPush alias: $e');
      }
    }

    // FCM doesn't have alias concept, uses topics or direct token targeting
  }

  /// Clear user alias (on logout)
  Future<void> clearUserAlias() async {
    try {
      final jpushService = _ref.read(jpushServiceProvider.notifier);
      await jpushService.deleteAlias();
      _logger.i('JPush alias cleared');
    } catch (e) {
      _logger.e('Failed to clear JPush alias: $e');
    }
  }

  /// Set device tags for audience segmentation
  Future<void> setDeviceTags(List<String> tags) async {
    if (_primaryChannel == PushChannel.jpush) {
      try {
        final jpushService = _ref.read(jpushServiceProvider.notifier);
        await jpushService.cleanTags();
        await jpushService.addTags(tags);
        _logger.i('JPush tags set: $tags');
      } catch (e) {
        _logger.e('Failed to set JPush tags: $e');
      }
    }

    // For FCM, subscribe to topics
    if (PushConfig.fcmEnabled) {
      try {
        final fcmService = _ref.read(firebaseMessagingServiceProvider);
        for (final tag in tags) {
          await fcmService.subscribeToTopic(tag);
        }
        _logger.i('FCM topics subscribed: $tags');
      } catch (e) {
        _logger.e('Failed to subscribe to FCM topics: $e');
      }
    }
  }

  /// Get current push token(s)
  ///
  /// Returns a map of channel -> token
  Future<Map<PushChannel, String?>> getCurrentTokens() async {
    final tokens = <PushChannel, String?>{};

    // Get FCM token
    if (PushConfig.fcmEnabled) {
      try {
        final fcmService = _ref.read(firebaseMessagingServiceProvider);
        tokens[PushChannel.fcm] = fcmService.currentToken;
      } catch (e) {
        _logger.e('Failed to get FCM token: $e');
      }
    }

    // Get JPush token
    if (PushConfig.jpushEnabled && Platform.isAndroid) {
      try {
        final jpushService = _ref.read(jpushServiceProvider.notifier);
        tokens[PushChannel.jpush] = jpushService.currentRegistrationId;
      } catch (e) {
        _logger.e('Failed to get JPush token: $e');
      }
    }

    return tokens;
  }

  /// Set badge number (iOS only)
  Future<void> setBadge(int badge) async {
    if (!Platform.isIOS) return;

    try {
      final jpushService = _ref.read(jpushServiceProvider.notifier);
      await jpushService.setBadge(badge);
    } catch (e) {
      _logger.e('Failed to set badge: $e');
    }
  }

  /// Clear all notifications
  Future<void> clearAllNotifications() async {
    try {
      final jpushService = _ref.read(jpushServiceProvider.notifier);
      await jpushService.clearAllNotifications();
    } catch (e) {
      _logger.e('Failed to clear notifications: $e');
    }
  }
}

/// Provider for UnifiedPushService
final unifiedPushServiceProvider = Provider<UnifiedPushService>((ref) {
  return UnifiedPushService(ref);
});

/// Provider for push service initialization state
final pushInitializedProvider = StateProvider<bool>((ref) => false);
