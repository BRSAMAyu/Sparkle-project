import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/auth/presentation/widgets/guest_conversion_card.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<(GoRouter, SharedPreferences)> pumpCard(
    WidgetTester tester, {
    required bool isGuest,
    bool seedSignal = false,
    TaskModel? activeTask,
  }) async {
    SharedPreferences.setMockInitialValues({
      if (seedSignal) 'guest_conversion_signal_count': 1,
    });
    final prefs = await SharedPreferences.getInstance();
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (_, __) => const Scaffold(body: GuestConversionCard()),
        ),
        GoRoute(
          path: '/register',
          builder: (_, __) => const Scaffold(
            body: Center(child: Text('REGISTER_SCREEN')),
          ),
        ),
      ],
    );

    await tester.pumpWidget(
      // Key 防坑：同一 testWidgets 内二次 pump 时，同型 ProviderScope 会复用
      // State（容器不重建、旧 override 残留）；按用例身份换 key 强制新容器。
      ProviderScope(
        key: ValueKey('guest-conversion-$isGuest-$seedSignal-$activeTask'),
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          authProvider.overrideWith(
            (ref) => isGuest
                ? _StaticGuestAuthNotifier()
                : _StaticRegisteredAuthNotifier(),
          ),
          if (activeTask != null)
            activeTaskProvider.overrideWith((ref) => activeTask),
        ],
        child: MaterialApp.router(
          routerConfig: router,
          theme: ThemeData.light().copyWith(
            extensions: [SparkleThemeExtension.light()],
          ),
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
        ),
      ),
    );
    await tester.pumpAndSettle();
    return (router, prefs);
  }

  testWidgets('价值信号触发：访客+已有价值动作 → 价值回顾形引导卡可见',
      (tester) async {
    await pumpCard(tester, isGuest: true, seedSignal: true);

    expect(find.text('你的备考进度已保存在本机'), findsOneWidget);
    expect(find.text('注册并同步进度'), findsOneWidget);
    expect(find.text('暂不'), findsOneWidget);
  });

  testWidgets('克制红线：进行中任务时卡不可见（永不打断进行中任务）', (tester) async {
    await pumpCard(
      tester,
      isGuest: true,
      seedSignal: true,
      activeTask: _buildTask(TaskStatus.inProgress),
    );

    expect(find.text('你的备考进度已保存在本机'), findsNothing);
  });

  testWidgets('零信号访客与注册用户均不可见（唯一钩子，不骚扰）', (tester) async {
    await pumpCard(tester, isGuest: true);
    expect(
      find.text('你的备考进度已保存在本机'),
      findsNothing,
      reason: 'aha 之前不谈 signup',
    );

    await pumpCard(tester, isGuest: false, seedSignal: true);
    expect(
      find.text('你的备考进度已保存在本机'),
      findsNothing,
      reason: '注册用户不是转化对象',
    );
  });

  testWidgets('点「注册并同步进度」→ 落 /register 路由，且本会话硬关', (tester) async {
    final (_, _) = await pumpCard(tester, isGuest: true, seedSignal: true);

    await tester.tap(find.text('注册并同步进度'));
    await tester.pumpAndSettle();

    // 路由断言（UI 锚点）：'REGISTER_SCREEN' 桩只挂在 GoRouter 的
    // '/register' GoRoute builder 上——它出现即证明 push 落在了注册路由
    // （routeInformationProvider/currentConfiguration 在测试导航下不回写）。
    expect(find.text('REGISTER_SCREEN'), findsOneWidget);
    expect(
      find.text('你的备考进度已保存在本机'),
      findsNothing,
      reason: '点击注册后本会话硬关，卡不再出现',
    );
  });

  testWidgets('点「暂不」→ 卡消失且持久挂起标记落盘（直到下个价值信号）', (tester) async {
    final (_, prefs) = await pumpCard(tester, isGuest: true, seedSignal: true);

    await tester.tap(find.text('暂不'));
    await tester.pumpAndSettle();

    expect(find.text('你的备考进度已保存在本机'), findsNothing);
    expect(find.text('注册并同步进度'), findsNothing);
    expect(
      prefs.getBool('guest_conversion_dismissed_until_next_signal'),
      isTrue,
    );
  });
}

TaskModel _buildTask(TaskStatus status) {
  final now = DateTime(2026, 9, 22);
  return TaskModel(
    id: 'task-1',
    userId: 'user-1',
    title: '完成一次冲刺任务',
    type: TaskType.learning,
    tags: const ['test'],
    estimatedMinutes: 25,
    difficulty: 2,
    energyCost: 2,
    status: status,
    priority: 1,
    createdAt: now,
    updatedAt: now,
  );
}

UserModel _buildUser({String? registrationSource}) {
  final now = DateTime(2026, 9, 22);
  return UserModel(
    id: '00000000-0000-0000-0000-000000000001',
    username: 'guest_test_user',
    email: 'guest@example.com',
    flameLevel: 1,
    flameBrightness: 0.5,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    registrationSource: registrationSource,
    createdAt: now,
    updatedAt: now,
  );
}

class _StaticGuestAuthNotifier extends AuthNotifier {
  _StaticGuestAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: _buildUser(registrationSource: 'guest'),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _StaticRegisteredAuthNotifier extends AuthNotifier {
  _StaticRegisteredAuthNotifier()
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: _buildUser(registrationSource: 'email'),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) => InterceptorsWrapper() as T;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_NoopApiClient(), _MapTokenStorage());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MapTokenStorage implements TokenStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> write(String key, String value) async => _values[key] = value;

  @override
  Future<void> delete(String key) async => _values.remove(key);
}
