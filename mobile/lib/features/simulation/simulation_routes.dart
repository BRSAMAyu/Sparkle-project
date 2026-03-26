import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/simulation/presentation/screens/simulation_screen.dart';

class SimulationRoutes {
  static const String simulation = '/simulation';

  static List<RouteBase> get routes => [
        GoRoute(
          path: simulation,
          name: 'simulation',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const SimulationScreen(),
          ),
        ),
      ];
}
