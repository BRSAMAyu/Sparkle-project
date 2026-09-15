import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/reflection/presentation/screens/reflection_summary_screen.dart';

class ReflectionRoutes {
  static const String summary = '/reflection/summary';

  static List<RouteBase> get routes => [
        GoRoute(
          path: summary,
          name: 'reflectionSummary',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: const ReflectionSummaryScreen(),
          ),
        ),
      ];
}
