import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/community/presentation/screens/community_main_screen.dart';
import 'package:sparkle/features/community/presentation/screens/create_group_screen.dart';
import 'package:sparkle/features/community/presentation/screens/friends_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_detail_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_list_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_search_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_tasks_screen.dart';

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

class CommunityRoutes {
  static List<RouteBase> get routes => [
    GoRoute(
        path: '/community',
        builder: (context, state) => const CommunityMainScreen(),
      ),
      GoRoute(
        path: '/community/friends',
        name: 'friends',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const FriendsScreen(),
        ),
      ),
      GoRoute(
        path: '/community/groups',
        name: 'groups',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const GroupListScreen(),
        ),
      ),
      GoRoute(
        path: '/community/groups/search',
        name: 'groupSearch',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const GroupSearchScreen(),
        ),
      ),
      GoRoute(
        path: '/community/groups/create',
        name: 'createGroup',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const CreateGroupScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),
      GoRoute(
        path: '/community/groups/:id',
        name: 'groupDetail',
        pageBuilder: (context, state) {
          final groupId = state.pathParameters['id'];
          return _buildTransitionPage(
            state: state,
            child: GroupDetailScreen(groupId: groupId),
          );
        },
      ),
      GoRoute(
        path: '/community/groups/:id/tasks',
        name: 'groupTasks',
        pageBuilder: (context, state) {
          final groupId = state.pathParameters['id'];
          return _buildTransitionPage(
            state: state,
            child: GroupTasksScreen(groupId: groupId),
          );
        },
      ),
  ];
}
