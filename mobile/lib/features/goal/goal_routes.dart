import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/goal/presentation/pages/goal_detail_page.dart';

class GoalRoutes {
  GoalRoutes._();

  static const String detail = '/goals/:goalId';

  static String detailLocation(String goalId) => '/goals/$goalId';

  static List<RouteBase> get routes => [
        GoRoute(
          path: detail,
          name: 'goalDetail',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            type: SharedAxisTransitionType.scaled,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.plan,
              ),
              child: GoalDetailPage(
                goalId: state.pathParameters['goalId']!,
              ),
            ),
          ),
        ),
      ];
}
