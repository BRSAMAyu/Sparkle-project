import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/bgm_scope.dart';
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
        child: const BgmScope(
          track: BgmTrack.achievement,
          child: AchievementListScreen(),
        ),
      ),
    ),
    GoRoute(
      path: streakDetails,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const BgmScope(
          track: BgmTrack.achievement,
          child: StreakDetailsScreen(),
        ),
      ),
    ),
    GoRoute(
      path: map,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const BgmScope(
          track: BgmTrack.achievement,
          child: AchievementMapScreen(),
        ),
      ),
    ),
    GoRoute(
      path: contract,
      pageBuilder: (context, state) => MaterialPage<void>(
        key: state.pageKey,
        child: const BgmScope(
          track: BgmTrack.achievement,
          child: AchievementContractScreen(),
        ),
      ),
    ),
    GoRoute(
      path: '$basePath/:id',
      pageBuilder: (context, state) {
        final id = state.pathParameters['id']!;
        return MaterialPage<void>(
          key: state.pageKey,
          child: BgmScope(
            track: BgmTrack.achievement,
            child: AchievementDetailScreen(achievementId: id),
          ),
        );
      },
    ),
  ];
}
