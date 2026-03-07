import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/home/presentation/screens/notification_list_screen.dart';

class HomeRoutes {
  // Route constants for deep linking and navigation
  static const String home = '/home';
  static const String notifications = '/notifications';

  static List<RouteBase> get routes => [
        // Note: /home is handled by StatefulShellRoute in routes.dart.
        GoRoute(
          path: notifications,
          name: 'notifications',
          pageBuilder: (context, state) => MaterialPage<void>(
            key: state.pageKey,
            child: const NotificationListScreen(),
          ),
        ),
      ];
}
