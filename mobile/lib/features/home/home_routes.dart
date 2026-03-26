import 'package:go_router/go_router.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/home/presentation/screens/notification_list_screen.dart';
import 'package:sparkle/features/home/presentation/screens/weather_guide_screen.dart';

class HomeRoutes {
  // Route constants for deep linking and navigation
  static const String home = '/home';
  static const String notifications = '/notifications';
  static const String weatherGuide = '/weather';

  static List<RouteBase> get routes => [
        // Note: /home is handled by StatefulShellRoute in routes.dart.
        GoRoute(
          path: notifications,
          name: 'notifications',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.dashboard,
              ),
              child: const NotificationListScreen(),
            ),
          ),
        ),
        GoRoute(
          path: weatherGuide,
          name: 'weather-guide',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.dashboardProductive.audioPolicy(
                trackOverride: BgmTrack.dashboard,
              ),
              child: const WeatherGuideScreen(),
            ),
          ),
        ),
      ];
}
