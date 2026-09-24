import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_card.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/home/presentation/widgets/onboarding_resume_card.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// J-02（A-SPEC8B G1 软化）· OnboardingResumeCard 可见性守门与入口导航。
///
/// 注册墙改「放行 + 提醒」后，本卡是首页侧的提醒职责承载：
/// - 仅注册用户且 onboardingCompleted == false 可见（completed==null 视为
///   同步未决，同样不可见，对齐 M6-07「未决不做引导跳转」语义）；
/// - guest 恒不可见（guest 走 N40 转化卡，两卡互斥）；
/// - CTA 跳 persona 引导（价值体验随时可回）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
  });

  Future<void> pumpCard(
    WidgetTester tester, {
    required AuthState authState,
    required bool? onboardingCompleted,
  }) async {
    final router = GoRouter(
      initialLocation: '/home',
      routes: [
        GoRoute(
          path: '/home',
          builder: (_, __) =>
              const Scaffold(body: Center(child: OnboardingResumeCard())),
        ),
        GoRoute(
          path: UserRoutes.personaOnboarding,
          builder: (_, __) =>
              const Scaffold(body: Text('J02_PERSONA_STUB')),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          authProvider.overrideWith((ref) => _FakeAuthNotifier(authState)),
          onboardingCompletedProvider.overrideWith(
            (ref) => _StaticOnboardingCompletedNotifier(
              ref,
              onboardingCompleted,
            ),
          ),
        ],
        child: testMaterialApp(routerConfig: router),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
  }

  testWidgets('visible for registrant with pending onboarding; CTA walks '
      'into persona flow', (tester) async {
    await pumpCard(
      tester,
      authState: AuthState(isAuthenticated: true, user: _buildUser()),
      onboardingCompleted: false,
    );

    expect(find.text('完成引导，让 AI 更懂你'), findsOneWidget);
    expect(find.text('继续引导'), findsOneWidget);
    expect(find.byType(SparkleCard), findsOneWidget);
    // F-8（wt324 证据包）：首页唯一 Primary Action 归属 cockpit 本卡 CTA
    // 锁定为 ghost 档（tonal 视觉权重），不得回升为 primary 填充。
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is SparkleButton &&
            widget.variant == ButtonVariant.primary,
        description: 'J-02 primary CTA（F-8 后应为零）',
      ),
      findsNothing,
    );
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is SparkleButton && widget.variant == ButtonVariant.ghost,
        description: 'J-02 ghost CTA',
      ),
      findsOneWidget,
    );

    await tester.tap(find.text('继续引导'));
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(seconds: 1));

    expect(find.text('J02_PERSONA_STUB'), findsOneWidget);
  });

  testWidgets('hidden when onboarding already completed', (tester) async {
    await pumpCard(
      tester,
      authState: AuthState(isAuthenticated: true, user: _buildUser()),
      onboardingCompleted: true,
    );

    expect(find.byType(SparkleCard), findsNothing);
    expect(find.text('完成引导，让 AI 更懂你'), findsNothing);
  });

  testWidgets('hidden while onboarding state is unresolved (null)',
      (tester) async {
    await pumpCard(
      tester,
      authState: AuthState(isAuthenticated: true, user: _buildUser()),
      onboardingCompleted: null,
    );

    expect(find.byType(SparkleCard), findsNothing);
  });

  testWidgets('hidden for guests (N40 conversion card territory)',
      (tester) async {
    final guest = UserModel(
      id: 'j02-guest-user',
      username: 'guest_j02',
      email: 'guest.j02@example.com',
      nickname: 'Guest J02',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
      registrationSource: 'guest',
    );
    await pumpCard(
      tester,
      authState: AuthState(isAuthenticated: true, user: guest),
      onboardingCompleted: false,
    );

    expect(find.byType(SparkleCard), findsNothing);
    expect(find.text('继续引导'), findsNothing);
  });
}

UserModel _buildUser() => UserModel(
      id: 'j02-resume-user',
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

class _StaticOnboardingCompletedNotifier extends OnboardingCompletedNotifier {
  _StaticOnboardingCompletedNotifier(super.ref, this._value) {
    state = _value;
  }

  final bool? _value;

  @override
  Future<void> syncForUser(UserModel? user) async {
    state = _value;
  }

  @override
  Future<void> setCompleted(bool value) async {
    state = value;
  }
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
