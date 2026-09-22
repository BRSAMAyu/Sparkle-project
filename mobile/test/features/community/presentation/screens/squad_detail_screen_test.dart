import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/shared_error_models.dart';
import 'package:sparkle/features/community/data/models/squad_board_models.dart';
import 'package:sparkle/features/community/data/models/squad_models.dart';
import 'package:sparkle/features/community/data/models/study_room_models.dart';
import 'package:sparkle/features/community/data/repositories/squad_repository.dart';
import 'package:sparkle/features/community/presentation/providers/squad_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('SquadDetailScreen (D-COMM-4/5)', () {
    testWidgets(
        'leaderboard renders tied ranks as-is (1,1,3) with completion percent',
        (tester) async {
      await _pumpSquadDetail(
        tester,
        repository: _FakeSquadRepository(
          board: _boardTies(),
          presence: _presence(inRoomCount: 1),
        ),
      );

      // 必达项①：成员完成度榜（info 语义标题 + 并列名次 1,1,3 如实渲染）。
      expect(find.text('成员完成度榜'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('squad-leaderboard-rank-u1')),
        findsOneWidget,
      );
      expect(find.text('1'), findsNWidgets(2)); // 并列第一 ×2
      expect(find.text('3'), findsOneWidget); // 竞赛排名如实，不重排
      expect(find.text('完成度 80%'), findsNWidgets(2));
      expect(find.text('完成度 40%'), findsOneWidget);
      // has_ledger_data=false：诚实显示「无账本数据」，不伪装成 0%。
      expect(find.text('无账本数据'), findsOneWidget);
      expect(find.text('完成度 0%'), findsNothing);
    });

    testWidgets('study room shows presence list and enter action calls API',
        (tester) async {
      final repository = _FakeSquadRepository(
        board: _boardTies(),
        presence: _presence(inRoomCount: 1),
      );
      await _pumpSquadDetail(tester, repository: repository);

      // 必达项②：在室状态（success 语义徽标 + 今日累计 + 全员在场）。
      expect(find.text('共学自习室'), findsOneWidget);
      expect(find.text('1 人在室'), findsOneWidget);
      expect(find.text('未在室'), findsOneWidget); // 本人（心跳诚实上报）
      expect(find.text('今日自习 12 分钟'), findsOneWidget);
      // 在室队友（success 语义在场点；榜行 + 在场行各一处，如实渲染）。
      expect(find.text('小明'), findsNWidgets(2));
      expect(find.text('今日自习 30 分钟'), findsOneWidget);
      // 未入场成员如实列 0（不惩罚缺席）。
      expect(find.text('今日自习 0 分钟'), findsOneWidget);

      // 显式进出：点进入 → API 调用一次，状态翻转。
      await tester
          .tap(find.byKey(const ValueKey('squad-study-room-enter-button')));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 400));

      expect(repository.enterCalls, 1);
      expect(
        find.byKey(const ValueKey('squad-study-room-exit-button')),
        findsOneWidget,
      );
    });

    testWidgets(
        'self_view_only degrade shows notice and self-anchor switch, not a broken board',
        (tester) async {
      await _pumpSquadDetail(
        tester,
        repository: _FakeSquadRepository(
          board: _boardTies().copyWithDegrade(),
          presence: _presence(inRoomCount: 0),
        ),
      );

      // 降级提示 + 切自我锚入口（既有路由）。
      expect(find.textContaining('小队不足 3 人'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('squad-degrade-self-anchor-button')),
        findsOneWidget,
      );
      expect(find.text('查看我的自我锚'), findsOneWidget);
      // 不渲染残缺榜（无名次行、无完成度数字）。
      expect(
        find.byKey(const ValueKey('squad-leaderboard-rank-u1')),
        findsNothing,
      );
      expect(find.text('完成度 80%'), findsNothing);
    });

    testWidgets(
        'shared errors section is honest when empty and renders snapshot cards',
        (tester) async {
      // 空态：诚实引导，不报错不造假卡。
      await _pumpSquadDetail(
        tester,
        repository: _FakeSquadRepository(
          board: _boardTies(),
          presence: _presence(inRoomCount: 0),
        ),
      );
      expect(find.text('错题分享'), findsOneWidget);
      expect(find.textContaining('还没有错题分享'), findsOneWidget);
      expect(find.text('去错题本'), findsOneWidget);
      expect(find.text('小明 分享'), findsNothing);

      // 数据态：白名单投影如实渲染（题目/知识点/掌握度快照），无答案字段可渲染。
      final shared = SharedErrorEntry(
        shareId: 'share-1',
        sharerId: 'u2',
        sharerName: '小明',
        errorId: 'err-9',
        questionText: '计算定积分 ∫0..1 x² dx',
        subjectCode: 'math',
        knowledgeNodes: const [
          SharedKnowledgeNode(id: 'k1', name: '定积分', isPrimary: true),
        ],
        note: '我卡在换元这步',
        masteryLevel: 0.55,
        reviewCount: 2,
        createdAt: DateTime.utc(2026, 9, 21),
      );
      await _pumpSquadDetail(
        tester,
        repository: _FakeSquadRepository(
          board: _boardTies(),
          presence: _presence(inRoomCount: 0),
          sharedErrors: [shared],
        ),
      );
      expect(find.text('小明 分享'), findsOneWidget);
      expect(find.text('计算定积分 ∫0..1 x² dx'), findsOneWidget);
      expect(find.text('定积分'), findsOneWidget);
      expect(find.text('完成度 55%'), findsOneWidget);
      expect(find.text('我卡在换元这步'), findsOneWidget);
      // 契约无答案字段：任何「答案」字样都不该出现（不造不存在的字段）。
      expect(find.textContaining('正确答案'), findsNothing);
      expect(find.textContaining('我的答案'), findsNothing);
    });
  });
}

SquadLeaderboard _boardTies() => const SquadLeaderboard(
      squadId: 'sq-1',
      memberCount: 4,
      sprintActive: true,
      boardValid: true,
      selfViewOnly: false,
      entries: [
        SquadLeaderboardEntry(
          rank: 1,
          userId: 'u1',
          displayName: '阿黄',
          completionRate: 0.8,
          hasLedgerData: true,
          percentile: 75,
        ),
        SquadLeaderboardEntry(
          rank: 1,
          userId: 'u2',
          displayName: '小明',
          completionRate: 0.8,
          hasLedgerData: true,
          percentile: 75,
        ),
        SquadLeaderboardEntry(
          rank: 3,
          userId: 'u3',
          displayName: '小李',
          completionRate: 0.4,
          hasLedgerData: true,
          percentile: 25,
        ),
        SquadLeaderboardEntry(
          rank: 4,
          userId: 'u4',
          completionRate: 0.0,
          hasLedgerData: false,
          percentile: 0,
        ),
      ],
    );

extension on SquadLeaderboard {
  SquadLeaderboard copyWithDegrade() => SquadLeaderboard(
        squadId: squadId,
        memberCount: 2,
        sprintActive: sprintActive,
        boardValid: false,
        selfViewOnly: true,
        myRank: myRank,
        entries: entries,
      );
}

StudyRoomPresence _presence({required int inRoomCount}) => StudyRoomPresence(
      groupId: 'sq-1',
      memberCount: 3,
      inRoomCount: inRoomCount,
      members: const [
        StudyRoomPresenceEntry(
          userId: 'u2',
          displayName: '小明',
          inRoom: true,
          isStale: false,
          currentSessionMinutes: 30,
          todayMinutes: 30,
        ),
        StudyRoomPresenceEntry(
          userId: 'u3',
          displayName: '小李',
          inRoom: false,
          isStale: false,
          currentSessionMinutes: 0,
          todayMinutes: 0,
        ),
      ],
    );

Future<void> _pumpSquadDetail(
  WidgetTester tester, {
  required _FakeSquadRepository repository,
}) async {
  tester.view.physicalSize = const Size(390, 2200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final router = GoRouter(
    navigatorKey: navigatorKey,
    initialLocation: CommunityRoutes.squadDetailPath('sq-1'),
    routes: CommunityRoutes.routes,
  );
  addTearDown(router.dispose);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        squadRepositoryProvider.overrideWithValue(repository),
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

  await tester.pump();
  await tester.pump(const Duration(milliseconds: 600));
}

class _FakeSquadRepository extends SquadRepository {
  _FakeSquadRepository({
    this.board,
    this.presence,
    this.sharedErrors = const [],
  }) : super(_UnusedApiClient());

  final SquadLeaderboard? board;
  final StudyRoomPresence? presence;
  final List<SharedErrorEntry> sharedErrors;
  int enterCalls = 0;

  @override
  Future<List<SquadListItem>> listMySquads() async => const [];

  @override
  Future<SquadInfo> getSquad(String groupId) async => SquadInfo(
        id: groupId,
        name: '高数期末互助队',
        sprintGoal: '期末数学一周冲刺',
        deadline: DateTime.utc(2026, 9, 27),
        maxMembers: 8,
        isPublic: true,
        memberCount: 4,
        daysRemaining: 5,
        myRole: 'owner',
        createdAt: DateTime.utc(2026, 9, 20),
      );

  @override
  Future<SquadLeaderboard> getLeaderboard(String groupId) async =>
      board ?? (throw Exception('no board fixture'));

  @override
  Future<StudyRoomPresence> getPresence(String groupId) async =>
      presence ?? (throw Exception('no presence fixture'));

  @override
  Future<StudyRoomMyStatus> heartbeatStudyRoom(String groupId) async =>
      StudyRoomMyStatus(inRoom: enterCalls > 0, todayMinutes: 12);

  @override
  Future<StudyRoomMyStatus> enterStudyRoom(String groupId) async {
    enterCalls++;
    return const StudyRoomMyStatus(inRoom: true, todayMinutes: 12);
  }

  @override
  Future<SharedErrorList> listSharedErrors(String groupId) async =>
      SharedErrorList(
        squadId: groupId,
        total: sharedErrors.length,
        items: sharedErrors,
      );
}

class _UnusedApiClient extends ApiClient {
  _UnusedApiClient() : super(_UnusedRef());
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
