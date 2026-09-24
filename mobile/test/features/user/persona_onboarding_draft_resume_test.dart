import 'dart:convert';

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

/// J-02（A-SPEC8B §5 改造 #3 / N50 前半）· persona 引导进度断点续存。
///
/// 钉住三层语义：
/// 1. store 往返：save→load 等值；损坏 JSON 视为无草稿；clamp 钳住越界值；
/// 2. 屏恢复：杀进程重进（新 mount）从断点步续，不重填已选内容；
/// 3. 生命周期：步进即落盘；跳过清除草稿（用户显式放弃逐页引导）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const userId = 'j02-persona-user';
  final draftKey = PersonaOnboardingDraftStore.keyForUser(userId);

  PersonaOnboardingDraft draftFor(Map<String, dynamic> patch) =>
      PersonaOnboardingDraft.fromJson(
        <String, dynamic>{
          'step': 0,
          'goal_type': 'exam',
          'goal_text': '',
          'learning_style': 'balanced',
          'knowledge_level': 'beginner',
          'study_minutes': 60,
          'depth_preference': 0.5,
          'curiosity_preference': 0.5,
        }..addAll(patch),
      );

  group('PersonaOnboardingDraftStore (unit)', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('save→load roundtrip preserves every field', () async {
      final store = PersonaOnboardingDraftStore();
      const draft = PersonaOnboardingDraft(
        step: 3,
        goalType: 'skill',
        goalText: '两周内搞定高数期末',
        learningStyle: 'visual',
        knowledgeLevel: 'intermediate',
        studyMinutes: 90,
        depthPreference: 0.7,
        curiosityPreference: 0.2,
      );

      await store.save(userId, draft);
      final loaded = await store.load(userId);

      expect(loaded, isNotNull);
      expect(loaded?.step, 3);
      expect(loaded?.goalType, 'skill');
      expect(loaded?.goalText, '两周内搞定高数期末');
      expect(loaded?.learningStyle, 'visual');
      expect(loaded?.knowledgeLevel, 'intermediate');
      expect(loaded?.studyMinutes, 90);
      expect(loaded?.depthPreference, 0.7);
      expect(loaded?.curiosityPreference, 0.2);
    });

    test('corrupted draft degrades to null instead of crashing restore',
        () async {
      SharedPreferences.setMockInitialValues({draftKey: '{not-json'});
      final store = PersonaOnboardingDraftStore();

      expect(await store.load(userId), isNull);
    });

    test('clamp pins out-of-range step and slider values', () {
      final clamped = draftFor({
        'step': 99,
        'study_minutes': 9999,
        'depth_preference': 42.0,
        'curiosity_preference': -7.0,
      }).clamp();

      expect(clamped.step, 4);
      expect(clamped.studyMinutes, 180);
      expect(clamped.depthPreference, 1.0);
      expect(clamped.curiosityPreference, 0.0);
    });

    test('clear removes the per-user draft', () async {
      final store = PersonaOnboardingDraftStore();
      await store.save(userId, draftFor(const {}));
      await store.clear(userId);

      expect(await store.load(userId), isNull);
    });
  });

  group('PersonaOnboardingScreen draft resume (widget)', () {
    setUp(setUpI18nForTesting);

    Future<void> pumpScreen(
      WidgetTester tester, {
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
            userRepositoryProvider.overrideWithValue(_StubUserRepository()),
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

    testWidgets('restores breakpoint step and previously filled content',
        (tester) async {
      SharedPreferences.setMockInitialValues({
        draftKey: jsonEncode(
          draftFor({
            'step': 2,
            'goal_text': '两周内搞定高数期末',
            'learning_style': 'visual',
            'study_minutes': 90,
          }).toJson(),
        ),
      });

      await pumpScreen(tester);

      final stepper =
          tester.widgetList<Stepper>(find.byType(Stepper)).first;
      expect(
        stepper.currentStep,
        2,
        reason: '中断在第 3 步（学习时长），重进应续步',
      );
      expect(
        find.text('两周内搞定高数期末'),
        findsOneWidget,
        reason: '已填目标文本必须恢复，不要求重填',
      );
    });

    testWidgets('advancing a step persists the draft immediately',
        (tester) async {
      SharedPreferences.setMockInitialValues({});
      final store = PersonaOnboardingDraftStore();

      await pumpScreen(tester);

      await tester.tap(find.text('下一步').hitTestable().first);
      await tester.pump(const Duration(milliseconds: 400));

      final saved = await store.load(userId);
      expect(saved?.step, 1);
    });

    testWidgets('skip clears the draft and walks into modeling chat',
        (tester) async {
      SharedPreferences.setMockInitialValues({
        draftKey: jsonEncode(draftFor({'step': 1}).toJson()),
      });
      final store = PersonaOnboardingDraftStore();
      final router = GoRouter(
        initialLocation: UserRoutes.personaOnboarding,
        routes: [
          GoRoute(
            path: UserRoutes.personaOnboarding,
            builder: (_, __) => const PersonaOnboardingScreen(),
          ),
          GoRoute(
            path: UserRoutes.modelingChat,
            builder: (_, __) =>
                const Scaffold(body: Text('J02_MODELING_STUB')),
          ),
        ],
      );

      await pumpScreen(tester, router: router);

      await tester.tap(find.text('跳过'));
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pump(const Duration(seconds: 1));

      expect(await store.load(userId), isNull, reason: '跳过=显式放弃，草稿应清除');
      expect(
        router.routeInformationProvider.value.uri.path,
        UserRoutes.modelingChat,
      );
      expect(find.text('J02_MODELING_STUB'), findsOneWidget);
    });
  });
}

UserModel _user() => UserModel(
      id: 'j02-persona-user',
      username: 'j02_tester',
      email: 'j02@example.com',
      nickname: 'J02 Tester',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier(AuthState authState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = authState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _StubUserRepository extends UserRepository {
  _StubUserRepository() : super(_UnusedApiClient());

  @override
  Future<Map<String, dynamic>> fetchOnboardingPreview(
    Map<String, dynamic> payload,
  ) async => <String, dynamic>{'message': 'J02_PREVIEW'};
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
