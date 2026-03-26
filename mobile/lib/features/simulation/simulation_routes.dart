import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/simulation/presentation/screens/simulation_screen.dart';

class SimulationRoutes {
  static const String simulation = '/simulation';

  static List<RouteBase> get routes => [
        GoRoute(
          path: simulation,
          name: 'simulation',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: const SceneAudioPolicy(track: BgmTrack.insights),
              child: SimulationScreen(
                initialTopic: state.uri.queryParameters['topic'],
                initialScenarioKey: state.uri.queryParameters['scenario_key'],
              ),
            ),
          ),
        ),
      ];
}
