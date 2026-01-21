import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
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
  static const String taskList = '/tasks';
  static const String taskCreate = '/tasks/new';
  static const String taskDetail = '/tasks/:id';
  static const String taskExecution = '/tasks/:id/execute';

  static List<RouteBase> get routes => [
        GoRoute(
          path: taskList,
          name: 'tasks',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const TaskListScreen(),
          ),
        ),
        GoRoute(
          path: taskCreate,
          name: 'createTask',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const TaskCreateScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: taskDetail,
          name: 'taskDetail',
          pageBuilder: (context, state) {
            // id is a required path parameter, so it won't be null
            final taskId = state.pathParameters['id']!;
            return _buildTransitionPage(
              state: state,
              child: TaskDetailScreen(taskId: taskId),
            );
          },
        ),
        GoRoute(
          path: taskExecution,
          name: 'taskExecution',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const TaskExecutionScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
      ];
}
