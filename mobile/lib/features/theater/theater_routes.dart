import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/theater/presentation/screens/knowledge_theater_screen.dart';

class TheaterRoutes {
  static const String theater = '/theater';

  static List<RouteBase> get routes => <RouteBase>[
        GoRoute(
          path: theater,
          name: 'theater',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: const SceneAudioPolicy(track: BgmTrack.insights),
              child: KnowledgeTheaterScreen(
                initialTopic: state.uri.queryParameters['topic'],
                initialTargetNodeId:
                    state.uri.queryParameters['target_node_id'],
                initialPredictionId: state.uri.queryParameters['prediction_id'],
                initialRouteId: state.uri.queryParameters['route_id'],
                initialSourceChatSessionId:
                    state.uri.queryParameters['source_chat_session_id'],
                initialSimulationSessionId:
                    state.uri.queryParameters['simulation_session_id'],
              ),
            ),
          ),
        ),
      ];
}
