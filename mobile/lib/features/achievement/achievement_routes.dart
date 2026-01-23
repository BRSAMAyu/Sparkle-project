import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/achievement/presentation/screens/achievement_detail_screen.dart';
import 'package:sparkle/features/achievement/presentation/screens/achievement_list_screen.dart';

/// 成就系统路由配置
class AchievementRoutes {
  AchievementRoutes._();

  static const String basePath = '/achievements';

  static List<RouteBase> routes = [
    GoRoute(
      path: basePath,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const AchievementListScreen(),
      ),
    ),
    GoRoute(
      path: '$basePath/:id',
      pageBuilder: (context, state) {
        final id = state.pathParameters['id']!;
        return MaterialPage<void>(
          key: state.pageKey,
          child: AchievementDetailScreen(achievementId: id),
        );
      },
    ),
  ];
}
