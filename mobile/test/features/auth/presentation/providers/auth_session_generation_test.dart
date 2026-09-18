import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/shared/entities/user_model.dart';

/// W-1 竞态收口红绿测试：AuthNotifier 会话世代守卫。
///
/// round-1 web 走查实测：登录 200 后 UI 不跳转的疑因 2 —— 并发
/// `checkAuthStatus()` 的终态写入（未认证）落在 `login()` 成功写入之后，
/// 把会话状态打回未认证。
///
/// 红（修复前）：过世代流程的 catch/finally/终态写入直接覆盖新流程状态，
/// 两个测试均失败（isAuthenticated 被打回 false）。
/// 绿（修复后）：过世代写入被丢弃。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<void> settle() async {
    for (var i = 0; i < 5; i++) {
      await Future<void>.delayed(Duration.zero);
    }
    await Future<void>.delayed(const Duration(milliseconds: 10));
  }

  final user = UserModel(
    id: 'gen-user-1',
    username: 'gen_user',
    email: 'gen@example.com',
    nickname: 'Gen User',
    flameLevel: 1,
    flameBrightness: 0.5,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    createdAt: DateTime(2026),
    updatedAt: DateTime(2026),
  );

  Future<ProviderContainer> buildContainer(_GatedAuthRepository repo) async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    return ProviderContainer(
      overrides: [
        authRepositoryProvider.overrideWithValue(repo),
        sharedPreferencesProvider.overrideWithValue(prefs),
        sessionBoundProvidersProvider.overrideWithValue(const []),
      ],
    );
  }

  test('过世代 checkAuthStatus 的未认证写入不得覆盖 login 成功态', () async {
    final repo = _GatedAuthRepository(user);
    // 构造器触发的 checkAuthStatus（gen1）挂起在 isLoggedIn，稍后以
    // 「未登录」放行——模拟引导期检查晚于登录完成的竞态。
    final staleGate = Completer<bool>();
    repo.queueIsLoggedInGate(staleGate);

    final container = await buildContainer(repo);
    addTearDown(container.dispose);

    container.read(authProvider.notifier); // gen1 starts, parks at gate
    await settle();

    await container.read(authProvider.notifier).login('u', 'p'); // gen2 wins
    expect(container.read(authProvider).isAuthenticated, isTrue);

    staleGate.complete(false); // 过世代 gen1 恢复：isLoggedIn == false
    await settle();

    // 红：false（被过世代写入覆盖）；绿：true（过世代写入被丢弃）。
    expect(container.read(authProvider).isAuthenticated, isTrue);
  });

  test('过世代 login 的失败态不得覆盖新 checkAuthStatus 的成功态', () async {
    final repo = _GatedAuthRepository(user);
    final staleGate = Completer<bool>()..complete(false);
    final freshGate = Completer<bool>()..complete(true);
    repo
      ..queueIsLoggedInGate(staleGate) // gen1（构造器）：未登录
      ..queueIsLoggedInGate(freshGate) // gen3（显式检查）：已登录
      ..loginGate = Completer<void>() // gen2 的 login 挂起
      ..loginShouldFail = true;

    final container = await buildContainer(repo);
    addTearDown(container.dispose);

    final notifier = container.read(authProvider.notifier); // gen1 done
    await settle();

    final loginFuture = notifier.login('u', 'p'); // gen2 parks in loginGate
    await settle();
    expect(container.read(authProvider).isLoading, isTrue);

    // 新的会话检查（gen3）在 login 在途时完成，给出成功态。
    await notifier.checkAuthStatus();
    expect(container.read(authProvider).isAuthenticated, isTrue);

    repo.loginGate!.complete(); // 放行过世代 login → 失败
    await loginFuture;
    await settle();

    // 红：false（过世代 catch/finally 覆盖）；绿：true（丢弃）。
    expect(container.read(authProvider).isAuthenticated, isTrue);
    expect(container.read(authProvider).error, isNull);
  });

  test('logout 作废在途 login 的写入', () async {
    final repo = _GatedAuthRepository(user);
    final staleGate = Completer<bool>()..complete(false);
    repo.queueIsLoggedInGate(staleGate);
    repo.loginGate = Completer<void>();

    final container = await buildContainer(repo);
    addTearDown(container.dispose);

    final notifier = container.read(authProvider.notifier);
    await settle();

    final loginFuture = notifier.login('u', 'p'); // gen2 parks
    await settle();

    await notifier.logout(); // gen3：logout 开新世代并重置状态
    repo.loginGate!.complete();
    await loginFuture;
    await settle();

    expect(container.read(authProvider).isAuthenticated, isFalse);
  });
}

class _GatedAuthRepository extends AuthRepository {
  _GatedAuthRepository(this._user)
      : super(_UnusedApiClient(), _MemoryTokenStorage());

  final UserModel _user;
  final List<Completer<bool>> _isLoggedInGates = <Completer<bool>>[];
  Completer<void>? loginGate;
  bool loginShouldFail = false;

  void queueIsLoggedInGate(Completer<bool> gate) =>
      _isLoggedInGates.add(gate);

  @override
  Future<bool> isLoggedIn() async {
    if (_isLoggedInGates.isNotEmpty) {
      return _isLoggedInGates.removeAt(0).future;
    }
    return await getAccessToken() != null;
  }

  @override
  Future<UserModel> getCurrentUser() async => _user;

  @override
  Future<UserModel> login(String usernameOrEmail, String password) async {
    final gate = loginGate;
    if (gate != null) {
      await gate.future;
    }
    if (loginShouldFail) {
      throw Exception('login failed (test)');
    }
    await saveTokens(
      TokenResponse(
        accessToken: 'gen-access-token',
        refreshToken: 'gen-refresh-token',
        expiresIn: 3600,
      ),
    );
    return _user;
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {
    await clearTokens();
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
