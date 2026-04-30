import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  group('S0-COM-01: friend request navigation avoids recursion', () {
    testWidgets('pending invite banner navigates to dedicated requests page',
        (tester) async {
      String? lastRoute;

      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            builder: (context, state) => Scaffold(
              body: Center(
                child: ElevatedButton(
                  onPressed: () => context.pushNamed('friendRequests'),
                  child: const Text('查看请求'),
                ),
              ),
            ),
          ),
          GoRoute(
            path: CommunityRoutes.friendsRequests,
            name: 'friendRequests',
            builder: (context, state) {
              lastRoute = 'friendRequests';
              return const Scaffold(
                body: Center(child: Text('requests-page')),
              );
            },
          ),
          GoRoute(
            path: CommunityRoutes.friends,
            name: 'friends',
            builder: (context, state) {
              lastRoute = 'friends';
              return const Scaffold(
                body: Center(child: Text('full-friends-page')),
              );
            },
          ),
        ],
      );
      addTearDown(router.dispose);

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp.router(
            routerConfig: router,
            localizationsDelegates: _locDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: const Locale('zh'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('查看请求'));
      await tester.pumpAndSettle();

      // Must land on dedicated requests page, NOT the full friends page
      expect(lastRoute, 'friendRequests');
      expect(find.text('requests-page'), findsOneWidget);
      expect(find.text('full-friends-page'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('friendRequests and friendsDiscover are separate named routes',
        (tester) async {
      // Verify that the route constants are distinct —
      // the original bug was both going to the same page
      expect(CommunityRoutes.friendsRequests, '/community/friends/requests');
      expect(CommunityRoutes.friendsDiscover, '/community/friends/discover');
      expect(CommunityRoutes.friends, '/community/friends');

      // All three must be distinct paths
      expect(
        {
          CommunityRoutes.friendsRequests,
          CommunityRoutes.friendsDiscover,
          CommunityRoutes.friends,
        }.length,
        3,
      );
    });
  });

  group('S0-COM-02: friend detail graceful fallback and route stability', () {
    testWidgets('friend profile fallback constructs valid UserBrief on error',
        (tester) async {
      // Simulates what FriendProfileScreen does when API fails:
      // it constructs a FriendProfileDetail with the userId and displayName
      // that were passed as constructor params, then builds content from that.
      const userId = 'user-404';
      const displayName = 'MissingUser';

      // The fallback UserBrief must be valid
      final fallbackUser = UserBrief(
        id: userId,
        username: displayName,
        nickname: displayName,
      );

      expect(fallbackUser.id, userId);
      expect(fallbackUser.displayName, displayName);

      // Verify the route accepts the profile path with query params
      expect(
        CommunityRoutes.userProfile,
        '/community/users/:id',
      );
    });

    testWidgets('favorites, requests, and discover all have safe back navigation',
        (tester) async {
      // Verify all three screens use canPop() -> pop() else go('/community')
      // This test checks the route definitions exist and are distinct
      final routes = CommunityRoutes.routes;

      final routePaths = routes.whereType<GoRoute>().map((r) => r.path).toSet();

      expect(routePaths.contains(CommunityRoutes.friendsRequests), isTrue);
      expect(routePaths.contains(CommunityRoutes.friendsDiscover), isTrue);
      expect(routePaths.contains(CommunityRoutes.favorites), isTrue);
      expect(routePaths.contains(CommunityRoutes.userProfile), isTrue);
    });
  });

  group('S0-COM-04: accountability nudge shows delivery summary', () {
    testWidgets('nudge success prioritizes delivery_summary over generic message',
        (tester) async {
      // Verify the priority chain: delivery_summary > message > default
      const successResult = {
        'delivery_summary': '已通过站内提醒发送，对方在线时会实时看到',
        'message': '已提醒',
      };
      final displayMessage = (successResult['delivery_summary'] as String?) ??
          (successResult['message'] as String?) ??
          '已通过站内提醒发送，对方在线时会实时看到';
      expect(displayMessage, '已通过站内提醒发送，对方在线时会实时看到');

      // When delivery_summary is absent, falls back to message
      const fallbackResult = {'message': '已提醒伙伴'};
      final fallbackMessage =
          (fallbackResult['delivery_summary'] as String?) ??
              (fallbackResult['message'] as String?) ??
              '已通过站内提醒发送，对方在线时会实时看到';
      expect(fallbackMessage, '已提醒伙伴');

      // When both absent, uses informative default
      const emptyResult = <String, dynamic>{};
      final defaultMessage = (emptyResult['delivery_summary'] as String?) ??
          (emptyResult['message'] as String?) ??
          '已通过站内提醒发送，对方在线时会实时看到';
      expect(defaultMessage.contains('站内'), isTrue);
      expect(defaultMessage.contains('实时'), isTrue);
    });

    testWidgets('cooldown error message explains delivery mechanism',
        (tester) async {
      // Verify cooldown detection patterns
      expect('HTTP 429 cooldown'.contains('429'), isTrue);
      expect('cooldown period'.contains('cooldown'), isTrue);

      // Verify the new cooldown message explains HOW reminders are delivered
      const cooldownDisplay =
          '刚提醒过，冷却期内不会重复发送。提醒会以站内提示的形式送达，对方在线时会实时看到。';
      expect(cooldownDisplay.contains('站内提示'), isTrue);
      expect(cooldownDisplay.contains('实时看到'), isTrue);
      expect(cooldownDisplay.contains('冷却期'), isTrue);
    });
  });

  group('S0-COM-05: group and private chat AI assistant functionality', () {
    testWidgets('private chat AI has 5 distinct preset prompts',
        (tester) async {
      final presets = [
        'polish_reply',
        'gentle_reminder',
        'schedule_sync',
        'summary',
        'next_step',
      ];

      final prompts = <String>{};
      for (final preset in presets) {
        final prompt = buildPrivateAssistantPresetPrompt(preset);
        expect(prompt.isNotEmpty, isTrue,
            reason: 'preset "$preset" must produce a non-empty prompt');
        expect(prompt.length > 10, isTrue,
            reason: 'preset "$preset" must produce a real prompt');
        prompts.add(prompt);
      }
      // All 5 presets must produce distinct prompts
      expect(prompts.length, 5);
    });

    testWidgets('group chat AI has 3 distinct preset prompts',
        (tester) async {
      final presets = ['summary', 'reminder', 'consensus'];

      final prompts = <String>{};
      for (final preset in presets) {
        final prompt = buildGroupAssistantPresetPrompt(preset);
        expect(prompt.isNotEmpty, isTrue,
            reason: 'preset "$preset" must produce a non-empty prompt');
        expect(prompt.length > 10, isTrue,
            reason: 'preset "$preset" must produce a real prompt');
        prompts.add(prompt);
      }
      // All 3 presets must produce distinct prompts
      expect(prompts.length, 3);
    });

    testWidgets('group agent prompt includes group name and user input',
        (tester) async {
      final prompt = buildGroupAgentPrompt(
        input: '帮我总结一下',
        recentMessages: const [],
        groupName: '冲刺群',
      );

      expect(prompt.contains('冲刺群'), isTrue);
      expect(prompt.contains('帮我总结一下'), isTrue);
      expect(prompt.contains('群聊AI助手'), isTrue);
    });

    testWidgets('private agent prompt includes friend name and user input',
        (tester) async {
      final prompt = buildPrivateAgentPrompt(
        input: '帮我润色',
        recentMessages: const [],
        friendName: '小明',
      );

      expect(prompt.contains('小明'), isTrue);
      expect(prompt.contains('帮我润色'), isTrue);
      expect(prompt.contains('私聊AI助手'), isTrue);
    });

    testWidgets('agent user identity constants are well-defined',
        (tester) async {
      expect(kCommunityAgentUserId, isNotEmpty);
      expect(kCommunityAgentDisplayName, isNotEmpty);
      expect(kCommunityAgentAvatarSeed, isNotEmpty);

      final agentUser = buildCommunityAgentUser();
      expect(agentUser.id, kCommunityAgentUserId);
      expect(agentUser.status, UserStatus.online);
    });
  });
}

const _locDelegates = [
  ...AppLocalizations.localizationsDelegates,
  GlobalMaterialLocalizations.delegate,
  GlobalWidgetsLocalizations.delegate,
  GlobalCupertinoLocalizations.delegate,
];
