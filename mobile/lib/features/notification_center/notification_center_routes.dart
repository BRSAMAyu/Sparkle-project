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
        // NAV-IA P-3：/notification-analytics 已从路由表摘除（0 入边孤儿面，
        // 挂在路由表即可被任意深链触达的未审面）。屏与 provider 文件保留，
        // 处置背景见 docs/engineering/KNOWN_CODE_DEBT_LEDGER.md；重新挂载
        // 需产品裁决（如挂到 admin-operations 下）。
      ];
}
