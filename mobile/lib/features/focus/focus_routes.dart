import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/focus/presentation/screens/focus_main_screen.dart';
import 'package:sparkle/features/focus/presentation/screens/mindfulness_mode_screen.dart';

class FocusRoutes {
  // Route constants for deep linking and navigation
  static const String home = '/focus';
  static const String mindfulness = '/focus/mindfulness/:id';

  static List<RouteBase> get routes => [
        // Focus main screen (detail page, full-screen)
        GoRoute(
          path: home,
          name: 'focus',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: SceneAudioScope(
              policy: ExperienceProfiles.focusImmersive.audioPolicy(
                trackOverride: BgmTrack.focusStart,
              ),
              child: const FocusMainScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        // Mindfulness mode (modal-like, full-screen)
        GoRoute(
          path: mindfulness,
          name: 'mindfulness',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            // id is a required path parameter, so it won't be null
            final taskId = state.pathParameters['id']!;
            final interventionId = state.uri.queryParameters['intervention_id'];
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              child: SceneAudioScope(
                policy: ExperienceProfiles.focusImmersive.audioPolicy(
                  trackOverride: BgmTrack.focusDeep,
                  useSavedAmbient: true,
                ),
                child: MindfulnessModeScreen(
                  taskId: taskId,
                  interventionId: interventionId,
                ),
              ),
              type: SharedAxisTransitionType.scaled,
            );
          },
        ),
      ];
}
