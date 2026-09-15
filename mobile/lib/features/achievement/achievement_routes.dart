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
import 'package:sparkle/features/achievement/presentation/screens/milestone_celebration_screen.dart';
import 'package:sparkle/features/achievement/presentation/screens/streak_details_screen.dart';

/// 成就系统路由配置
class AchievementRoutes {
  AchievementRoutes._();

  static const String basePath = '/achievements';
  static const String streakDetails = '$basePath/streak';
  static const String map = '$basePath/map';
  static const String contract = '$basePath/contract';
  static const String milestone = '$basePath/milestone';

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
      path: '$milestone/:milestoneId',
      name: 'achievementMilestone',
      pageBuilder: (context, state) {
        final milestoneId = state.pathParameters['milestoneId']!;
        final extra = state.extra;
        final payload = switch (extra) {
          final MilestoneCelebrationPayload milestonePayload =>
            milestonePayload,
          final Map<String, dynamic> rawPayload =>
            MilestoneCelebrationPayload.fromMap(rawPayload),
          _ => MilestoneCelebrationPayload.fromQueryParameters(
              milestoneId,
              state.uri.queryParameters,
            ),
        };
        return buildSparkleTransitionPage(
          state: state,
          motionToken: SparkleMotionToken.hero,
          child: SceneAudioScope(
            policy: ExperienceProfiles.celebrationRare.audioPolicy(
              trackOverride: BgmTrack.celebration,
            ),
            child: MilestoneCelebrationScreen(payload: payload),
          ),
        );
      },
    ),
    GoRoute(
      path: '$basePath/:id',
      name: 'achievementDetail',
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
