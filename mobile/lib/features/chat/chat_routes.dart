import 'package:animations/animations.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/widgets/scene_audio_scope.dart';
import 'package:sparkle/features/chat/presentation/screens/chat_settings_screen.dart';
import 'package:sparkle/features/chat/presentation/screens/group_chat_screen.dart';
import 'package:sparkle/features/chat/presentation/screens/private_chat_screen.dart';

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
  static const String chatSettings = '/chat/settings';
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
          path: chatSettings,
          name: 'chatSettings',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            motionToken: SparkleMotionToken.scene,
            type: SharedAxisTransitionType.scaled,
            child: SceneAudioScope(
              policy: ExperienceProfiles.assistantFlow.audioPolicy(
                trackOverride: BgmTrack.chat,
              ),
              child: const ChatSettingsScreen(),
            ),
          ),
        ),
        GoRoute(
          path: groupChat,
          name: 'groupChat',
          parentNavigatorKey: navigatorKey,
          pageBuilder: (context, state) {
            final groupId = state.pathParameters['id']!;
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              type: SharedAxisTransitionType.scaled,
              child: SceneAudioScope(
                policy: ExperienceProfiles.assistantFlow.audioPolicy(
                  trackOverride: BgmTrack.chat,
                ),
                child: GroupChatScreen(groupId: groupId),
              ),
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
            return buildSparkleTransitionPage(
              state: state,
              motionToken: SparkleMotionToken.scene,
              type: SharedAxisTransitionType.scaled,
              child: SceneAudioScope(
                policy: ExperienceProfiles.assistantFlow.audioPolicy(
                  trackOverride: BgmTrack.chat,
                ),
                child: PrivateChatScreen(
                  friendId: friendId,
                  friendName: friendName,
                ),
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
            final params = _mergeQueryWithDefaultName(
              state,
              I18nService.instance.l10n.chatDefaultGroupName,
            );
            return Uri(path: '/chat/group/$id', queryParameters: params)
                .toString();
          },
        ),
        // /community/chat/private/:id -> /chat/private/:id
        GoRoute(
          path: legacyPrivateChat,
          redirect: (context, state) {
            final id = state.pathParameters['id'];
            final params = _mergeQueryWithDefaultName(
              state,
              I18nService.instance.l10n.chatDefaultFriendName,
            );
            return Uri(path: '/chat/private/$id', queryParameters: params)
                .toString();
          },
        ),
        // /community/groups/:id/chat -> /chat/group/:id
        GoRoute(
          path: legacyGroupsChat,
          redirect: (context, state) {
            final id = state.pathParameters['id'];
            final params = _mergeQueryWithDefaultName(
              state,
              I18nService.instance.l10n.chatDefaultGroupName,
            );
            return Uri(path: '/chat/group/$id', queryParameters: params)
                .toString();
          },
        ),
        // /community/friends/:id/chat -> /chat/private/:id
        GoRoute(
          path: legacyFriendsChat,
          redirect: (context, state) {
            final id = state.pathParameters['id'];
            final params = _mergeQueryWithDefaultName(
              state,
              I18nService.instance.l10n.chatDefaultFriendName,
            );
            return Uri(path: '/chat/private/$id', queryParameters: params)
                .toString();
          },
        ),
      ];
}
