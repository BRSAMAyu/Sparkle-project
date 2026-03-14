import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:timezone/data/latest_all.dart' as tz_data;
import 'package:timezone/timezone.dart' as tz;

// Global navigator key to allow navigation without context from notifications
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

class NotificationService {
  NotificationService(this._ref) {
    unawaited(_initialize());
  }
  final Ref _ref;
  final FlutterLocalNotificationsPlugin _notificationsPlugin =
      FlutterLocalNotificationsPlugin();
  final Logger _logger = Logger();

  Future<void> _initialize() async {
    tz_data.initializeTimeZones();
    // Assuming Asia/Shanghai for default, but should ideally get from device
    // tz.setLocalLocation(tz.getLocation('Asia/Shanghai'));

    const initializationSettingsAndroid = AndroidInitializationSettings(
        '@mipmap/ic_launcher',); // Verify icon name

    const initializationSettingsDarwin = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const initializationSettings = InitializationSettings(
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

    // Request permissions (Android 13+)
    await _notificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();

    await _notificationsPlugin
        .resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>()
        ?.requestPermissions(
          alert: true,
          badge: true,
          sound: true,
        );

    await _notificationsPlugin
        .resolvePlatformSpecificImplementation<
            MacOSFlutterLocalNotificationsPlugin>()
        ?.requestPermissions(
          alert: true,
          badge: true,
          sound: true,
        );

    _logger.i('NotificationService initialized');
  }

  // Static/Global callback for background handling if needed
  @pragma('vm:entry-point')
  static void _onBackgroundNotificationResponse(NotificationResponse details) {
    // Handle background actions (snooze, dismiss)
    debugPrint('Background notification action: ${details.actionId}');
  }

  void _onNotificationResponse(NotificationResponse details) {
    _logger.i(
        'Notification action: ${details.actionId}, payload: ${details.payload}',);

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

        if (actionId == 'START_NOW') {
          // Navigate to Task Execution
          // Since we are inside a callback, we might need the context or router
          // We use the global navigatorKey context if available
          final context = navigatorKey.currentContext;
          if (context != null) {
            // Parse taskId from payload
            final taskId = payload['taskId'] as String?;
            if (taskId != null) {
              unawaited(GoRouter.of(context)
                  .pushNamed('taskExecution', pathParameters: {'id': taskId}),);
            }
          }
        } else if (actionId == 'SNOOZE') {
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
    // TODO: Call API to snooze
    _logger.i('Snoozing notification: $payload');
  }

  void _handleDismiss(Map<String, dynamic> payload) {
    // TODO: Call API to dismiss
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

    const notificationDetails = NotificationDetails(android: androidDetails);

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
        'Scheduled notification $id for $scheduledDate with match: $matchDateTimeComponents',);
  }

  Future<void> cancelNotification(int id) async {
    await _notificationsPlugin.cancel(id);
    _logger.i('Cancelled notification $id');
  }
}

final notificationServiceProvider =
    Provider<NotificationService>((ref) => NotificationService(ref));
