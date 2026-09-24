import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_providers.dart';
import 'package:sparkle/features/community/presentation/widgets/groups_hub_view.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('GroupsHubView squads entry (NAV-IA P-4)', () {
    testWidgets('squads entry tile is visible and pushes /community/squads',
        (tester) async {
      final router = GoRouter(
        navigatorKey: navigatorKey,
        initialLocation: '/groups-hub',
        routes: [
          GoRoute(
            path: '/groups-hub',
            builder: (_, __) => const Scaffold(body: GroupsHubView()),
          ),
          GoRoute(
            path: '/community/squads',
            builder: (_, __) =>
                const Scaffold(body: Center(child: Text('小队列表'))),
          ),
        ],
      );
      addTearDown(router.dispose);

      await _pumpHub(tester, router: router);

      // Community（Groups tab）首行「冲刺小队」入口——同伴关系的家内直达小队。
      expect(
        find.byKey(const ValueKey('community-squads-entry')),
        findsOneWidget,
      );
      expect(find.text('冲刺小队'), findsOneWidget);
      expect(find.text('组队冲刺，互盯完成度'), findsOneWidget);

      await tester
          .tap(find.byKey(const ValueKey('community-squads-entry')));
      await tester.pumpAndSettle();

      // push 后原屏在栈下不可见（offstage），以落点屏内容断言。
      expect(find.text('小队列表'), findsOneWidget);
    });
  });

  group('GroupsHubView S-03 surface convergence', () {
    testWidgets(
        'today check-in section renders sprint-first tiles with real counts',
        (tester) async {
      final router = _hubRouter();
      addTearDown(router.dispose);

      await _pumpHub(tester, router: router, shareRepository: _FakeShareRepo());

      // 收敛段标题 + 语义提示（Flame=群活跃，非付费）
      expect(find.text('今日打卡'), findsOneWidget);
      expect(find.text('打卡喂养群火堆——火苗只代表群活跃度'), findsOneWidget);

      // 冲刺群排前：第一个 tile 是 sprint 群，计数直读真源数字。
      expect(
        find.byKey(const ValueKey('community-checkin-tile-sprint-1')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('community-checkin-tile-squad-1')),
        findsOneWidget,
      );
      expect(find.text('今日 9 次打卡'), findsOneWidget);
      expect(find.text('今日 2 次打卡'), findsOneWidget);
    });

    testWidgets('check-in action calls repository and shows flame receipt',
        (tester) async {
      final router = _hubRouter();
      addTearDown(router.dispose);
      final shareRepo = _FakeShareRepo();

      await _pumpHub(tester, router: router, shareRepository: shareRepo);

      // 第一个打卡按钮（冲刺群 tile 内）。
      final checkinButtons =
          find.byKey(const ValueKey('community-checkin-open-button'));
      expect(checkinButtons, findsNWidgets(2));
      await tester.tap(checkinButtons.first);
      await tester.pumpAndSettle();

      // 对话框字段与群聊打卡一致：时长 + 内容。
      expect(find.text('每日打卡'), findsOneWidget);
      expect(find.text('打卡内容'), findsOneWidget);

      await tester.tap(
        find.descendant(
          of: find.byType(AlertDialog),
          matching: find.text('打卡'),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // 成功回执把 Flame 锚定在群活跃语义上（+火苗 喂进群火堆）。
      expect(find.text('打卡成功，+20 火苗喂进群火堆'), findsOneWidget);

      // 走完 snackbar 自动关闭计时器，避免测试收尾残留 pending timer。
      await tester.pump(const Duration(seconds: 3));
    });

    testWidgets('artifact feedback section surfaces shared resources',
        (tester) async {
      final router = _hubRouter();
      addTearDown(router.dispose);

      await _pumpHub(tester, router: router, shareRepository: _FakeShareRepo());

      expect(find.text('成果反馈'), findsOneWidget);
      expect(find.text('伙伴共享的学习成果——采纳即进你的知识库'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('community-artifact-card-res-1')),
        findsOneWidget,
      );
    });

    testWidgets('empty group list shows honest check-in empty state',
        (tester) async {
      final router = _hubRouter();
      addTearDown(router.dispose);

      await _pumpHub(
        tester,
        router: router,
        shareRepository: _FakeShareRepo(),
        emptyGroups: true,
      );

      expect(find.text('加入小队或群组后，在这里完成每日打卡'), findsOneWidget);
    });
  });

  group('GroupsHubView S-04 feedback → goal evidence', () {
    testWidgets(
        'check-in with linked goal offers trajectory jump and passes goal_id',
        (tester) async {
      final router = _hubRouterWithGoalDetail();
      addTearDown(router.dispose);
      final repo = _FakeCommunityRepository();

      await _pumpHub(
        tester,
        router: router,
        shareRepository: _FakeShareRepo(),
        communityRepository: repo,
        goals: const [ActiveGoalOption(id: 'goal-1', title: 'S-04 目标')],
      );

      await tester.tap(
        find.byKey(const ValueKey('community-checkin-open-button')).first,
      );
      await tester.pumpAndSettle();

      // 目标下拉出现并选中「S-04 目标」。
      await tester.tap(
        find.byKey(const ValueKey('community-checkin-goal-picker')),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('S-04 目标').last);
      await tester.pumpAndSettle();

      await tester.tap(
        find.descendant(
          of: find.byType(AlertDialog),
          matching: find.text('打卡'),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // repo 收到 goal_id（GJ16 回链）；成功回执带「查看目标轨迹」动作。
      expect(repo.lastGoalLink, 'goal-1');
      expect(find.text('打卡成功，+20 火苗'), findsOneWidget);
      await tester.tap(find.text('查看轨迹'));
      await tester.pumpAndSettle();
      debugPrint(
        'texts=${tester.widgetList<Text>(find.byType(Text)).map((w) => w.data).toList()}',
      );
      debugPrint('lastGoalLink=${repo.lastGoalLink}');
      expect(find.text('goal-detail:goal-1'), findsOneWidget);

      await tester.pump(const Duration(seconds: 3));
    });

    testWidgets('peer artifact exposes feedback action that submits verdict',
        (tester) async {
      final router = _hubRouter();
      addTearDown(router.dispose);
      final shareRepo = _FakeShareRepo();

      await _pumpHub(
        tester,
        router: router,
        shareRepository: shareRepo,
      );

      final feedbackButton = find.descendant(
        of: find.byKey(const ValueKey('community-artifact-card-res-1')),
        matching: find.byKey(const ValueKey('shared-resource-feedback-button')),
      );
      expect(feedbackButton, findsOneWidget);
      await tester.tap(feedbackButton);
      await tester.pumpAndSettle();

      // 反馈面板声明「反馈不改掌握度」语义后提交。
      expect(find.text('反馈这份共享成果'), findsOneWidget);
      await tester.tap(find.text('我照做了'));
      await tester.pumpAndSettle();
      await tester.tap(
        find.byKey(const ValueKey('shared-resource-feedback-submit')),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      expect(shareRepo.givenFeedbackIds, contains('res-1'));
      expect(shareRepo.lastVerdict, ResourceFeedbackVerdict.applied);
      expect(find.text('反馈已送达，感谢你的回应'), findsOneWidget);

      await tester.pump(const Duration(seconds: 3));
    });

    testWidgets('own artifact offers adopt-as-evidence entry with receipts',
        (tester) async {
      final router = _hubRouter();
      addTearDown(router.dispose);
      final shareRepo = _FakeShareRepo(ownOnly: true);

      await _pumpHub(
        tester,
        router: router,
        shareRepository: shareRepo,
      );

      // 本人共享卡片带「采纳为成果证据」入口（未采纳反馈 > 0）。
      await tester.tap(
        find.byKey(const ValueKey('shared-resource-adopt-evidence')),
      );
      await tester.pumpAndSettle();

      // 反馈面板列出反馈，采纳后走真实契约（回执含 goal_title）。
      expect(find.text('「我的作品集任务」收到的反馈'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('adopt-evidence-fb-1')));
      await tester.pumpAndSettle();

      expect(shareRepo.adoptedFeedbackIds, contains('fb-1'));
      expect(find.text('已采纳为「S-04 目标」的成果证据'), findsOneWidget);

      await tester.pump(const Duration(seconds: 3));
    });
  });
}

GoRouter _hubRouterWithGoalDetail() => GoRouter(
      navigatorKey: navigatorKey,
      initialLocation: '/groups-hub',
      routes: [
        GoRoute(
          path: '/groups-hub',
          builder: (_, __) => const Scaffold(body: GroupsHubView()),
        ),
        GoRoute(
          path: '/goals/:goalId',
          builder: (_, state) =>
              Scaffold(body: Center(child: Text('goal-detail:${state.pathParameters['goalId']!}'))),
        ),
      ],
    );

GoRouter _hubRouter() => GoRouter(
      navigatorKey: navigatorKey,
      initialLocation: '/groups-hub',
      routes: [
        GoRoute(
          path: '/groups-hub',
          builder: (_, __) => const Scaffold(body: GroupsHubView()),
        ),
      ],
    );

Future<void> _pumpHub(
  WidgetTester tester, {
  required GoRouter router,
  _FakeShareRepo? shareRepository,
  bool emptyGroups = false,
  List<ActiveGoalOption> goals = const [],
  _FakeCommunityRepository? communityRepository,
}) async {
  final shareRepo = shareRepository ?? _FakeShareRepo();
  tester.view.physicalSize = const Size(390, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        communityRepositoryProvider.overrideWithValue(
          communityRepository ?? _FakeCommunityRepository(emptyGroups: emptyGroups),
        ),
        communityShareRepositoryProvider.overrideWithValue(shareRepo),
        activeGoalsProvider.overrideWith((ref) => Future.value(goals)),
      ],
      child: MaterialApp.router(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        routerConfig: router,
        locale: const Locale('zh'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

class _FakeCommunityRepository extends CommunityRepository {
  _FakeCommunityRepository({this.emptyGroups = false}) : super(_UnusedApiClient());

  final bool emptyGroups;

  @override
  Future<List<GroupListItem>> getMyGroups() async => emptyGroups
      ? const []
      : [
          // 刻意让 squad 在前、sprint 在后，验证段内排序把冲刺群提到首位。
          GroupListItem(
            id: 'squad-1',
            name: '期末自习室（演示）',
            type: GroupType.squad,
            memberCount: 12,
            totalFlamePower: 640,
            todayCheckinCount: 2,
            focusTags: const [],
          ),
          GroupListItem(
            id: 'sprint-1',
            name: '算法冲刺小队',
            type: GroupType.sprint,
            memberCount: 8,
            totalFlamePower: 980,
            todayCheckinCount: 9,
            focusTags: const [],
            daysRemaining: 5,
          ),
        ];

  @override
  Future<CheckinResponse> checkin(
    String groupId, {
    required int todayDurationMinutes,
    String? message,
  }) async =>
      CheckinResponse(
        success: true,
        newStreak: 3,
        flameEarned: 20,
        rankInGroup: 1,
        groupCheckinCount: 10,
      );

  String? lastGoalLink;

  @override
  Future<CheckinGoalLink> checkinWithGoalLink(
    String groupId, {
    required int todayDurationMinutes,
    String? message,
    String? goalId,
  }) async {
    lastGoalLink = goalId;
    return CheckinGoalLink(
      response: CheckinResponse(
        success: true,
        newStreak: 3,
        flameEarned: 20,
        rankInGroup: 1,
        groupCheckinCount: 10,
      ),
      goalId: goalId,
      goalTitle: goalId == null ? null : 'S-04 目标',
    );
  }

  @override
  Future<GroupDirectoryInfo> getGroupDirectory({
    String? keyword,
    GroupType? type,
    List<String>? tags,
    GroupDirectorySort sortBy = GroupDirectorySort.hot,
    int limit = 20,
    int offset = 0,
  }) async =>
      GroupDirectoryInfo(
        sortBy: sortBy,
        availableTags: const [],
        totalCount: 0,
        recommendations: const [],
        groups: const [],
      );

  @override
  Future<List<GroupRecommendationItem>> getGroupRecommendations({
    int limit = 20,
    int cursor = 0,
  }) async =>
      const [];
}

/// 成果反馈段：走既有 CommunityShareRepository 契约的假实现（真实接口形状）。
class _FakeShareRepo extends CommunityShareRepository {
  _FakeShareRepo({this.ownOnly = false})
      : super(_UnusedApiClient(), _UnusedEventStream());

  final bool ownOnly;

  final List<String> givenFeedbackIds = <String>[];
  final List<String> adoptedFeedbackIds = <String>[];
  ResourceFeedbackVerdict? lastVerdict;

  @override
  Future<List<SharedResourceInfo>> fetchSharedResources({
    String sort = 'quality',
    String? resourceType,
    int limit = 20,
  }) async => ownOnly
        ? [
            // S-04：本人共享、带未采纳反馈——主人「采纳为成果证据」入口。
            SharedResourceInfo(
              id: 'res-own',
              resourceType: SharedResourceType.task,
              createdAt: DateTime.utc(2026, 9),
              resourceTitle: '我的作品集任务',
              resourceSummary: '自己共享的任务',
              qualityScore: 0.8,
              feedbackCount: 1,
              unadoptedFeedbackCount: 1,
              isOwn: true,
            ),
          ]
        : [
            SharedResourceInfo(
              id: 'res-1',
              resourceType: SharedResourceType.plan,
              createdAt: DateTime.utc(2026, 9),
              resourceTitle: '错题复盘计划',
              resourceSummary: '伙伴共享的复盘计划',
              qualityScore: 0.9,
            ),
          ];

  @override
  Future<void> giveFeedback({
    required String sharedResourceId,
    required ResourceFeedbackVerdict verdict,
    String? comment,
  }) async {
    givenFeedbackIds.add(sharedResourceId);
    lastVerdict = verdict;
  }

  @override
  Future<List<ResourceFeedbackItem>> fetchFeedback({
    required String sharedResourceId,
  }) async => [
            ResourceFeedbackItem(
              id: 'fb-1',
              sharedResourceId: sharedResourceId,
              verdict: 'helpful',
              comment: '很清楚',
              giverName: '社群伙伴',
            ),
          ];

  @override
  Future<Map<String, dynamic>> adoptFeedbackAsEvidence({
    required String sharedResourceId,
    required String feedbackId,
    String? goalId,
  }) async {
    adoptedFeedbackIds.add(feedbackId);
    return <String, dynamic>{
      'success': true,
      'goal_id': 'goal-1',
      'goal_title': 'S-04 目标',
      'feedback_id': feedbackId,
    };
  }
}

class _UnusedApiClient extends ApiClient {
  _UnusedApiClient() : super(_UnusedRef());
}

class _UnusedEventStream implements AppEventStreamService {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
