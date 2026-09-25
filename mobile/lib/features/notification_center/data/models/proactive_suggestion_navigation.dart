import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';

/// P-03: 建议卡点击导航的解析结果。
///
/// [route] 是建议指向的正确页面（Goal 页优先，读侧 `goal_state.goal_id`，
/// 不误用 plan_id——F-7 判例）；[fallbackRoute] 是目标失效（离线/过期/已删除）
/// 时的可退回落点，复用 [RouteResilience] 既有兜底真源，不另建映射。
class SuggestionNavigation {
  const SuggestionNavigation({required this.route, required this.fallbackRoute});

  final String route;
  final String fallbackRoute;
}

/// 解析主动建议的点击导航目标；无任何可解析目标时返回 `null`
/// （调用方回退到详情弹窗，与既有通知行为一致）。
SuggestionNavigation? resolveSuggestionNavigation(
  UnifiedNotification notification,
) {
  final route = _resolveTargetRoute(notification);
  if (route == null) {
    return null;
  }
  return SuggestionNavigation(
    route: route,
    fallbackRoute: RouteResilience.fallbackRouteForExternalRoute(route),
  );
}

String? _resolveTargetRoute(UnifiedNotification notification) {
  // 引擎下发的 destination_route / deep_link 优先（comeback 真源已按
  // goal → plan → chat 组装）。
  final direct =
      (notification.metadata['destination_route'] ?? notification.metadata['deep_link'])
          ?.toString()
          .trim();
  if (direct != null && direct.isNotEmpty) {
    return direct;
  }

  // 客户端兜底：goal_state.goal_id 存在 → Goal 详情页。
  final goalState = notification.metadata['goal_state'];
  if (goalState is Map) {
    final goalId = goalState['goal_id']?.toString().trim();
    if (goalId != null && goalId.isNotEmpty) {
      return '/goals/$goalId';
    }
  }

  final planId = notification.planId;
  if (planId != null && planId.isNotEmpty) {
    return '/plans/$planId';
  }

  return null;
}
