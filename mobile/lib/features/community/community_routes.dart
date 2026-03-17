import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/community/presentation/screens/accountability_screen.dart';
import 'package:sparkle/features/community/presentation/screens/accountability_detail_screen.dart';
import 'package:sparkle/features/community/presentation/screens/create_group_screen.dart';
import 'package:sparkle/features/community/presentation/screens/create_post_screen.dart';
import 'package:sparkle/features/community/presentation/screens/favorites_screen.dart';
import 'package:sparkle/features/community/presentation/screens/friends_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_detail_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_discover_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_files_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_list_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_members_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_moderation_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_search_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_tasks_screen.dart';
import 'package:sparkle/features/community/presentation/screens/friend_profile_screen.dart';
import 'package:sparkle/features/community/presentation/screens/user_search_screen.dart';

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
  static const String friendsDiscover = '/community/friends/discover';
  static const String userSearch = '/community/users/search';
  static const String groups = '/community/groups';
  static const String groupsSearch = '/community/groups/search';
  static const String groupsDiscover = '/community/groups/discover';
  static const String groupsCreate = '/community/groups/create';
  static const String postsCreate = '/community/posts/create';
  static const String groupDetail = '/community/groups/:id';
  static const String groupTasks = '/community/groups/:id/tasks';
  static const String groupMembers = '/community/groups/:id/members';
  static const String groupFiles = '/community/groups/:id/files';
  static const String groupModeration = '/community/groups/:id/moderation';
  static const String userProfile = '/community/users/:id';
  static const String favorites = '/community/favorites';
  static const String accountability = '/community/accountability';
  static const String accountabilityDetail =
      '/community/accountability/:id';

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
        // Friends discover / recommendations (detail page, full-screen)
        GoRoute(
          path: friendsDiscover,
          name: 'friendsDiscover',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const FriendsScreen(),
          ),
        ),
        // User search (detail page, full-screen)
        GoRoute(
          path: userSearch,
          name: 'userSearch',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const UserSearchScreen(),
          ),
        ),
        // User profile (must be AFTER /community/users/search to avoid :id capturing "search")
        GoRoute(
          path: userProfile,
          name: 'userProfile',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final userId = state.pathParameters['id']!;
            final name = state.uri.queryParameters['name'];
            return _buildTransitionPage(
              state: state,
              child: FriendProfileScreen(userId: userId, displayName: name),
            );
          },
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
        // Group discover (detail page, full-screen)
        GoRoute(
          path: groupsDiscover,
          name: 'groupDiscover',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const GroupDiscoverScreen(),
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
        GoRoute(
          path: postsCreate,
          name: 'createPost',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const CreatePostScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        // Group detail (full-screen, uses root navigator)
        GoRoute(
          path: groupDetail,
          name: 'groupDetail',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            // id is required in path, so it won't be null
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
            // id is required in path, so it won't be null
            final groupId = state.pathParameters['id']!;
            return _buildTransitionPage(
              state: state,
              child: GroupTasksScreen(groupId: groupId),
            );
          },
        ),
        // Group members (full-screen, uses root navigator)
        GoRoute(
          path: groupMembers,
          name: 'groupMembers',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            // id is required in path, so it won't be null
            final groupId = state.pathParameters['id']!;
            final groupName = state.uri.queryParameters['name'] ?? '';
            return _buildTransitionPage(
              state: state,
              child: GroupMembersScreen(
                groupId: groupId,
                groupName: groupName,
              ),
            );
          },
        ),
        // Group files (full-screen, uses root navigator)
        GoRoute(
          path: groupFiles,
          name: 'groupFiles',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final groupId = state.pathParameters['id']!;
            return _buildTransitionPage(
              state: state,
              child: GroupFilesScreen(groupId: groupId),
            );
          },
        ),
        // Group moderation (admin only)
        GoRoute(
          path: groupModeration,
          name: 'groupModeration',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final groupId = state.pathParameters['id']!;
            return _buildTransitionPage(
              state: state,
              child: GroupModerationScreen(groupId: groupId),
            );
          },
        ),
        // Message favorites
        GoRoute(
          path: favorites,
          name: 'favorites',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const FavoritesScreen(),
          ),
        ),
        // Accountability partner list
        GoRoute(
          path: accountability,
          name: 'accountability',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const AccountabilityScreen(),
          ),
        ),
        // Accountability detail
        GoRoute(
          path: accountabilityDetail,
          name: 'accountabilityDetail',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final id = state.pathParameters['id']!;
            return _buildTransitionPage(
              state: state,
              child: AccountabilityDetailScreen(partnershipId: id),
            );
          },
        ),
      ];
}
