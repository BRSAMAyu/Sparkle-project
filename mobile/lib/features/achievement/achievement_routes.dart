import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/achievement/presentation/screens/achievement_contract_screen.dart';
import 'package:sparkle/features/achievement/presentation/screens/achievement_detail_screen.dart';
import 'package:sparkle/features/achievement/presentation/screens/achievement_list_screen.dart';
import 'package:sparkle/features/achievement/presentation/screens/achievement_map_screen.dart';
import 'package:sparkle/features/achievement/presentation/screens/streak_details_screen.dart';

/// 成就系统路由配置
class AchievementRoutes {
  AchievementRoutes._();

  static const String basePath = '/achievements';
  static const String streakDetails = '$basePath/streak';
  static const String map = '$basePath/map';
  static const String contract = '$basePath/contract';

  static List<RouteBase> routes = [
    GoRoute(
      path: basePath,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const AchievementListScreen(),
      ),
    ),
    GoRoute(
      path: streakDetails,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const StreakDetailsScreen(),
      ),
    ),
    GoRoute(
      path: map,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const AchievementMapScreen(),
      ),
    ),
    GoRoute(
      path: contract,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const AchievementContractScreen(),
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
