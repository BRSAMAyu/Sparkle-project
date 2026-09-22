import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/leaderboard/presentation/screens/self_anchor_screen.dart';

/// Leaderboard-domain routes。
///
/// D-COMM-1 裁决：全站综合榜保持 D17 隐藏不建路由；本文件只挂按裁决
/// 路由的「自我锚」视图（`/leaderboards/self-anchor`）。
class LeaderboardRoutes {
  LeaderboardRoutes._();

  /// 自我 7 日锚视图（对应后端 `GET /leaderboards/self-anchor`）。
  static const String selfAnchor = '/leaderboards/self-anchor';

  static List<RouteBase> routes = [
    GoRoute(
      path: selfAnchor,
      name: 'selfAnchor',
      pageBuilder: (context, state) => buildSparkleTransitionPage(
        state: state,
        child: const SelfAnchorScreen(),
      ),
    ),
  ];
}
