import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/persona_onboarding_draft.dart';
import 'package:sparkle/features/user/presentation/screens/persona_onboarding_screen.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

import '../../shared/i18n_test_helper.dart';

/// J-02 · 「只问改变 first action 的问题；其他信息延后」——最小 goal capture
/// 快车道（value before profile 的施工面）。
///
/// 钉住四层语义：
/// 1. 步 1 目标非空才出现快车道 CTA（空目标不提供——快车道不是跳过引导）；
/// 2. 快车道只提交 goal 捕获两字段（goal + goal_type），四项偏好零上行——
///    服务端 /profile/onboarding 各偏好条件写入（J-02 卡面「其他信息延后」）；
/// 3. 成功后续走 modeling 访谈（对话化画像，与全量提交同一续接面）；
///    草稿保留且步进到第一个「延后问」（学习风格），重进续答不重填目标；
/// 4. 失败可见可重试（与全量提交同一反馈形制，不假装成功）。
///
/// 渐进画像的完成态语义（服务端钉死）：goal-only 提交不写
/// study_time_preference/knowledge_level/response_style 偏好 →
/// onboardingCompleted 保持 false → OnboardingResumeCard 留存「继续引导」
/// 入口（后四问经它可达），五问零裁减（TV-G3），只延后。
const userId = 'j02-fastpath-user';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    setUpI18nForTesting();
  });

  Future<void> pumpScreen(
    WidgetTester tester, {
    required _RecordingUserRepository repo,
    GoRouter? router,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authProvider.overrideWith(
            (ref) => _FakeAuthNotifier(
              AuthState(isAuthenticated: true, user: _user()),
            ),
          ),
          userRepositoryProvider.overrideWithValue(repo),
        ],
        child: router == null
            ? testMaterialApp(home: const PersonaOnboardingScreen())
            : testMaterialApp(routerConfig: router),
      ),
    );
    // 异步恢复草稿 + 预览防抖。
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
  }

  Future<void> enterGoal(WidgetTester tester, String text) async {
    await tester.enterText(find.byType(TextField), text);
    await tester.pump(const Duration(milliseconds: 100));
  }

  testWidgets('fast-path CTA stays hidden until the goal has text',
      (tester) async {
    final repo = _RecordingUserRepository();
    await pumpScreen(tester, repo: repo);

    expect(
      find.byKey(const ValueKey('j02-fast-path-cta')),
      findsNothing,
      reason: '空目标不提供快车道——快车道不是跳过引导',
    );

    await enterGoal(tester, '两周内搞定高数期末');

    expect(find.byKey(const ValueKey('j02-fast-path-cta')), findsOneWidget);
  });

  testWidgets('fast-path submits ONLY the goal capture fields and walks '
      'into modeling chat', (tester) async {
    final repo = _RecordingUserRepository();
    final router = GoRouter(
      initialLocation: UserRoutes.personaOnboarding,
      routes: [
        GoRoute(
          path: UserRoutes.personaOnboarding,
          builder: (_, __) => const PersonaOnboardingScreen(),
        ),
        GoRoute(
          path: UserRoutes.modelingChat,
          builder: (_, __) => const Scaffold(body: Text('J02_MODELING_STUB')),
        ),
      ],
    );

    await pumpScreen(tester, repo: repo, router: router);
    await enterGoal(tester, '两周内搞定高数期末');

    await tester.tap(find.byKey(const ValueKey('j02-fast-path-cta')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(seconds: 1));

    expect(repo.submittedPayloads, hasLength(1));
    final payload = repo.submittedPayloads.single;
    expect(payload['learning_goal'], '两周内搞定高数期末');
    expect(payload['learning_goal_type'], 'exam');
    // 「其他信息延后」：四项偏好零上行——只问改变 first action 的问题。
    expect(
      payload.containsKey('learning_style'),
      isFalse,
      reason: '学习风格不改变 first action，快车道不上行',
    );
    expect(payload.containsKey('study_time_minutes'), isFalse);
    expect(payload.containsKey('knowledge_level'), isFalse);
    expect(payload.containsKey('response_depth'), isFalse);
    expect(payload.containsKey('curiosity_preference'), isFalse);

    expect(
      router.routeInformationProvider.value.uri.path,
      UserRoutes.modelingChat,
      reason: '快车道与全量提交同一续接面：modeling 访谈（对话化画像）',
    );
    expect(find.text('J02_MODELING_STUB'), findsOneWidget);
  });

  testWidgets('fast-path keeps the draft and resumes at the first '
      'deferred question', (tester) async {
    final repo = _RecordingUserRepository();
    await pumpScreen(tester, repo: repo);
    await enterGoal(tester, '两周内搞定高数期末');

    await tester.tap(find.byKey(const ValueKey('j02-fast-path-cta')));
    await tester.pump(const Duration(milliseconds: 500));

    final store = PersonaOnboardingDraftStore();
    final saved = await store.load(userId);
    expect(saved, isNotNull, reason: '延后问未答完，草稿必须保留');
    expect(saved?.step, 1, reason: '重进落在第一个延后问（学习风格），目标已入库不重问');
    expect(saved?.goalText, '两周内搞定高数期末');
  });

  testWidgets('fast-path failure surfaces visible feedback instead of '
      'pretending success', (tester) async {
    final repo = _RecordingUserRepository(failSubmit: true);
    await pumpScreen(tester, repo: repo);
    await enterGoal(tester, '两周内搞定高数期末');

    await tester.tap(find.byKey(const ValueKey('j02-fast-path-cta')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 诚实失败：仍在 persona 屏，提交失败反馈可见（SnackBar），不跳转。
    expect(find.byType(PersonaOnboardingScreen), findsOneWidget);
    expect(find.byType(SnackBar), findsOneWidget);
    expect(repo.submittedPayloads, hasLength(1));
  });
}

UserModel _user() => UserModel(
      id: userId,
      username: 'j02_fastpath',
      email: 'j02-fastpath@example.com',
      nickname: 'J02 FastPath',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _RecordingUserRepository extends UserRepository {
  _RecordingUserRepository({this.failSubmit = false})
      : super(_UnusedApiClient());

  final bool failSubmit;
  final List<Map<String, dynamic>> submittedPayloads = [];

  @override
  Future<Map<String, dynamic>> fetchOnboardingPreview(
    Map<String, dynamic> payload,
  ) async => <String, dynamic>{'message': 'J02_PREVIEW'};

  @override
  Future<String?> submitOnboarding(Map<String, dynamic> payload) async {
    submittedPayloads.add(Map<String, dynamic>.of(payload));
    if (failSubmit) {
      throw Exception('j02 fast-path stubbed submit failure');
    }
    return 'J02_FIRST_MESSAGE';
  }
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier(AuthState authState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = authState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository()
      : super(
          _UnusedApiClient(),
          SecureTokenStorage(storage: _MemorySecureStorage()),
        );
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MemorySecureStorage implements FlutterSecureStorage {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
