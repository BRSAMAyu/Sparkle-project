import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/errors/failures.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/notification_center/data/repositories/notification_center_repository.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/shared/entities/user_model.dart';

import '../../shared/i18n_test_helper.dart';

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakePrefs implements SharedPreferences {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;

  @override
  Future<bool> setBool(String key, bool value) async => true;

  @override
  bool? getBool(String key) => null;
}

/// 测试 Ref：read 一律回 _FakePrefs（auth 域 demo 偏好读写用）。
class _FakeRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => _FakePrefs();
}

/// 抛错仓储：按卡只重写被测方法，其余 noSuchMethod 兜底。
class _ThrowingAuthRepository extends AuthRepository {
  _ThrowingAuthRepository() : super(_NoopApiClient(), SecureTokenStorage());

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('unexpected repository call');

  @override
  Future<void> changePassword(String oldPassword, String newPassword) async =>
      throw const SocketException('connection reset by peer');

  @override
  Future<UserModel> updateAvatar(String filePath) async =>
      throw DioException(
        requestOptions: RequestOptions(path: '/me/avatar'),
        response: Response<void>(
          requestOptions: RequestOptions(path: '/me/avatar'),
          statusCode: 401,
        ),
      );
}

/// login 抛网络异常的仓储（登录渲染链路端到端用）。
class _LoginThrowingRepository extends AuthRepository {
  _LoginThrowingRepository() : super(_NoopApiClient(), SecureTokenStorage());

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('unexpected repository call');

  /// 未登录干净起步：checkAuthStatus 走 logged-out 分支，不触发本卡外的链路。
  @override
  Future<bool> isLoggedIn() async => false;

  @override
  Future<UserModel> login(String usernameOrEmail, String password) async =>
      throw const SocketException('connection reset by peer');
}

class _StubAuthNotifier extends AuthNotifier {
  _StubAuthNotifier() : super(_FakeRef(), _ThrowingAuthRepository());

  @override
  Future<void> checkAuthStatus() async {}
}

class _ThrowingNotifRepository extends NotificationCenterRepository {
  _ThrowingNotifRepository() : super(_NoopApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('notification feed blew up unexpectedly');

  @override
  Future<int> markAllAsRead() async =>
      throw const SocketException('connection refused');
}

/// ERR-SECONDARY 批（A-SPEC3 N15 次级域 provider 赋值批）：
/// auth 15 处 / notification_center 14(+1) 处 `error: e.toString()` 赋值
/// 全部类型化——错误字段只存 [UiErrorCategory]，raw 异常永不入户。
void main() {
  group('AppFailure.uiErrorCategory（kind → 类别纯绑定）', () {
    test('六类 failure 均自报类别，零文本嗅探', () {
      expect(
        const NetworkFailure(message: 'x').uiErrorCategory,
        UiErrorCategory.network,
      );
      expect(
        const OfflineFailure(message: 'x').uiErrorCategory,
        UiErrorCategory.network,
      );
      expect(
        const AuthFailure(message: 'x').uiErrorCategory,
        UiErrorCategory.auth,
      );
      expect(
        const ServerFailure(message: 'x').uiErrorCategory,
        UiErrorCategory.server,
      );
      expect(
        const ValidationFailure(message: 'x').uiErrorCategory,
        UiErrorCategory.format,
      );
      expect(
        const UnknownFailure(message: 'x').uiErrorCategory,
        UiErrorCategory.unknown,
      );
    });
  });

  group('auth provider 账号安全流错误字段类型化', () {
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer(
        overrides: [
          authProvider.overrideWith((ref) => _StubAuthNotifier()),
        ],
      );
    });

    tearDown(() => container.dispose());

    test('changePassword 网络异常 → error 存 network 类别（非异常文本）',
        () async {
      await expectLater(
        container.read(authProvider.notifier).changePassword('a', 'b'),
        throwsA(isA<SocketException>()),
      );
      final state = container.read(authProvider);
      expect(state.error, UiErrorCategory.network);
      // N15：字段已是类别枚举，raw 异常文本形态不可能出现。
      expect(state.failure, isNull);
    });

    test('updateAvatar 401 → AppFailure 类型化判定 → auth 类别', () async {
      await expectLater(
        container.read(authProvider.notifier).updateAvatar('/tmp/x.png'),
        throwsA(isA<DioException>()),
      );
      expect(container.read(authProvider).error, UiErrorCategory.auth);
    });
  });

  group('notification_center provider 错误字段类型化', () {
    late ProviderContainer container;

    setUp(() {
      container = ProviderContainer(
        overrides: [
          notificationCenterRepositoryProvider
              .overrideWithValue(_ThrowingNotifRepository()),
        ],
      );
    });

    tearDown(() => container.dispose());

    test('markAllAsRead 网络异常 → error 存 network 类别（非异常文本）',
        () async {
      await container
          .read(notificationCenterProvider.notifier)
          .markAllAsRead();
      final state = container.read(notificationCenterProvider);
      expect(state.error, UiErrorCategory.network);
      // 契约钉死：状态错误字段的静态类型即类别——异常文本无处可存。
      expect(
        state.error.runtimeType,
        UiErrorCategory,
      );
    });
  });

  group('登录失败渲染链路（_failedAuthState 类型化 + login 监听端到端）', () {
    testWidgets('login 网络异常 → SnackBar 出 failure 人话，raw 异常零出现',
        (tester) async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final container = ProviderContainer(
        overrides: [
          authRepositoryProvider
              .overrideWithValue(_LoginThrowingRepository()),
          sharedPreferencesProvider.overrideWithValue(prefs),
          sessionBoundProvidersProvider.overrideWithValue(const []),
        ],
      );
      addTearDown(container.dispose);
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: testMaterialApp(
            theme: AppThemes.lightTheme,
            home: const LoginScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextFormField).at(0), 'login_user');
      await tester.enterText(find.byType(TextFormField).at(1), 'password123');
      await tester.pump();

      await tester.tap(find.widgetWithText(SparkleButton, '登录'),
          warnIfMissed: false,);
      // 错误 SnackBar 常驻不自动消失，pumpAndSettle 会永不等静——用定长 pump。
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));

      // 状态侧：错误字段类型化（network 类别 + OfflineFailure 随行——
      // SocketException 被 failure 判定表归为离线，类别同属 network 族）。
      final state = container.read(authProvider);
      expect(state.error, UiErrorCategory.network);
      expect(state.failure, isA<OfflineFailure>());

      // 渲染侧：SnackBar 出 failure.userMessage 人话，raw 异常零出现。
      expect(find.textContaining('connection reset by peer'), findsNothing);
      expect(find.textContaining('Exception'), findsNothing);
      expect(find.textContaining('像是离线状态'), findsOneWidget);
    });
  });
}
