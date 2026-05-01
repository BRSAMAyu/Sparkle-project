import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/group_chat_bubble.dart';
import 'package:sparkle/features/community/presentation/widgets/private_chat_bubble.dart';
import 'package:sparkle/features/community/presentation/widgets/share_resource_sheet.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  group('J3 frontend closure', () {
    testWidgets('private task share adopt lands in task detail route',
        (tester) async {
      final repo = _FakeCommunityShareRepository(
        adoptResult: {
          'resource_type': 'task',
          'new_resource_id': 'task-owned-1',
        },
      );

      await _pumpHarness(
        tester,
        repo: repo,
        child: PrivateChatBubble(
          message: PrivateMessageInfo(
            id: 'pm-1',
            sender: _user('sender-1', 'Alice'),
            receiver: _user('receiver-1', 'Bob'),
            messageType: MessageType.taskShare,
            isRead: false,
            createdAt: DateTime(2026, 3, 25, 10),
            updatedAt: DateTime(2026, 3, 25, 10),
            content: '分享任务',
            contentData: {
              'shared_resource_id': 'shared-task-1',
              'resource_id': 'task-source-1',
              'resource_title': '链表刷题',
              'resource_summary': '完成 45 分钟',
            },
          ),
        ),
      );

      await tester.tap(find.text('采纳任务'));
      await tester.pumpAndSettle();

      expect(repo.lastAdoptedId, 'shared-task-1');
      expect(find.text('task-route:task-owned-1'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('group plan share adopt lands in plan detail route',
        (tester) async {
      final repo = _FakeCommunityShareRepository(
        adoptResult: {
          'resource_type': 'plan',
          'new_resource_id': 'plan-owned-1',
        },
      );

      await _pumpHarness(
        tester,
        repo: repo,
        child: GroupChatBubble(
          message: MessageInfo(
            id: 'gm-1',
            sender: _user('sender-2', 'Carol'),
            messageType: MessageType.planShare,
            createdAt: DateTime(2026, 3, 25, 10),
            updatedAt: DateTime(2026, 3, 25, 10),
            content: '分享计划',
            contentData: {
              'shared_resource_id': 'shared-plan-1',
              'resource_id': 'plan-source-1',
              'resource_title': '系统设计冲刺',
              'resource_meta': {
                'progress': 0.4,
              },
            },
          ),
        ),
      );

      await tester.tap(find.text('采纳计划'));
      await tester.pumpAndSettle();

      expect(repo.lastAdoptedId, 'shared-plan-1');
      expect(find.text('plan-route:plan-owned-1'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('plan share succeeds without popping parent route',
        (tester) async {
      final shareRepo = _FakeCommunityShareRepository(
        adoptResult: const {},
        shareResult: const {'id': 'shared-plan-created'},
      );
      final communityRepo = _FakeCommunityRepository(
        friends: [
          _friendship('friend-1', 'Alice'),
        ],
        groups: [
          _group('group-1', '冲刺群'),
        ],
      );

      await _pumpShareSheetHarness(
        tester,
        shareRepository: shareRepo,
        communityRepository: communityRepo,
      );

      expect(find.text('分享到社群'), findsOneWidget);
      await tester.tap(find.text('Alice'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('立即分享'));
      await tester.pumpAndSettle();

      expect(shareRepo.lastShareRequest?['resource_type'], 'plan');
      expect(shareRepo.lastShareRequest?['target_user_id'], 'friend-1');
      expect(find.text('j3-root'), findsOneWidget);
      expect(find.text('分享到社群'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('achievement share uses chat message send and keeps parent route',
        (tester) async {
      final shareRepo = _FakeCommunityShareRepository(
        adoptResult: const {},
        shareResult: const {'id': 'unused'},
      );
      final communityRepo = _FakeCommunityRepository(
        friends: [
          _friendship('friend-1', 'Alice'),
        ],
        groups: [
          _group('group-9', '火花群'),
        ],
      );

      await _pumpShareSheetHarness(
        tester,
        shareRepository: shareRepo,
        communityRepository: communityRepo,
        resourceType: 'achievement',
      );

      await tester.tap(find.text('群组'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('火花群'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('立即分享'));
      await tester.pumpAndSettle();

      expect(shareRepo.lastShareRequest, isNull);
      expect(communityRepo.lastGroupMessageType, MessageType.achievement);
      expect(communityRepo.lastGroupId, 'group-9');
      expect(find.text('j3-root'), findsOneWidget);
      expect(find.text('分享到社群'), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('knowledge and achievement cards render without adopt actions',
        (tester) async {
      await _pumpHarness(
        tester,
        repo: _FakeCommunityShareRepository(adoptResult: const {}),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            GroupChatBubble(
              message: MessageInfo(
                id: 'gm-knowledge-1',
                sender: _user('sender-3', 'Dana'),
                messageType: MessageType.capsuleShare,
                createdAt: DateTime(2026, 3, 25, 10),
                updatedAt: DateTime(2026, 3, 25, 10),
                content: '分享知识',
                contentData: {
                  'resource_type': 'knowledge_node',
                  'resource_id': 'node-1',
                  'resource_title': '编译原理',
                  'resource_summary': '语法分析与语义分析',
                },
              ),
            ),
            PrivateChatBubble(
              message: PrivateMessageInfo(
                id: 'pm-achievement-1',
                sender: _user('sender-4', 'Evan'),
                receiver: _user('receiver-4', 'Finn'),
                messageType: MessageType.achievement,
                isRead: false,
                createdAt: DateTime(2026, 3, 25, 10),
                updatedAt: DateTime(2026, 3, 25, 10),
                content: '分享成就',
                contentData: {
                  'achievement_id': 'ach-1',
                  'name': '七日连胜',
                  'description': '连续 7 天完成任务',
                },
              ),
            ),
          ],
        ),
      );

      expect(find.text('编译原理'), findsOneWidget);
      expect(find.text('七日连胜'), findsOneWidget);
      expect(find.textContaining('采纳'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });
}

Future<void> _pumpHarness(
  WidgetTester tester, {
  required CommunityShareRepository repo,
  required Widget child,
}) async {
  final router = GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => Scaffold(body: Center(child: child)),
      ),
      GoRoute(
        path: '/tasks/:id',
        builder: (context, state) => Scaffold(
          body: Center(
            child: Text('task-route:${state.pathParameters['id']}'),
          ),
        ),
      ),
      GoRoute(
        path: '/plans/:id',
        builder: (context, state) => Scaffold(
          body: Center(
            child: Text('plan-route:${state.pathParameters['id']}'),
          ),
        ),
      ),
    ],
  );
  addTearDown(router.dispose);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        communityShareRepositoryProvider.overrideWithValue(repo),
      ],
      child: MaterialApp.router(
        routerConfig: router,
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
      ),
    ),
  );

  await tester.pumpAndSettle();
}

Future<void> _pumpShareSheetHarness(
  WidgetTester tester, {
  required _FakeCommunityShareRepository shareRepository,
  required _FakeCommunityRepository communityRepository,
  String resourceType = 'plan',
}) async {
  final router = GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => Scaffold(
          body: Center(
            child: _AutoOpenShareView(
              resourceType: resourceType,
              child: const Text('j3-root'),
            ),
          ),
        ),
      ),
    ],
  );
  addTearDown(router.dispose);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        communityShareRepositoryProvider.overrideWithValue(shareRepository),
        communityRepositoryProvider.overrideWithValue(communityRepository),
        accountabilityOverviewProvider.overrideWith(
          (ref) async => AccountabilityOverviewInfo(slotType: 'core'),
        ),
      ],
      child: MaterialApp.router(
        routerConfig: router,
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
      ),
    ),
  );

  await tester.pumpAndSettle();
}

class _AutoOpenShareView extends StatefulWidget {
  const _AutoOpenShareView({
    required this.resourceType,
    required this.child,
  });

  final String resourceType;
  final Widget child;

  @override
  State<_AutoOpenShareView> createState() => _AutoOpenShareViewState();
}

class _AutoOpenShareViewState extends State<_AutoOpenShareView> {
  bool _didOpen = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_didOpen) return;
    _didOpen = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      unawaited(
        showModalBottomSheet<void>(
          context: context,
          isScrollControlled: true,
          builder: (sheetContext) => ShareResourceSheet(
            resourceType: widget.resourceType,
            resourceId: 'resource-1',
            title: '测试资源',
            subtitle: '测试摘要',
            feedbackContext: context,
          ),
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) => widget.child;
}

UserBrief _user(String id, String name) => UserBrief(
      id: id,
      username: name.toLowerCase(),
      nickname: name,
      status: UserStatus.online,
    );

FriendshipInfo _friendship(String id, String name) => FriendshipInfo(
      id: 'friendship-$id',
      friend: _user(id, name),
      status: FriendshipStatus.accepted,
      createdAt: DateTime(2026, 3, 25, 9),
      updatedAt: DateTime(2026, 3, 25, 9),
    );

GroupListItem _group(String id, String name) => GroupListItem(
      id: id,
      name: name,
      type: GroupType.squad,
      memberCount: 3,
      totalFlamePower: 12,
      focusTags: const ['协作'],
    );

class _FakeCommunityShareRepository extends CommunityShareRepository {
  _FakeCommunityShareRepository({
    required this.adoptResult,
    this.shareResult,
  })
      : super(
          _UnusedApiClient(),
          AppEventStreamService(_FakeRef(), _UnusedApiClient()),
        );

  final Map<String, dynamic> adoptResult;
  final Map<String, dynamic>? shareResult;
  String? lastAdoptedId;
  Map<String, dynamic>? lastShareRequest;

  @override
  Future<Map<String, dynamic>> adoptResource({
    required String sharedResourceId,
  }) async {
    lastAdoptedId = sharedResourceId;
    return adoptResult;
  }

  @override
  Future<Map<String, dynamic>> shareResource({
    required String resourceType,
    required String resourceId,
    String? targetGroupId,
    String? targetUserId,
    String permission = 'view',
    String? comment,
  }) async {
    lastShareRequest = {
      'resource_type': resourceType,
      'resource_id': resourceId,
      'target_group_id': targetGroupId,
      'target_user_id': targetUserId,
      'permission': permission,
      'comment': comment,
    };
    return shareResult ?? {'id': 'shared-generic'};
  }
}

class _FakeCommunityRepository extends CommunityRepository {
  _FakeCommunityRepository({
    required this.friends,
    required this.groups,
  }) : super(_UnusedApiClient());

  final List<FriendshipInfo> friends;
  final List<GroupListItem> groups;
  String? lastGroupId;
  MessageType? lastGroupMessageType;
  PrivateMessageSend? lastPrivateMessage;

  @override
  Future<List<FriendshipInfo>> getFriends({
    int limit = 50,
    int offset = 0,
  }) async =>
      friends;

  @override
  Future<List<GroupListItem>> getMyGroups() async => groups;

  @override
  Future<MessageInfo> sendMessage(
    String groupId, {
    required MessageType type,
    String? content,
    Map<String, dynamic>? contentData,
    String? replyToId,
    String? threadRootId,
    List<String>? mentionUserIds,
    String? nonce,
  }) async {
    lastGroupId = groupId;
    lastGroupMessageType = type;
    return MessageInfo(
      id: 'group-message-1',
      sender: _user('sender-system', 'System'),
      messageType: type,
      createdAt: DateTime(2026, 3, 25, 11),
      updatedAt: DateTime(2026, 3, 25, 11),
      content: content,
      contentData: contentData,
    );
  }

  @override
  Future<PrivateMessageInfo> sendPrivateMessage(
    PrivateMessageSend message,
  ) async {
    lastPrivateMessage = message;
    return PrivateMessageInfo(
      id: 'private-message-1',
      sender: _user('sender-system', 'System'),
      receiver: _user(message.targetUserId, 'Target'),
      messageType: message.messageType,
      isRead: false,
      createdAt: DateTime(2026, 3, 25, 11),
      updatedAt: DateTime(2026, 3, 25, 11),
      content: message.content,
      contentData: message.contentData,
    );
  }
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeRef implements Ref {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
