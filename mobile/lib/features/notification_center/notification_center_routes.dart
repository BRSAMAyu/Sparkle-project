import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/notification_center/notification_center.dart';

class NotificationCenterRoutes {
  static List<RouteBase> get routes => [
        GoRoute(
          path: '/notification-center',
          name: 'notificationCenter',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const NotificationCenterScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: '/notification-analytics',
          name: 'notificationAnalytics',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const NotificationAnalyticsScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
      ];
}
