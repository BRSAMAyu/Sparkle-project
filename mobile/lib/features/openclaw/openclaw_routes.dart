import 'package:go_router/go_router.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/home/presentation/screens/openclaw_hub_screen.dart';
import 'package:sparkle/features/openclaw/presentation/screens/openclaw_screen.dart';

class OpenClawRoutes {
  const OpenClawRoutes._();

  static const String hub = '/openclaw';

  static List<RouteBase> get routes => [
        GoRoute(
          path: hub,
          name: 'openclaw-hub',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.dashboard,
              ),
              child: OpenClawScreen(
                initialSection: OpenClawHubSection.fromQuery(
                  state.uri.queryParameters['section'],
                ),
              ),
            ),
          ),
        ),
      ];
}
