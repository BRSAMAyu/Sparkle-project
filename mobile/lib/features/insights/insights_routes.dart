import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/insights/insights.dart';

class InsightsRoutes {
  static const String learningInsightsOverview = '/learning/insights';
  static const String learningInsightsForecast = '/learning/forecast';

  static String overviewLocation({String? initialPanel}) {
    if (initialPanel == null || initialPanel.isEmpty) {
      return learningInsightsOverview;
    }
    return '$learningInsightsOverview?initialPanel=${Uri.encodeQueryComponent(initialPanel)}';
  }

  static List<RouteBase> get routes => [
        GoRoute(
          path: learningInsightsOverview,
          name: 'learning-insights-overview',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            type: SharedAxisTransitionType.scaled,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.insights,
                atmosphereOverride: ExperienceAtmosphere.insightsMist,
              ),
              child: LearningInsightsOverviewScreen(
                initialPanel: state.uri.queryParameters['initialPanel'],
              ),
            ),
          ),
        ),
        GoRoute(
          path: learningInsightsForecast,
          name: 'learningForecast',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            type: SharedAxisTransitionType.scaled,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.insights,
                atmosphereOverride: ExperienceAtmosphere.insightsMist,
              ),
              child: const LearningForecastScreen(),
            ),
          ),
        ),
      ];
}
