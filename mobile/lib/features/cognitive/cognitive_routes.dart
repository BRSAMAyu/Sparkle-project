import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/cognitive/cognitive.dart';

class CognitiveRoutes {
  static List<RouteBase> get routes => [
        GoRoute(
          path: '/cognitive/patterns',
          name: 'patternList',
          pageBuilder: (context, state) {
            final highlightId = state.uri.queryParameters['highlight'];
            return buildSparkleTransitionPage(
              state: state,
              child: PatternListScreen(highlightId: highlightId),
            );
          },
        ),
        GoRoute(
          path: '/curiosity-capsule',
          name: 'curiosityCapsule',
          pageBuilder: (context, state) {
            final highlightId = state.uri.queryParameters['highlight'];
            return buildSparkleTransitionPage(
              state: state,
              child: CuriosityCapsuleScreen(highlightId: highlightId),
            );
          },
        ),
      ];
}
