import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/notification_service.dart';
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
  // Route constants for deep linking and navigation
  static const String home = '/community';
  static const String friends = '/community/friends';
  static const String groups = '/community/groups';
  static const String groupsSearch = '/community/groups/search';
  static const String groupsCreate = '/community/groups/create';
  static const String groupDetail = '/community/groups/:id';
  static const String groupTasks = '/community/groups/:id/tasks';

  static List<RouteBase> get routes => [
    // Friends list (detail page, full-screen)
    GoRoute(
        path: friends,
        name: 'friends',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const FriendsScreen(),
        ),
      ),
    // Group list (detail page, full-screen)
    GoRoute(
        path: groups,
        name: 'groups',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const GroupListScreen(),
        ),
      ),
    // Group search (detail page, full-screen)
    GoRoute(
        path: groupsSearch,
        name: 'groupSearch',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const GroupSearchScreen(),
        ),
      ),
    // Create group (modal-like, full-screen)
    GoRoute(
        path: groupsCreate,
        name: 'createGroup',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const CreateGroupScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),
    // Group detail (full-screen, uses root navigator)
    GoRoute(
        path: groupDetail,
        name: 'groupDetail',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) {
          final groupId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: GroupDetailScreen(groupId: groupId),
          );
        },
      ),
    // Group tasks (full-screen, uses root navigator)
    GoRoute(
        path: groupTasks,
        name: 'groupTasks',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) {
          final groupId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: GroupTasksScreen(groupId: groupId),
          );
        },
      ),
  ];
}
