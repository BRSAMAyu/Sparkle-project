import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/intervention_action_service.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

// Global navigator key to allow navigation without context from notifications
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

/// 通知权限状态
class NotificationPermissionStatus {
  final bool hasPermission;
  final bool? alertEnabled;
  final bool? badgeEnabled;
  final bool? soundEnabled;
  final String? denialReason;

  const NotificationPermissionStatus({
    required this.hasPermission,
    this.alertEnabled,
    this.badgeEnabled,
    this.soundEnabled,
    this.denialReason,
  });

  factory NotificationPermissionStatus.granted() =>
      const NotificationPermissionStatus(hasPermission: true);

  factory NotificationPermissionStatus.denied({String? reason}) =>
      NotificationPermissionStatus(hasPermission: false, denialReason: reason);

  factory NotificationPermissionStatus.partial({
    bool? alert,
    bool? badge,
    bool? sound,
  }) {
    final hasAny = alert == true || badge == true || sound == true;
    return NotificationPermissionStatus(
      hasPermission: hasAny,
      alertEnabled: alert,
      badgeEnabled: badge,
      soundEnabled: sound,
    );
  }

  @override
  String toString() =>
      'NotificationPermissionStatus(hasPermission: $hasPermission, '
      'alert: $alertEnabled, badge: $badgeEnabled, sound: $soundEnabled)';
}

class NotificationService {
  NotificationService(this._ref, {bool autoInitialize = true}) {
    if (autoInitialize) {
      unawaited(_initialize());
    }
  }
  final Ref _ref;
  final FlutterLocalNotificationsPlugin _notificationsPlugin =
      FlutterLocalNotificationsPlugin();
  final Logger _logger = Logger();
  bool _isInitialized = false;

  Future<void> _initialize() async {
    tz_data.initializeTimeZones();
    // Assuming Asia/Shanghai for default, but should ideally get from device
    // tz.setLocalLocation(tz.getLocation('Asia/Shanghai'));

    const initializationSettingsAndroid = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    ); // Verify icon name

    final initializationSettingsDarwin = DarwinInitializationSettings(
      notificationCategories: <DarwinNotificationCategory>[
        DarwinNotificationCategory(
          'sparkle_smart_push',
          actions: <DarwinNotificationAction>[
            DarwinNotificationAction.plain(
              'START_NOW',
              '⚡ 开始',
              options: <DarwinNotificationActionOption>{
                DarwinNotificationActionOption.foreground,
              },
            ),
            DarwinNotificationAction.plain(
              'SNOOZE',
              '💤 稍后',
            ),
            DarwinNotificationAction.plain(
              'DISMISS',
              '🔕 勿扰',
              options: <DarwinNotificationActionOption>{
                DarwinNotificationActionOption.destructive,
              },
            ),
          ],
        ),
      ],
    );

    final initializationSettings = InitializationSettings(
      android: initializationSettingsAndroid,
      iOS: initializationSettingsDarwin,
      macOS: initializationSettingsDarwin,
    );

    await _notificationsPlugin.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: _onNotificationResponse,
      onDidReceiveBackgroundNotificationResponse:
          _onBackgroundNotificationResponse,
    );

    // Create Channel
    const channel = AndroidNotificationChannel(
      'sparkle_smart_push', // id
      'Smart Push Notifications', // title
      description: 'Notifications for Sparkle Smart Push', // description
      importance: Importance.high,
    );

    await _notificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);

    _isInitialized = true;
    _logger.i('NotificationService initialized');
  }

  /// 检查通知权限状态
  Future<NotificationPermissionStatus> checkPermissionStatus() async {
    if (!_isInitialized) {
      await _initialize();
    }

    try {
      // Android
      final androidPlugin =
          _notificationsPlugin.resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>();
      if (androidPlugin != null) {
        final granted = await androidPlugin.areNotificationsEnabled();
        // Android 13+: areNotificationsEnabled returns bool
        // For older Android, notifications are always enabled
        return NotificationPermissionStatus(
          hasPermission: granted ?? true,
          alertEnabled: granted,
          badgeEnabled: granted,
          soundEnabled: granted,
        );
      }

      // iOS
      final iosPlugin =
          _notificationsPlugin.resolvePlatformSpecificImplementation<
              IOSFlutterLocalNotificationsPlugin>();
      if (iosPlugin != null) {
        final settings = await iosPlugin.checkPermissions();
        if (settings != null) {
          return NotificationPermissionStatus.partial(
            alert: settings.isEnabled,
            badge: settings.isEnabled,
            sound: settings.isEnabled,
          );
        }
      }

      // macOS
      final macosPlugin =
          _notificationsPlugin.resolvePlatformSpecificImplementation<
              MacOSFlutterLocalNotificationsPlugin>();
      if (macosPlugin != null) {
        final settings = await macosPlugin.checkPermissions();
        if (settings != null) {
          return NotificationPermissionStatus.partial(
            alert: settings.isEnabled,
            badge: settings.isEnabled,
            sound: settings.isEnabled,
          );
        }
      }

      // Fallback: assume granted if we can't check
      return NotificationPermissionStatus.granted();
    } catch (e) {
      _logger.e('Failed to check notification permission: $e');
      return NotificationPermissionStatus.denied(reason: e.toString());
    }
  }

  /// 请求通知权限
  Future<bool> requestPermission() async {
    if (!_isInitialized) {
      await _initialize();
    }

    try {
      // Android
      final androidPlugin =
          _notificationsPlugin.resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>();
      if (androidPlugin != null) {
        final granted = await androidPlugin.requestNotificationsPermission();
        return granted ?? false;
      }

      // iOS
      final iosPlugin =
          _notificationsPlugin.resolvePlatformSpecificImplementation<
              IOSFlutterLocalNotificationsPlugin>();
      if (iosPlugin != null) {
        final granted = await iosPlugin.requestPermissions(
          alert: true,
          badge: true,
          sound: true,
        );
        return granted ?? false;
      }

      // macOS
      final macosPlugin =
          _notificationsPlugin.resolvePlatformSpecificImplementation<
              MacOSFlutterLocalNotificationsPlugin>();
      if (macosPlugin != null) {
        final granted = await macosPlugin.requestPermissions(
          alert: true,
          badge: true,
          sound: true,
        );
        return granted ?? false;
      }

      return true; // Other platforms assume granted
    } catch (e) {
      _logger.e('Failed to request notification permission: $e');
      return false;
    }
  }

  /// 是否已初始化
  bool get isInitialized => _isInitialized;

  // Static/Global callback for background handling if needed
  @pragma('vm:entry-point')
  static void _onBackgroundNotificationResponse(NotificationResponse details) {
    // Handle background actions (snooze, dismiss)
    debugPrint('Background notification action: ${details.actionId}');
  }

  void _onNotificationResponse(NotificationResponse details) {
    _logger.i(
      'Notification action: ${details.actionId}, payload: ${details.payload}',
    );

    if (details.payload != null) {
      try {
        final decodedPayload = jsonDecode(details.payload!);
        final payload = decodedPayload is Map<String, dynamic>
            ? decodedPayload
            : <String, dynamic>{};

        final actionId = details.actionId;
        final interactionAction = _mapInteractionAction(actionId);
        if (interactionAction != null) {
          unawaited(_reportPushInteraction(interactionAction, payload));
        }

        final interventionAction = _mapInterventionLifecycleAction(actionId);
        if (interventionAction != null) {
          unawaited(
            _ref
                .read(interventionActionServiceProvider)
                .reportActionFromPayload(
              payload: payload,
              action: interventionAction,
              surface: 'local_notification',
              extraPayload: {
                'source': 'local_notification_response',
                if (actionId != null) 'action_id': actionId,
              },
            ),
          );
        }

        if (actionId == null || actionId == 'START_NOW') {
          _navigateToPayload(payload);
        }

        if (actionId == 'SNOOZE') {
          // Handle Snooze API call
          _handleSnooze(payload);
        } else if (actionId == 'DISMISS') {
          // Handle Dismiss API call
          _handleDismiss(payload);
        }
      } catch (e) {
        _logger.e('Error parsing notification payload: $e');
      }
    }
  }

  void _handleSnooze(Map<String, dynamic> payload) {
    // TRACKED(TD-003): Call API to snooze
    _logger.i('Snoozing notification: $payload');
  }

  void _handleDismiss(Map<String, dynamic> payload) {
    // TRACKED(TD-003): Call API to dismiss
    _logger.i('Dismissing notification: $payload');
  }

  String? _mapInteractionAction(String? actionId) {
    if (actionId == null) {
      return 'opened';
    }
    switch (actionId) {
      case 'START_NOW':
        return 'opened';
      case 'SNOOZE':
      case 'DISMISS':
        return 'dismissed';
      default:
        return null;
    }
  }

  String? _mapInterventionLifecycleAction(String? actionId) {
    if (actionId == null) {
      return 'seen';
    }
    switch (actionId) {
      case 'START_NOW':
        return 'accepted';
      case 'SNOOZE':
        return 'snoozed';
      case 'DISMISS':
        return 'dismissed';
      default:
        return null;
    }
  }

  Future<void> _reportPushInteraction(
    String action,
    Map<String, dynamic> payload,
  ) async {
    final pushId = payload['push_id'] ?? payload['pushId'] ?? payload['pushID'];
    if (pushId == null) {
      _logger.w('Push interaction missing push_id: $payload');
      return;
    }
    try {
      final apiClient = _ref.read(apiClientProvider);
      await apiClient.post<void>(
        ApiEndpoints.pushInteraction,
        data: <String, dynamic>{
          'push_id': pushId,
          'action': action,
          'timestamp': DateTime.now().toUtc().toIso8601String(),
        },
      );
    } catch (e) {
      _logger.w('Failed to report push interaction: $e');
    }
  }

  void _navigateToPayload(Map<String, dynamic> payload) {
    final context = navigatorKey.currentContext;
    if (context == null) {
      _logger.w('Navigator context not available for notification navigation');
      return;
    }

    final destinationRoute = payload['destination_route'] as String?;
    if (destinationRoute != null && destinationRoute.isNotEmpty) {
      unawaited(
        RouteResilience.openExternalRoute(
          context,
          destinationRoute,
          currentContextLookup: () => navigatorKey.currentContext,
        ),
      );
      return;
    }

    final deepLink = payload['deep_link']?.toString().trim();
    if (deepLink != null && deepLink.isNotEmpty) {
      if (DeepLinkService.handleExternalDeepLink(
        context,
        deepLink,
        currentContextLookup: () => navigatorKey.currentContext,
      )) {
        return;
      }
    }

    final taskId =
        payload['taskId']?.toString() ?? payload['entity_id']?.toString();
    if (taskId != null && taskId.isNotEmpty) {
      unawaited(
        RouteResilience.openExternalRoute(
          context,
          '/tasks/$taskId/execute',
          currentContextLookup: () => navigatorKey.currentContext,
        ),
      );
      return;
    }
  }

  Future<void> showSmartPush({
    required String title,
    required String body,
    required Map<String, dynamic> payload,
  }) async {
    const androidDetails = AndroidNotificationDetails(
      'sparkle_smart_push',
      'Smart Push Notifications',
      channelDescription: 'Notifications for Sparkle Smart Push',
      importance: Importance.high,
      priority: Priority.high,
      ticker: 'ticker',
      actions: <AndroidNotificationAction>[
        AndroidNotificationAction(
          'START_NOW',
          '⚡ 开始',
          showsUserInterface: true,
        ),
        AndroidNotificationAction(
          'SNOOZE',
          '💤 稍后',
        ),
        AndroidNotificationAction(
          'DISMISS',
          '🔕 勿扰',
        ),
      ],
    );

    const darwinDetails = DarwinNotificationDetails(
      categoryIdentifier: 'sparkle_smart_push',
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    const notificationDetails = NotificationDetails(
      android: androidDetails,
      iOS: darwinDetails,
      macOS: darwinDetails,
    );

    await _notificationsPlugin.show(
      DateTime.now().millisecond, // unique ID
      title,
      body,
      notificationDetails,
      payload: jsonEncode(payload),
    );
  }

  Future<void> scheduleNotification({
    required int id,
    required String title,
    required String body,
    required DateTime scheduledDate,
    required Map<String, dynamic> payload,
    DateTimeComponents? matchDateTimeComponents,
  }) async {
    const androidDetails = AndroidNotificationDetails(
      'sparkle_calendar_reminders',
      'Calendar Reminders',
      channelDescription: 'Reminders for Calendar Events',
      importance: Importance.high,
      priority: Priority.high,
    );

    const notificationDetails = NotificationDetails(android: androidDetails);

    // Ensure we are scheduling in the future (unless it's a recurring event, logic might differ but for simple schedule, yes)
    // For recurring, zonedSchedule handles it if matchDateTimeComponents is set
    if (matchDateTimeComponents == null &&
        scheduledDate.isBefore(DateTime.now())) {
      _logger
          .w('Attempted to schedule notification in the past: $scheduledDate');
      return;
    }

    await _notificationsPlugin.zonedSchedule(
      id,
      title,
      body,
      tz.TZDateTime.from(scheduledDate, tz.local),
      notificationDetails,
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
      payload: jsonEncode(payload),
      matchDateTimeComponents: matchDateTimeComponents,
    );

    _logger.i(
      'Scheduled notification $id for $scheduledDate with match: $matchDateTimeComponents',
    );
  }

  Future<void> cancelNotification(int id) async {
    await _notificationsPlugin.cancel(id);
    _logger.i('Cancelled notification $id');
  }
}

final notificationServiceProvider =
    Provider<NotificationService>(NotificationService.new);

/// 通知权限状态 Provider
final notificationPermissionStatusProvider = AsyncNotifierProvider<
    NotificationPermissionStatusNotifier, NotificationPermissionStatus>(
  NotificationPermissionStatusNotifier.new,
);

class NotificationPermissionStatusNotifier
    extends AsyncNotifier<NotificationPermissionStatus> {
  @override
  Future<NotificationPermissionStatus> build() async {
    try {
      final notificationService = ref.read(notificationServiceProvider);
      return await notificationService.checkPermissionStatus();
    } catch (error, stackTrace) {
      Error.throwWithStackTrace(error, stackTrace);
    }
  }

  /// 刷新权限状态
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final notificationService = ref.read(notificationServiceProvider);
      return notificationService.checkPermissionStatus();
    });
  }

  /// 请求权限并刷新状态
  Future<bool> requestPermission() async {
    final notificationService = ref.read(notificationServiceProvider);
    final granted = await notificationService.requestPermission();
    await refresh();
    return granted;
  }
}
