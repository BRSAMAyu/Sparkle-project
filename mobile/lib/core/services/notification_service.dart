import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logger/logger.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

// Global navigator key to allow navigation without context from notifications
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

class NotificationService {
  final FlutterLocalNotificationsPlugin _notificationsPlugin =
      FlutterLocalNotificationsPlugin();
  final Logger _logger = Logger();

  NotificationService() {
    _initialize();
  }

  Future<void> _initialize() async {
    tz.initializeTimeZones();
    // Assuming Asia/Shanghai for default, but should ideally get from device
    // tz.setLocalLocation(tz.getLocation('Asia/Shanghai'));

    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher'); // Verify icon name

    // TODO: Add iOS settings
    const InitializationSettings initializationSettings =
        InitializationSettings(
      android: initializationSettingsAndroid,
    );

    await _notificationsPlugin.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: _onNotificationResponse,
      onDidReceiveBackgroundNotificationResponse: _onBackgroundNotificationResponse,
    );

    // Create Channel
    const AndroidNotificationChannel channel = AndroidNotificationChannel(
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
        
    _logger.i("NotificationService initialized");
  }

  // Static/Global callback for background handling if needed
  @pragma('vm:entry-point')
  static void _onBackgroundNotificationResponse(NotificationResponse details) {
    // Handle background actions (snooze, dismiss)
    print("Background notification action: ${details.actionId}");
  }

  void _onNotificationResponse(NotificationResponse details) {
    _logger.i("Notification action: ${details.actionId}, payload: ${details.payload}");
    
    if (details.payload != null) {
      try {
        final payload = jsonDecode(details.payload!);
        
        if (details.actionId == 'START_NOW') {
           // Navigate to Task Execution
           // Since we are inside a callback, we might need the context or router
           // We use the global navigatorKey context if available
           if (navigatorKey.currentContext != null) {
              final context = navigatorKey.currentContext!;
              // Parse taskId from payload
              final taskId = payload['taskId'];
              if (taskId != null) {
                GoRouter.of(context).pushNamed('taskExecution', pathParameters: {'id': taskId});
              }
           }
        } else if (details.actionId == 'SNOOZE') {
          // Handle Snooze API call
          _handleSnooze(payload);
        } else if (details.actionId == 'DISMISS') {
          // Handle Dismiss API call
          _handleDismiss(payload);
        }
      } catch (e) {
        _logger.e("Error parsing notification payload: $e");
      }
    }
  }
  
  void _handleSnooze(Map<String, dynamic> payload) {
    // TODO: Call API to snooze
    _logger.i("Snoozing notification: $payload");
  }

  void _handleDismiss(Map<String, dynamic> payload) {
    // TODO: Call API to dismiss
    _logger.i("Dismissing notification: $payload");
  }

  Future<void> showSmartPush({
    required String title,
    required String body,
    required Map<String, dynamic> payload,
  }) async {
    const AndroidNotificationDetails androidDetails =
        AndroidNotificationDetails(
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
          showsUserInterface: false,
          cancelNotification: true,
        ),
        AndroidNotificationAction(
          'DISMISS',
          '🔕 勿扰',
          showsUserInterface: false,
          cancelNotification: true,
        ),
      ],
    );

    const NotificationDetails notificationDetails =
        NotificationDetails(android: androidDetails);

    await _notificationsPlugin.show(
      DateTime.now().millisecond, // unique ID
      title,
      body,
      notificationDetails,
      payload: jsonEncode(payload),
    );
  }
}

final notificationServiceProvider = Provider<NotificationService>((ref) {
  return NotificationService();
});
