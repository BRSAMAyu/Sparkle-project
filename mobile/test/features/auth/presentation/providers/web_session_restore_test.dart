import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/core/storage/token_storage_web.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

/// N-4（web-round2 / W-2 残留）红绿测试：会话重载恢复链。
///
/// round-2 实测：web 登录成功后 localStorage 四键齐全
/// （flutter.access_token / flutter.refresh_token / accessToken / guest_id），
/// 但 reload 后仍回 `#/login?return_to=…` —— 写 ✓ 恢复 ✗。
///
/// 本测试把「恢复链」从头到尾锁住：token 注入 **真实的 TokenStorageWeb**
/// （web 后端，SharedPreferences/localStorage）→ 真实 `AuthRepository`
/// 继承的 `isLoggedIn()/getAccessToken()` 消费它 → 真实
/// `AuthNotifier.checkAuthStatus()`（含 guest reseed 分支与会话世代收口）
/// → `isAuthenticated == true`。同时验证失败语义：无 token 时必须回到
/// 未认证而非挂起。
///
/// 红（修复前 / 接线断裂时）：恢复链任何一环断开（如 tokenStorageProvider
/// 未被 authRepositoryProvider 消费、checkAuthStatus 竞态覆盖），本测试
/// isAuthenticated 到不了 true。
/// 绿（HEAD @ 164a1cd6）：接线完整，恢复链全绿 —— round-2 的 as-served
/// 失败定性为「22:02 陈旧运行实例早于竞态收口修复」（web-round2.md
/// 关键定性 1），需重启 flutter run 后按本语义线上复验。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const guestId = 'guest_n4restore';
  final guestUser = UserModel(
    id: 'n4000000-0000-4000-8000-000000000001',
    username: guestId,
    email: '$guestId@sparkle.local',
    flameLevel: 1,
    flameBrightness: 0.8,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    status: UserStatus.online,
    createdAt: DateTime(2026),
    updatedAt: DateTime(2026),
    registrationSource: 'guest',
  );

  /// 容器装配：必须先由调用方 `SharedPreferences.setMockInitialValues(...)`
  /// （保证 TokenStorageWeb 的 localStorage 后端可运行）。
  Future<ProviderContainer> buildRestoreContainer(
    _RestoreAuthRepository repo,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(
      overrides: [
        authRepositoryProvider.overrideWithValue(repo),
        sharedPreferencesProvider.overrideWithValue(prefs),
        // checkAuthStatus 成功路径会触发 SessionRefreshService：
        // 会话绑定 provider 集合置空 + chatProvider 换成静默桩，
        // 保证测试只考察恢复链本身（不拉起 WebSocket/仪表盘）。
        sessionBoundProvidersProvider.overrideWithValue(const []),
        chatProvider.overrideWith(
          (ref) => _QuietChatNotifier(_QuietChatRepository(), ref),
        ),
      ],
    );
    return container;
  }

  Future<AuthState> settleAuth(ProviderContainer container) async {
    // 触发 AuthNotifier 构造（构造内 unawaited(checkAuthStatus())）。
    container.read(authProvider.notifier);
    for (var i = 0; i < 200; i++) {
      final state = container.read(authProvider);
      if (!state.isLoading) return state;
      await Future<void>.delayed(const Duration(milliseconds: 5));
    }
    return container.read(authProvider);
  }

  test('token 注入 TokenStorageWeb → checkAuthStatus 恢复 → isAuthenticated=true（含 guest reseed）',
      () async {
    // localStorage 初态：访客 id + 非演示模式（模拟 web-round2 v8 重载前）。
    SharedPreferences.setMockInitialValues(const {
      'flutter.guest_id': guestId,
      'flutter.demo_guest_mode_enabled': false,
    });
    final storage = TokenStorageWeb();
    await storage.write(AppConstants.keyAccessToken, 'access-tok-n4');
    await storage.write('accessToken', 'access-tok-n4'); // legacy 双写与 saveTokens 一致
    final repo = _RestoreAuthRepository(storage, guestUser);

    final container = await buildRestoreContainer(repo);
    addTearDown(container.dispose);

    final state = await settleAuth(container);

    // 恢复成功。
    expect(state.isAuthenticated, isTrue, reason: 'token 在 storage 里，恢复链必须放行');
    expect(state.user?.username, guestId);
    // 真实 AuthRepository（未覆写 isLoggedIn/getAccessToken）确实消费了
    // TokenStorageWeb。
    expect(await storage.read(AppConstants.keyAccessToken), 'access-tok-n4');
    // guest reseed 分支按 round-2 旅程真实执行。
    expect(repo.meCalls, 1);
    expect(repo.guestLoginCalls, 1);
  });

  test('无 token（清空 storage）→ 恢复链必须落到未认证而非误判已登录', () async {
    SharedPreferences.setMockInitialValues(const {
      'flutter.guest_id': guestId,
      'flutter.demo_guest_mode_enabled': false,
    });
    final storage = TokenStorageWeb();
    final repo = _RestoreAuthRepository(storage, guestUser);

    final container = await buildRestoreContainer(repo);
    addTearDown(container.dispose);

    final state = await settleAuth(container);

    expect(state.isAuthenticated, isFalse);
    expect(repo.meCalls, 0, reason: '无 token 时不得发起 /me 请求');
  });
}

/// 恢复链被测主体：isLoggedIn/getAccessToken/getRefreshToken 全部走继承的
/// 真实实现（消费注入的 TokenStorage）；仅网络出口 getCurrentUser/guestLogin
/// 打桩，避免 flutter test 触网。
class _RestoreAuthRepository extends AuthRepository {
  _RestoreAuthRepository(TokenStorage storage, this._user)
      : super(_UnusedApiClient(), storage);

  final UserModel _user;
  int meCalls = 0;
  int guestLoginCalls = 0;

  @override
  Future<UserModel> getCurrentUser() async {
    meCalls += 1;
    return _user;
  }

  @override
  Future<UserModel> guestLogin(String guestId) async {
    guestLoginCalls += 1;
    return _user;
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _QuietChatNotifier extends ChatNotifier {
  _QuietChatNotifier(super.chatRepository, super.ref);

  @override
  Future<void> warmUpConnection() async {}
}

class _QuietChatRepository extends Fake implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream =>
      const Stream<WsConnectionState>.empty();

  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;

  @override
  void dispose() {}
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
