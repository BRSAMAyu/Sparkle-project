import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/task/presentation/screens/task_create_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_detail_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_execution_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_list_screen.dart';

Page<dynamic> _buildTransitionPage({
  required GoRouterState state,
  required Widget child,
  SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
}) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionsBuilder: (context, animation, secondaryAnimation, child) =>
          SharedAxisTransition(
        animation: animation,
        secondaryAnimation: secondaryAnimation,
        transitionType: type,
        child: child,
      ),
    );

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
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(
                track: BgmTrack.task,
                priority: BgmPriority.route,
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
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const SceneAudioScope(
              policy: SceneAudioPolicy(
                track: BgmTrack.task,
                priority: BgmPriority.route,
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
            return _buildTransitionPage(
              state: state,
              child: SceneAudioScope(
                policy: SceneAudioPolicy(
                  track: BgmTrack.task,
                  priority: BgmPriority.route,
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
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: SceneAudioScope(
              policy: ExperienceProfiles.focusImmersive.audioPolicy(
                trackOverride: BgmTrack.focusDeep,
                priority: BgmPriority.route,
                useSavedAmbient: true,
              ),
              child: TaskExecutionScreen(),
            ),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
      ];
}
