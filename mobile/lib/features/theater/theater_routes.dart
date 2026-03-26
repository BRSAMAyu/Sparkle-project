import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/theater/presentation/screens/knowledge_theater_screen.dart';

class TheaterRoutes {
  static const String theater = '/theater';

  static List<RouteBase> get routes => <RouteBase>[
        GoRoute(
          path: theater,
          name: 'theater',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: KnowledgeTheaterScreen(
              initialTopic: state.uri.queryParameters['topic'],
              initialTargetNodeId: state.uri.queryParameters['target_node_id'],
            ),
          ),
        ),
      ];
}
