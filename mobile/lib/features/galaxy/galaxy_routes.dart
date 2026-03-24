import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/knowledge/presentation/screens/knowledge_detail_screen.dart';

class GalaxyRoutes {
  // Route constants for deep linking and navigation
  static const String home = '/galaxy';
  static const String knowledgeDetail = '/galaxy/node/:id';

  static List<RouteBase> get routes => [
        // Knowledge detail (full-screen, uses root navigator)
        GoRoute(
          path: knowledgeDetail,
          name: 'knowledgeDetail',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final nodeId = state.pathParameters['id']!;
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              type: SharedAxisTransitionType.scaled,
              child: SceneAudioScope(
                policy: ExperienceProfiles.focusImmersive.audioPolicy(
                  trackOverride: BgmTrack.galaxy,
                  atmosphereOverride: ExperienceAtmosphere.galaxyDrift,
                ),
                child: KnowledgeDetailScreen(nodeId: nodeId),
              ),
            );
          },
        ),
      ];
}
