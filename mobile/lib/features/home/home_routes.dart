import 'package:go_router/go_router.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/home/presentation/screens/weather_guide_screen.dart';
import 'package:sparkle/features/openclaw/openclaw_routes.dart';

class HomeRoutes {
  // Route constants for deep linking and navigation
  static const String home = '/home';
  static const String openClawHub = OpenClawRoutes.hub;
  static const String notifications = '/notifications';
  static const String weatherGuide = '/weather';

  static List<RouteBase> get routes => [
        // Note: /home is handled by StatefulShellRoute in routes.dart.
        // Legacy route for backward compatibility (redirected):
        // /notifications -> /notification-center（NAV-IA P-3 通知落点统一，
        // redirect 模式照抄 chat_routes legacy redirect；老深链/老入口可达
        // 且与全站通知入口落同一屏）。
        GoRoute(
          path: notifications,
          name: 'notifications',
          redirect: (context, state) {
            final params = state.uri.queryParameters;
            return Uri(path: '/notification-center', queryParameters: params)
                .toString();
          },
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
