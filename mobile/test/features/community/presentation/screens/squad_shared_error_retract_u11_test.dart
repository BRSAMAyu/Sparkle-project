import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/shared_error_models.dart';
import 'package:sparkle/features/community/data/models/squad_board_models.dart';
import 'package:sparkle/features/community/data/models/squad_models.dart';
import 'package:sparkle/features/community/data/models/study_room_models.dart';
import 'package:sparkle/features/community/data/repositories/squad_repository.dart';
import 'package:sparkle/features/community/presentation/providers/squad_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import '../../../../shared/i18n_test_helper.dart';

/// V4-U11 验收面 1（分享/撤回可达）移动端钉：本人分享行内撤回动作
/// 一正三反——
/// 正：撤回动作可见 → 确认 → DELETE 带对参数 → 列表刷新不含该行；
/// 反 1：他人分享零撤回入口（授权面 = 分享者本人）；
/// 反 2：撤回失败诚实报错、行保留（不乐观删行、不假成功）；
/// 反 3：取消确认不产生任何 API 调用。
void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    setUpI18nForTesting();
  });
  tearDown(tearDownI18n);

  SharedErrorEntry entry({
    required String shareId,
    String sharerId = 'user-b',
    String sharerName = '小明',
  }) =>
      SharedErrorEntry(
        shareId: shareId,
        sharerId: sharerId,
        sharerName: sharerName,
        errorId: 'err-$shareId',
        questionText: '计算定积分 ∫0..1 x² dx',
        subjectCode: 'math',
        masteryLevel: 0.55,
        reviewCount: 2,
        createdAt: DateTime.utc(2026, 9, 21),
      );

  testWidgets(
    'own share shows inline retract; confirm calls DELETE with share id and refreshes list',
    (tester) async {
      final repository = _FakeSquadRepository(
        sharedErrors: [
          entry(shareId: 'share-mine', sharerId: 'user-a', sharerName: '我'),
        ],
        currentUserId: 'user-a',
      );
      await _pumpSquadDetail(
        tester,
        repository: repository,
        currentUserId: 'user-a',
      );

      // 正面：本人分享行有撤回入口（key 含 shareId）。
      final retractButton = find
          .byKey(const ValueKey('squad-shared-error-retract-share-mine'));
      expect(retractButton, findsOneWidget);

      await tester.tap(retractButton);
      await _settle(tester);

      // 确认对话出现；确认后 DELETE 恰好一次且带对 shareId。
      expect(find.text('撤回这张错题分享？'), findsOneWidget);
      await tester.tap(
        find.byKey(const ValueKey('squad-shared-error-retract-confirm')),
      );
      await _settle(tester);

      expect(repository.retractCalls, 1);
      expect(repository.lastRetractedShareId, 'share-mine');
      // 刷新后列表不再含该分享（fake 仓库撤回后返回空列表 = 服务端软删语义）。
      expect(find.text('我 分享'), findsNothing);
      expect(
        find.byKey(const ValueKey('squad-shared-error-retract-share-mine')),
        findsNothing,
      );
    },
  );

  testWidgets(
    'other member share exposes no retract action (retract authorizes sharer only)',
    (tester) async {
      final repository = _FakeSquadRepository(
        sharedErrors: [entry(shareId: 'share-theirs')],
        currentUserId: 'user-a',
      );
      await _pumpSquadDetail(
        tester,
        repository: repository,
        currentUserId: 'user-a',
      );

      // 反面 1：他人分享的卡可渲染（白名单投影可见），但零撤回入口。
      expect(find.text('小明 分享'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('squad-shared-error-retract-share-theirs')),
        findsNothing,
      );
      expect(repository.retractCalls, 0);
    },
  );

  testWidgets(
    'retract failure keeps the entry and surfaces honest error (no fake success)',
    (tester) async {
      final repository = _FakeSquadRepository(
        sharedErrors: [
          entry(shareId: 'share-mine', sharerId: 'user-a', sharerName: '我'),
        ],
        currentUserId: 'user-a',
      )..retractError = Exception('network 500');
      await _pumpSquadDetail(
        tester,
        repository: repository,
        currentUserId: 'user-a',
      );

      await tester.tap(
        find.byKey(const ValueKey('squad-shared-error-retract-share-mine')),
      );
      await _settle(tester);
      await tester
          .tap(find.byKey(const ValueKey('squad-shared-error-retract-confirm')));
      await _settle(tester);

      // 反面 2：失败时调用发生但不刷新成「已消失」——行仍在，错误文案上浮。
      expect(repository.retractCalls, 1);
      expect(find.textContaining('撤回失败'), findsOneWidget);
      expect(find.text('我 分享'), findsOneWidget);
      expect(
        find.byKey(const ValueKey('squad-shared-error-retract-share-mine')),
        findsOneWidget,
      );
      expect(find.text('已撤回错题分享'), findsNothing);
    },
  );

  testWidgets('cancelling the confirm dialog triggers no API call',
      (tester) async {
    final repository = _FakeSquadRepository(
      sharedErrors: [
        entry(shareId: 'share-mine', sharerId: 'user-a', sharerName: '我'),
      ],
      currentUserId: 'user-a',
    );
    await _pumpSquadDetail(
      tester,
      repository: repository,
      currentUserId: 'user-a',
    );

    await tester.tap(
      find.byKey(const ValueKey('squad-shared-error-retract-share-mine')),
    );
    await _settle(tester);
    await tester.tap(find.text('取消'));
    await _settle(tester);

    // 反面 3：取消 = 零副作用。
    expect(repository.retractCalls, 0);
    expect(find.text('我 分享'), findsOneWidget);
  });
}

/// 屏内 shimmer/骨架屏是无限动画：像既有 squad_detail 屏测试一样用
/// 显式推进时钟，不用 pumpAndSettle（永不 settle）。
Future<void> _settle(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pump(const Duration(milliseconds: 400));
}

Future<void> _pumpSquadDetail(
  WidgetTester tester, {
  required _FakeSquadRepository repository,
  required String currentUserId,
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
        currentUserProvider.overrideWithValue(_buildUser(currentUserId)),
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

UserModel _buildUser(String id) => UserModel(
      id: id,
      username: 'current_user',
      email: 'current@example.com',
      flameLevel: 3,
      flameBrightness: 0.8,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _FakeSquadRepository extends SquadRepository {
  _FakeSquadRepository({
    required this.sharedErrors,
    required this.currentUserId,
  }) : super(_UnusedApiClient());

  List<SharedErrorEntry> sharedErrors;
  final String currentUserId;
  Exception? retractError;
  int retractCalls = 0;
  String? lastRetractedShareId;

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
      const SquadLeaderboard(
        squadId: 'sq-1',
        memberCount: 4,
        sprintActive: true,
        boardValid: true,
        selfViewOnly: false,
        entries: [
          SquadLeaderboardEntry(
            rank: 1,
            userId: 'user-a',
            displayName: '我',
            completionRate: 0.8,
            hasLedgerData: true,
            percentile: 75,
          ),
        ],
      );

  @override
  Future<StudyRoomPresence> getPresence(String groupId) async =>
      StudyRoomPresence(
        groupId: groupId,
        memberCount: 1,
        inRoomCount: 0,
        members: const [],
      );

  @override
  Future<StudyRoomMyStatus> heartbeatStudyRoom(String groupId) async =>
      const StudyRoomMyStatus(inRoom: false, todayMinutes: 0);

  @override
  Future<SharedErrorList> listSharedErrors(String groupId) async =>
      SharedErrorList(
        squadId: groupId,
        total: sharedErrors.length,
        items: sharedErrors,
      );

  @override
  Future<SharedErrorRetractResult> retractSharedError(
    String groupId,
    String shareId,
  ) async {
    retractCalls++;
    lastRetractedShareId = shareId;
    final error = retractError;
    if (error != null) {
      throw error;
    }

    // 软删语义：撤回后列表即不含该条。
    sharedErrors = sharedErrors
        .where((e) => e.shareId != shareId)
        .toList(growable: false);
    return SharedErrorRetractResult(
      shareId: shareId,
      retracted: true,
    );
  }
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
