import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/chat/presentation/screens/group_chat_screen.dart';
import 'package:sparkle/features/chat/presentation/screens/private_chat_screen.dart';

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

Map<String, String> _mergeQueryWithDefaultName(
  GoRouterState state,
  String defaultName,
) {
  final params = Map<String, String>.from(state.uri.queryParameters);
  final name = params['name'];
  if (name == null || name.isEmpty) {
    params['name'] = defaultName;
  }
  return params;
}

class ChatRoutes {
  // New unified chat routes
  static const String chat = '/chat';
  static const String groupChat = '/chat/group/:id';
  static const String privateChat = '/chat/private/:id';

  // Legacy route constants for backward compatibility (redirected)
  static const String legacyGroupChat = '/community/chat/group/:id';
  static const String legacyPrivateChat = '/community/chat/private/:id';
  static const String legacyGroupsChat = '/community/groups/:id/chat';
  static const String legacyFriendsChat = '/community/friends/:id/chat';

  static List<RouteBase> get routes => [
        // Group chat (full-screen, uses root navigator)
        GoRoute(
          path: groupChat,
          name: 'groupChat',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final groupId = state.pathParameters['id']!;
            return _buildTransitionPage(
              state: state,
              child: GroupChatScreen(groupId: groupId),
            );
          },
        ),
        // Private chat (full-screen, uses root navigator)
        GoRoute(
          path: privateChat,
          name: 'privateChat',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final friendId = state.pathParameters['id']!;
            final friendName = state.uri.queryParameters['name'];
            return _buildTransitionPage(
              state: state,
              child: PrivateChatScreen(
                friendId: friendId,
                friendName: friendName,
              ),
            );
          },
        ),
        // ========== Legacy redirect routes for backward compatibility ==========
        // /community/chat/group/:id -> /chat/group/:id
        GoRoute(
          path: legacyGroupChat,
          redirect: (context, state) {
            final id = state.pathParameters['id'];
            final params = _mergeQueryWithDefaultName(state, '群聊');
            return Uri(path: '/chat/group/$id', queryParameters: params).toString();
          },
        ),
        // /community/chat/private/:id -> /chat/private/:id
        GoRoute(
          path: legacyPrivateChat,
          redirect: (context, state) {
            final id = state.pathParameters['id'];
            final params = _mergeQueryWithDefaultName(state, '好友');
            return Uri(path: '/chat/private/$id', queryParameters: params).toString();
          },
        ),
        // /community/groups/:id/chat -> /chat/group/:id
        GoRoute(
          path: legacyGroupsChat,
          redirect: (context, state) {
            final id = state.pathParameters['id'];
            final params = _mergeQueryWithDefaultName(state, '群聊');
            return Uri(path: '/chat/group/$id', queryParameters: params).toString();
          },
        ),
        // /community/friends/:id/chat -> /chat/private/:id
        GoRoute(
          path: legacyFriendsChat,
          redirect: (context, state) {
            final id = state.pathParameters['id'];
            final params = _mergeQueryWithDefaultName(state, '好友');
            return Uri(path: '/chat/private/$id', queryParameters: params).toString();
          },
        ),
      ];
}
