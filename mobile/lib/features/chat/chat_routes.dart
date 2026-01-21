import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/chat/presentation/screens/chat_screen.dart';
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

class ChatRoutes {
  static const String chat = '/chat';
  static const String communityGroupChat = '/community/chat/group/:id';
  static const String communityPrivateChat = '/community/chat/private/:id';
  static const String groupChat = '/community/groups/:id/chat';
  static const String privateChat = '/community/friends/:id/chat';

  static List<RouteBase> get routes => [
        GoRoute(
          path: chat,
          name: 'chat',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const ChatScreen(),
          ),
        ),
        GoRoute(
          path: communityGroupChat,
          builder: (context, state) => GroupChatScreen(
            groupId: state.pathParameters['id']!,
          ),
        ),
        GoRoute(
          path: communityPrivateChat,
          builder: (context, state) => PrivateChatScreen(
            friendId: state.pathParameters['id']!,
            friendName: state.uri.queryParameters['name'],
          ),
        ),
        GoRoute(
          path: groupChat,
          name: 'groupChat',
          pageBuilder: (context, state) {
            final groupId = state.pathParameters['id']!;
            return _buildTransitionPage(
              state: state,
              child: GroupChatScreen(groupId: groupId),
            );
          },
        ),
        GoRoute(
          path: privateChat,
          name: 'privateChat',
          pageBuilder: (context, state) {
            final friendId = state.pathParameters['id']!;
            final friendName = state.uri.queryParameters['name'] ?? 'Chat';
            return _buildTransitionPage(
              state: state,
              child: PrivateChatScreen(
                friendId: friendId,
                friendName: friendName,
              ),
            );
          },
        ),
      ];
}
