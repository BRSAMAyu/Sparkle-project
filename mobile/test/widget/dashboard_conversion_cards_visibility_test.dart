import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/shared/entities/user_model.dart';

import '../features/home/dashboard_test_harness.dart';
import '../shared/i18n_test_helper.dart';

/// wt287 · 转化卡挂载盲区修复的回归守卫。
///
/// 背景：GuestConversionCard 原挂 growthSections，而 hasNoGoals 时
/// growthSections 整体不渲染——「没有目标的新访客」恰是转化卡主受众，
/// 却永远看不到卡。修复后卡挂 dashboardSections（两分支均渲染）。
///
/// 三个断面：
/// 1. guest + 价值信号 + 无目标 → 转化卡可见（盲区修复本体），
///    resume 卡不可见（guest 轴互斥，即使 completed==false 也隐藏）；
/// 2. 已认证非 guest + 未完成引导 + （甚至有访客信号）→ resume 卡可见，
///    转化卡不可见（注册用户永不被转化骚扰）；
/// 3. guest + 价值信号 + 有目标 → 转化卡仍可见（迁移回归向：挂载点
///    从 growthSections 移出后，有目标的访客不丢卡）。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  // 访客断面全量覆盖：guest 身份（auth + currentUser 双轴）+ 价值信号
  // 已触发（controller 软降级注入，绕开 prefs 单例陷阱）。
  List<Override> guestOverrides({required MultiGoalOverview overview}) => [
        authProvider.overrideWith((ref) => _GuestAuthNotifier()),
        currentUserProvider.overrideWith((ref) => _buildGuestUser()),
        guestConversionControllerProvider.overrideWith(
          (ref) => GuestConversionController(ref, null)
            ..state = const GuestConversionState(signalCount: 1),
        ),
        multiGoalOverviewProvider.overrideWith((ref) async => overview),
      ];

  testWidgets('盲区修复：guest+信号+无目标 → 转化卡可见、resume 卡不可见',
      (tester) async {
    await initializeDashboardTestEnvironment();
    await tester.pumpWidget(
      buildDashboardTestHarness(
        extraOverrides: guestOverrides(
          overview: const MultiGoalOverview.empty(),
        )
          // completed=false 强化互斥：resume 卡自身条件成立（非 guest 才可见）
          // 的前置即便满足，guest 轴仍把它钉死在隐藏态。
          ..add(
            onboardingCompletedProvider.overrideWith(
              _OnboardingIncompleteNotifier.new,
            ),
          ),
      ),
    );
    await _pumpDashboard(tester);

    const conversionTitle = 'Your exam prep progress is saved on this device';
    // scrollUntilVisible 先探再滚：找不到即抛错，本身就是「卡存在」断言。
    await tester.scrollUntilVisible(
      find.text(conversionTitle),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await _pumpDashboard(tester);
    expect(find.text(conversionTitle), findsOneWidget);
    expect(find.text('Register to sync progress'), findsOneWidget);

    // 互斥：guest 永不见 resume 卡（标题与 CTA 双锚点）。
    expect(
      find.text('Finish setup so Sparkle knows you better'),
      findsNothing,
      reason: 'guest 走转化卡，resume 卡对 guest 恒隐藏',
    );
    expect(find.text('Continue setup'), findsNothing);
  });

  testWidgets('互斥：已认证未完成引导 → resume 卡可见、转化卡不可见',
      (tester) async {
    await initializeDashboardTestEnvironment();
    await tester.pumpWidget(
      buildDashboardTestHarness(
        extraOverrides: [
          // harness 默认注册用户（非 guest），无需改 auth 轴；completed=false
          // 是 resume 卡唯一额外条件。信号照常注入——证明「非 guest 即使有
          // 价值信号也不见转化卡」。
          guestConversionControllerProvider.overrideWith(
            (ref) => GuestConversionController(ref, null)
              ..state = const GuestConversionState(signalCount: 1),
          ),
          onboardingCompletedProvider.overrideWith(
            _OnboardingIncompleteNotifier.new,
          ),
          multiGoalOverviewProvider.overrideWith(
            (ref) async => const MultiGoalOverview.empty(),
          ),
        ],
      ),
    );
    await _pumpDashboard(tester);

    const resumeTitle = 'Finish setup so Sparkle knows you better';
    await tester.scrollUntilVisible(
      find.text(resumeTitle),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await _pumpDashboard(tester);
    expect(find.text(resumeTitle), findsOneWidget);
    expect(find.text('Continue setup'), findsOneWidget);

    expect(
      find.text('Your exam prep progress is saved on this device'),
      findsNothing,
      reason: '注册用户不是转化对象，转化卡恒隐藏',
    );
    expect(find.text('Register to sync progress'), findsNothing);
  });

  testWidgets('迁移回归：guest+信号+有目标 → 转化卡仍可见', (tester) async {
    await initializeDashboardTestEnvironment();
    await tester.pumpWidget(
      buildDashboardTestHarness(
        extraOverrides: guestOverrides(
          overview: const MultiGoalOverview(
            goals: [
              ActiveGoalSnapshot(
                id: 'goal-1',
                title: 'Pass the final exam',
                goalType: 'exam',
                healthScore: 0.8,
                weeklyConflictCount: 0,
              ),
            ],
            selectedGoalId: 'goal-1',
          ),
        ),
      ),
    );
    await _pumpDashboard(tester);

    const conversionTitle = 'Your exam prep progress is saved on this device';
    await tester.scrollUntilVisible(
      find.text(conversionTitle),
      240,
      scrollable: find.byType(Scrollable).first,
    );
    await _pumpDashboard(tester);
    expect(find.text(conversionTitle), findsOneWidget);
  });
}

Future<void> _pumpDashboard(WidgetTester tester) async {
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

UserModel _buildGuestUser() {
  final now = DateTime(2026, 9, 22);
  return UserModel(
    id: '00000000-0000-0000-0000-000000000002',
    username: 'guest_dashboard_user',
    email: 'guest@example.com',
    flameLevel: 1,
    flameBrightness: 0.5,
    depthPreference: 0.5,
    curiosityPreference: 0.5,
    isActive: true,
    registrationSource: 'guest',
    createdAt: now,
    updatedAt: now,
  );
}

class _GuestAuthNotifier extends AuthNotifier {
  _GuestAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: _buildGuestUser(),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
}

/// 与 harness 的 _StaticOnboardingCompletedNotifier 同形，钉 completed=false
/// （引导未完成的注册用户是 resume 卡主受众）。
class _OnboardingIncompleteNotifier extends OnboardingCompletedNotifier {
  _OnboardingIncompleteNotifier(super.ref) {
    state = false;
  }

  @override
  Future<void> syncForUser(UserModel? user) async {
    state = false;
  }

  @override
  Future<void> setCompleted(bool value) async {
    state = value;
  }
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
