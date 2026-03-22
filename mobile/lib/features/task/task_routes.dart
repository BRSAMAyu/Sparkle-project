import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/task/presentation/screens/task_create_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_detail_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_execution_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_list_screen.dart';

class TaskRoutes {
  // Route constants for deep linking and navigation
  static const String home = '/tasks';
  static const String taskCreate = '/tasks/new';
  static const String taskDetail = '/tasks/:id';
  static const String taskExecution = '/tasks/:id/execute';

  static List<RouteBase> get routes => [
        // Task list (detail page, full-screen)
        GoRoute(
          path: home,
          name: 'tasks',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(
                track: BgmTrack.task,
              ),
              child: TaskListScreen(),
            ),
          ),
        ),
        // Task create (modal-like, full-screen)
        GoRoute(
          path: taskCreate,
          name: 'createTask',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(
                track: BgmTrack.task,
              ),
              child: TaskCreateScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        // Task detail (full-screen, uses root navigator)
        GoRoute(
          path: taskDetail,
          name: 'taskDetail',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            // id is a required path parameter, so it won't be null
            final taskId = state.pathParameters['id']!;
            return buildSparkleTransitionPage(
              state: state,
              child: SceneAudioScope(
                policy: const SceneAudioPolicy(
                  track: BgmTrack.task,
                ),
                child: TaskDetailScreen(taskId: taskId),
              ),
            );
          },
        ),
        // Task execution (modal-like, full-screen)
        GoRoute(
          path: taskExecution,
          name: 'taskExecution',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            child: SceneAudioScope(
              policy: ExperienceProfiles.focusImmersive.audioPolicy(
                trackOverride: BgmTrack.focusDeep,
                useSavedAmbient: true,
              ),
              child: const TaskExecutionScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
      ];
}
