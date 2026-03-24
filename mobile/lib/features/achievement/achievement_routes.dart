import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
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
      pageBuilder: (context, state) => buildSparkleTransitionPage(
        state: state,
        motionToken: SparkleMotionToken.hero,
        child: SceneAudioScope(
          policy: ExperienceProfiles.celebrationRare.audioPolicy(
            trackOverride: BgmTrack.achievement,
          ),
          child: const AchievementListScreen(),
        ),
      ),
    ),
    GoRoute(
      path: streakDetails,
      pageBuilder: (context, state) => buildSparkleTransitionPage(
        state: state,
        motionToken: SparkleMotionToken.hero,
        child: SceneAudioScope(
          policy: ExperienceProfiles.celebrationRare.audioPolicy(
            trackOverride: BgmTrack.achievement,
          ),
          child: const StreakDetailsScreen(),
        ),
      ),
    ),
    GoRoute(
      path: map,
      pageBuilder: (context, state) => buildSparkleTransitionPage(
        state: state,
        motionToken: SparkleMotionToken.hero,
        child: SceneAudioScope(
          policy: ExperienceProfiles.celebrationRare.audioPolicy(
            trackOverride: BgmTrack.achievement,
          ),
          child: const AchievementMapScreen(),
        ),
      ),
    ),
    GoRoute(
      path: contract,
      pageBuilder: (context, state) => buildSparkleTransitionPage(
        state: state,
        motionToken: SparkleMotionToken.scene,
        type: SharedAxisTransitionType.scaled,
        child: SceneAudioScope(
          policy: ExperienceProfiles.celebrationRare.audioPolicy(
            trackOverride: BgmTrack.achievement,
          ),
          child: const AchievementContractScreen(),
        ),
      ),
    ),
    GoRoute(
      path: '$basePath/:id',
      pageBuilder: (context, state) {
        final id = state.pathParameters['id']!;
        return buildSparkleTransitionPage(
          state: state,
          motionToken: SparkleMotionToken.scene,
          type: SharedAxisTransitionType.scaled,
          child: SceneAudioScope(
            policy: ExperienceProfiles.celebrationRare.audioPolicy(
              trackOverride: BgmTrack.achievement,
            ),
            child: AchievementDetailScreen(achievementId: id),
          ),
        );
      },
    ),
  ];
}
