import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/learning/data/learning_journey_models.dart';
import 'package:sparkle/features/learning/presentation/screens/learning_journey_screen.dart';

/// 学习旅程路由（V4-U10，只增不改——不触碰既有五 Tab 路由合同）。
///
/// 入口契约：从目标进入必须携带 goalId + goalTitle 查询参数（
/// [LearningJourneyContext.fromLaunch] 在缺参时抛 ArgumentError——
/// 「不会从目标跳入无上下文的工具空页」在路由面机制化）。
class LearningJourneyRoutes {
  static const String journey = '/learning/journey';

  static String journeyUri({required String goalId, required String goalTitle}) =>
      '/learning/journey?goalId=${Uri.encodeComponent(goalId)}'
      '&goalTitle=${Uri.encodeComponent(goalTitle)}';

  static List<RouteBase> get routes => [
        GoRoute(
          path: journey,
          name: 'learningJourney',
          pageBuilder: (BuildContext context, GoRouterState state) {
            final query = state.uri.queryParameters;
            final journeyContext = LearningJourneyContext.fromLaunch(
              goalTaskId: query['goalId'],
              goalTitle: query['goalTitle'],
            );
            return buildSparkleTransitionPage(
              state: state,
              child: LearningJourneyScreen(journeyContext: journeyContext),
            );
          },
        ),
      ];
}
