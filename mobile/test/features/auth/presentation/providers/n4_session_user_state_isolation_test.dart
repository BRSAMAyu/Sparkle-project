import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/home/presentation/providers/understanding_snapshot_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

/// N-4 跨账号本地状态泄漏 红绿测试。
///
/// Android round-2 实测（docs/competition/.../android-round2-verification.md
/// N-4）：登出 fieldtester20 后，新访客的驾驶舱仍显示前一账号的
/// 目标 `round4_nodate_goal`。
///
/// 根因：驾驶舱目标链（multiGoalOverviewProvider / activeGoalProvider）与
/// 理解快照（understandingSnapshotProvider）都是长生命周期（keep-alive）
/// provider，持有用户态数据，但**不在** sessionBoundProvidersProvider 的
/// 登出失效清单里 —— 登出只清了存储层（view_state.*），这些 provider 的
/// 内存态跨账号存活，下一账号首屏直接渲染上一账号的数据。
///
/// 红（修复前）：logout 后 activeGoalProvider 仍返回前一账号 goal id；
/// multiGoalOverviewProvider / understandingSnapshotProvider 不重算，
/// 继续吐出前一账号的数据。
/// 绿（修复后）：三者都在登出时失效重算，新账号读到新身份的数据。
const userAGoalId = 'goal-A-fieldtester20';
const userAGoalTitle = 'round4_nodate_goal';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const activeGoalStorageKey = 'view_state.active_goal.current_goal_id';

  Future<ProviderContainer> buildContainer(
    _GatedAuthRepository repo,
    _IdentityApiClient apiClient,
    SharedPreferences prefs,
  ) async {
    final container = ProviderContainer(
      overrides: [
        authRepositoryProvider.overrideWithValue(repo),
        sharedPreferencesProvider.overrideWithValue(prefs),
        apiClientProvider.overrideWithValue(apiClient),
        chatRepositoryProvider.overrideWithValue(_FakeChatRepository()),
      ],
    );
    return container;
  }

  Future<void> settle() async {
    for (var i = 0; i < 5; i++) {
      await Future<void>.delayed(Duration.zero);
    }
    await Future<void>.delayed(const Duration(milliseconds: 10));
  }

  test('session 失效清单包含驾驶舱目标链与理解快照 providers', () async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final prefs = await SharedPreferences.getInstance();
    final container = await buildContainer(
      _GatedAuthRepository(),
      _IdentityApiClient(),
      prefs,
    );
    addTearDown(container.dispose);

    final sessionBound = container.read(sessionBoundProvidersProvider);

    // 目标链（N-4 实测泄漏源：驾驶舱显示上一账号的 goal）
    expect(
      sessionBound,
      contains(activeGoalProvider),
      reason: 'activeGoalProvider 持有跨账号的 current_goal_id',
    );
    expect(
      sessionBound,
      contains(multiGoalOverviewProvider),
      reason: 'multiGoalOverviewProvider 持有上一账号的目标列表',
    );
    // 理解快照（同屏泄漏面）
    expect(sessionBound, contains(understandingSnapshotProvider));
  });

  test('登出后新账号不得看到前一账号的目标与理解快照', () async {
    // 用户 A 的本地持久化目标选择（真实路径：
    // multiGoalOverviewProvider → activeGoalProvider.selectGoal → prefs）
    SharedPreferences.setMockInitialValues(<String, Object>{
      activeGoalStorageKey: userAGoalId,
    });
    final prefs = await SharedPreferences.getInstance();
    await ViewStorageService.ensureInitialized();

    final apiClient = _IdentityApiClient();
    final container = await buildContainer(
      _GatedAuthRepository(),
      apiClient,
      prefs,
    );
    addTearDown(container.dispose);

    // ── 用户 A 会话 ──────────────────────────────────────────────
    // 本地残留的 A 的目标选择被 provider 恢复（登录态内存值）。
    expect(container.read(activeGoalProvider), userAGoalId);

    // A 的驾驶舱目标链渲染出 A 的目标（fake spine 返回 A 的数据）。
    final overviewA = await container.read(multiGoalOverviewProvider.future);
    expect(
      overviewA.goals.map((goal) => goal.id),
      contains(userAGoalId),
    );
    expect(
      overviewA.goals.map((goal) => goal.title),
      contains(userAGoalTitle),
    );

    // A 的理解快照。
    final snapshotA =
        await container.read(understandingSnapshotProvider.future);
    expect(
      snapshotA?.claims.map((claim) => claim.claimId),
      contains('claim-A'),
    );

    // ── 登出 → 新访客 B ─────────────────────────────────────────
    await container.read(authProvider.notifier).logout();
    await settle();

    // 服务器侧此刻属于新身份 B：返回空数据（模拟 B 的后端状态）。
    apiClient.serveIdentityAData = false;

    // 绿：activeGoalProvider 已失效重建，不再持有 A 的 goal id。
    expect(
      container.read(activeGoalProvider),
      isNull,
      reason: '登出后 A 的 current_goal_id 内存态必须被清掉',
    );

    // 绿：本地存储里 A 的目标选择也被清除。
    expect(prefs.getString(activeGoalStorageKey), isNull);

    // 绿：目标链与理解快照被登出失效，重算后反映新身份 B（空数据），
    // 而不是继续吐出 A 的缓存。
    final overviewB = await container.read(multiGoalOverviewProvider.future);
    expect(
      overviewB.goals.map((goal) => goal.id),
      isNot(contains(userAGoalId)),
      reason: 'multiGoalOverviewProvider 未在登出时失效，B 首屏直接渲染 A 的目标',
    );

    final snapshotB =
        await container.read(understandingSnapshotProvider.future);
    expect(
      snapshotB?.claims.map((claim) => claim.claimId),
      isNot(contains('claim-A')),
      reason: 'understandingSnapshotProvider 未在登出时失效，B 首屏直接渲染 A 的理解快照',
    );
  });
}

class _GatedAuthRepository extends AuthRepository {
  _GatedAuthRepository() : super(_UnusedApiClient(), _MemoryTokenStorage());

  @override
  Future<bool> isLoggedIn() async => await getAccessToken() != null;

  @override
  Future<void> logout({bool keepDemoMode = false}) async {
    await clearTokens();
  }
}

/// 按身份返回驾驶舱数据的 fake ApiClient。
///
/// [serveIdentityAData] 为 true 时模拟用户 A 的后端状态（spine goals、
/// 理解快照都有数据）；为 false 时模拟新身份 B（空数据）。
class _IdentityApiClient implements ApiClient {
  bool serveIdentityAData = true;

  @override
  dynamic noSuchMethod(Invocation invocation) {
    if (invocation.memberName == #get) {
      final path = invocation.positionalArguments.first as String;
      return Future<Response<Map<String, dynamic>>>.value(
        Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: path),
          data: _dataFor(path),
        ),
      );
    }
    return Future<Response<Map<String, dynamic>>>.value(
      Response<Map<String, dynamic>>(
        requestOptions: RequestOptions(),
        data: const <String, dynamic>{},
      ),
    );
  }

  Map<String, dynamic> _dataFor(String path) {
    if (!serveIdentityAData) {
      return const <String, dynamic>{};
    }
    if (path == '/aurora/spine/goals') {
      return <String, dynamic>{
        'goals': <Map<String, dynamic>>[
          <String, dynamic>{
            'goal_id': userAGoalId,
            'title': userAGoalTitle,
            'goal_type': 'exam',
          },
        ],
      };
    }
    if (path == '/experience/understanding-snapshot') {
      return <String, dynamic>{
        'claims': <Map<String, dynamic>>[
          <String, dynamic>{
            'claim_id': 'claim-A',
            'claim': '用户A的目标 claim',
            'confidence': 0.9,
            'confidence_label': 'high',
            'evidence_summary': 'evidence',
            'scope': 'memory_claim',
            'user_can_correct': true,
          },
        ],
      };
    }
    return const <String, dynamic>{};
  }
}

class _MemoryTokenStorage implements TokenStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> write(String key, String value) async {
    _values[key] = value;
  }

  @override
  Future<void> delete(String key) async {
    _values.remove(key);
  }
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeChatRepository extends ChatRepository {
  _FakeChatRepository() : super(Dio(), container: ProviderContainer());

  final _connectionController = StreamController<WsConnectionState>.broadcast();

  @override
  Stream<WsConnectionState> get connectionStateStream =>
      _connectionController.stream;

  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;

  @override
  void dispose() {
    unawaited(_connectionController.close());
  }
}
