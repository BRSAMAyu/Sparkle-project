import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/guest_service.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show guestServiceProvider, sharedPreferencesProvider;
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart'
    show WsConnectionState;
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart'
    show chatRepositoryProvider;
import 'package:sparkle/features/home/presentation/providers/episode_resume_provider.dart';
import 'package:sparkle/features/journey/data/repositories/first_action_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

/// V4-U06 验收③ · 身份切换隔离（U06 语义级）——「guest 示例不污染真实
/// 长期记忆」的客户端清除链与回执读面翻转。
///
/// 三层断言（n4 同口径：notifier 级驱动认证链，非 provider 直捅读面）：
/// 1. 清除链：register / upgradeGuest 必须执行 `clearGuestData`（N-4 清除
///    链的 guest 侧；真实数据侧由 LocalDatabase/ViewStorage try/catch 承载，
///    本夹具不初始化 isar——isar 就位时清除链在测试环境真异步挂起，见
///    guest_upgrade_landing_route_test 夹具注记）；
/// 2. roster 完整性（U06 增量）：回执读面 contextReceiptProvider 必须登记
///    进 session 失效清单——它持有上一身份的 selection receipt；不翻转则
///    (a) guest 回执泄漏进真实账号读面，(b) W2 bootstrap 会把 guest 的
///    receipt ref 携进新账号的 I01 调用（跨身份污染回执链）；
/// 3. 行为翻转：upgrade 后 latest 读面必须是新身份的回执，不得残留 guest
///    回执（红先行：回填 roster 前此断言红——guest 回执跨身份存活）。
class _IdentityScriptedApi implements ApiClient {
  bool identitySwitched = false;
  final gets = <String>[];

  Map<String, dynamic> _payload(String receiptId, String role) => {
        'mode': 'live',
        'schema_version': 'context_selection_receipt.v1',
        'receipt': {
          'schema_version': 'context_selection_receipt.v1',
          'receipt_id': receiptId,
          'selection_role': role,
          'decision_id': null,
          'input_versions': {
            'memory_epoch': 3,
            'selector_version': 'context_pack.v4-i06.v1',
          },
          'candidates': <Map<String, dynamic>>[
            {'ref': 'task://t1', 'status': 'selected', 'reason_code': null, 'note': null},
          ],
          'budget': {'candidate_scan_limit': 12, 'selected_max': 6, 'clarifications_used': 0},
          'why_now': null,
        },
        'source_verification': <Map<String, dynamic>>[],
        'resolved_selected_count': 1,
      };

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    gets.add(path);
    final data = identitySwitched
        ? _payload('csr_user_real', 'chat_context')
        : _payload('csr_guest_example', 'resume_view');
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: data as T,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('stub only implements get');
}

class _SpyGuestService extends GuestService {
  _SpyGuestService(super.prefs);

  int clearCalls = 0;

  @override
  Future<void> clearGuestData() async {
    clearCalls++;
    await super.clearGuestData();
  }
}

class _CountingAuthRepository extends AuthRepository {
  _CountingAuthRepository(this._identity) : super(_UnusedApi(), _MemoryTokenStorage());
  int registerCalls = 0;
  int upgradeCalls = 0;

  /// 身份切换时刻：仓储层成功即翻转脚本（清除链随后触发读面重算）。
  final _IdentityScriptedApi _identity;

  @override
  Future<bool> isLoggedIn() async => false;

  @override
  Future<UserModel> register(
    String username,
    String email,
    String password, {
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
  }) async {
    registerCalls++;
    _identity.identitySwitched = true;
    return _realUser();
  }

  @override
  Future<UserModel> upgradeGuest({
    required String username,
    required String email,
    required String password,
    required bool acceptedTos,
    required bool acceptedPrivacy,
    String tosVersion = 'v1',
    String privacyVersion = 'v1',
    String? agreedLocale,
  }) async {
    upgradeCalls++;
    _identity.identitySwitched = true;
    return _realUser();
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedApi implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeChatRepository extends ChatRepository {
  _FakeChatRepository() : super(Dio(), container: ProviderContainer());

  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;

  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

UserModel _realUser() => UserModel(
      id: '00000000-0000-0000-0000-00000000u06'.replaceFirst('u06', '06'),
      username: 'u06_real',
      email: 'u06real@example.com',
      nickname: 'U06 Real',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      registrationSource: 'email',
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<(_CountingAuthRepository, _SpyGuestService, _IdentityScriptedApi)>
      build() async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final api = _IdentityScriptedApi();
    final repo = _CountingAuthRepository(api);
    final spy = _SpyGuestService(prefs);
    return (repo, spy, api);
  }

  test('roster 完整性（U06 增量）：回执读面 + first-action 投影都在身份失效清单里',
      () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    final roster = container.read(sessionBoundProvidersProvider);
    expect(roster.contains(firstActionStateProvider), isTrue,
        reason: 'n4 既有约束（T3 同源）：first-action 投影持有用户 goal',);
    expect(roster.contains(contextReceiptProvider), isTrue,
        reason: 'U06 增量：回执读面持有上一身份的 selection receipt——'
            '不翻转则 guest 回执泄漏进真实账号首程面，且 W2 bootstrap 会把 '
            'guest receipt ref 携进新账号 I01（跨身份污染回执链）',);
    expect(
      roster.contains(episodeResumeProvider),
      isFalse,
      reason: '派生面不直接入册（其上游 receipt/growth 翻转即重算）',
    );
  });

  test('行为翻转：upgrade 后 latest 读面是新身份回执，guest 回执不跨身份存活',
      () async {
    final (repo, spy, api) = await build();
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(
      overrides: [
        authRepositoryProvider.overrideWithValue(repo),
        sharedPreferencesProvider.overrideWithValue(prefs),
        guestServiceProvider.overrideWithValue(spy),
        apiClientProvider.overrideWithValue(api),
        chatRepositoryProvider.overrideWithValue(_FakeChatRepository()),
      ],
    );
    addTearDown(container.dispose);

    // guest 会话期：latest = guest 的 resume_view 回执。
    await container.read(contextReceiptProvider.notifier).load();
    final guestState = container.read(contextReceiptProvider);
    expect(guestState.phase, ContextReceiptPhase.ready);
    expect(guestState.view?.receiptId, 'csr_guest_example',
        reason: '前置：guest 会话的回执在读面就位',);

    // 身份切换（真实 upgradeGuest 链）：清除链 + session 失效清单翻转。
    await container.read(authProvider.notifier).upgradeGuest(
          username: 'u06_real',
          email: 'u06real@example.com',
          password: 'U06-Passw0rd!',
          acceptedTos: true,
          acceptedPrivacy: true,
        );

    // 清除链证据：guest 数据侧清理被执行（register/upgrade 各自触发）。
    expect(spy.clearCalls, greaterThanOrEqualTo(1),
        reason: 'N-4 清除链 guest 侧必须随身份切换执行',);

    // refresh 是 unawaited —— 轮询等待回执读面按新身份重算。
    String? latestId;
    for (var i = 0; i < 100; i++) {
      await Future<void>.delayed(const Duration(milliseconds: 20));
      final state = container.read(contextReceiptProvider);
      final view = state.phase == ContextReceiptPhase.ready ? state.view : null;
      latestId = view?.receiptId;
      if (latestId == 'csr_user_real') {
        break;
      }
    }
    expect(latestId, 'csr_user_real',
        reason: 'U06 语义：身份切换后回执读面必须翻转——guest 示例回执不得'
            '泄漏进真实账号（红先行：roster 回填前 latest 残留 csr_guest_example）',);
  });

  test('清除链：register 同样触发 guest 侧清理（两条身份切换路径对称）', () async {
    final (repo, spy, api) = await build();
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(
      overrides: [
        authRepositoryProvider.overrideWithValue(repo),
        sharedPreferencesProvider.overrideWithValue(prefs),
        guestServiceProvider.overrideWithValue(spy),
        apiClientProvider.overrideWithValue(api),
        chatRepositoryProvider.overrideWithValue(_FakeChatRepository()),
      ],
    );
    addTearDown(container.dispose);

    expect(spy.clearCalls, 0);
    await container.read(authProvider.notifier).register(
          'u06_real',
          'u06real@example.com',
          'U06-Passw0rd!',
          acceptedTos: true,
          acceptedPrivacy: true,
        );
    expect(spy.clearCalls, greaterThanOrEqualTo(1),
        reason: '注册 = 身份切换的另一条路径，清除链必须同样执行'
            '（具体次数随清除链内部组合，语义层只锚「必须清」）',);
    expect(repo.registerCalls, 1);
  });
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
