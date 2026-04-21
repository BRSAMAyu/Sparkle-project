import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_interceptor.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';
import 'package:sparkle/features/community/presentation/screens/accountability_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  testWidgets('detail screen shows pending policy summary count and next trigger',
      (tester) async {
    await _pumpHarness(
      tester,
      repository: _FakeAccountabilityRepository(
        pendingPolicies: PendingPoliciesSummaryInfo(
          count: 3,
          nextTriggerAt: DateTime(2026, 4, 22, 9, 30),
          policyIds: const ['p1', 'p2', 'p3'],
        ),
      ),
    );

    expect(find.text('待执行策略'), findsOneWidget);
    expect(find.text('3 条'), findsOneWidget);
    expect(find.textContaining('下一次触发在'), findsOneWidget);
  });

  testWidgets('detail screen renders zero-state policy summary', (tester) async {
    await _pumpHarness(
      tester,
      repository: _FakeAccountabilityRepository(
        pendingPolicies: PendingPoliciesSummaryInfo(count: 0),
      ),
    );

    expect(find.text('0 条'), findsOneWidget);
    expect(find.text('当前没有待执行的问责策略。'), findsOneWidget);
  });

  testWidgets('detail screen shows event-waiting copy when next trigger is empty',
      (tester) async {
    await _pumpHarness(
      tester,
      repository: _FakeAccountabilityRepository(
        pendingPolicies: PendingPoliciesSummaryInfo(
          count: 2,
          policyIds: const ['p1', 'p2'],
        ),
      ),
    );

    expect(find.text('2 条'), findsOneWidget);
    expect(find.textContaining('等待事件触发'), findsOneWidget);
  });
}

Future<void> _pumpHarness(
  WidgetTester tester, {
  required _FakeAccountabilityRepository repository,
}) async {
  final router = GoRouter(
    initialLocation: '/accountability/demo-1',
    routes: [
      GoRoute(
        path: '/accountability/:id',
        builder: (context, state) => AccountabilityDetailScreen(
          partnershipId: state.pathParameters['id']!,
        ),
      ),
    ],
  );
  addTearDown(router.dispose);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        accountabilityRepositoryProvider.overrideWithValue(repository),
        authProvider.overrideWith((ref) => _FakeAuthNotifier()),
      ],
      child: MaterialApp.router(
        routerConfig: router,
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
      ),
    ),
  );

  await tester.pumpAndSettle();
}

class _FakeAccountabilityRepository extends AccountabilityRepository {
  _FakeAccountabilityRepository({required this.pendingPolicies})
      : super(_UnusedApiClient());

  final PendingPoliciesSummaryInfo pendingPolicies;

  @override
  Future<AccountabilityDashboardInfo> getDashboard(String partnershipId) async {
    return AccountabilityDashboardInfo(
      partnership: AccountabilityPartnershipInfo(
        id: partnershipId,
        initiatorId: 'me',
        partnerId: 'partner-1',
        initiatorGoal: '完成这周复盘',
        partnerGoal: '每天互相确认一次进度',
        checkInDays: 1,
        status: AccountabilityStatus.active,
        createdAt: DateTime(2026, 4, 1, 9),
        startedAt: DateTime(2026, 4, 1, 9),
        initiator: UserBrief(id: 'me', username: 'me', nickname: 'Me'),
        partner:
            UserBrief(id: 'partner-1', username: 'alice', nickname: 'Alice'),
        myCheckedInToday: false,
        partnerCheckedInToday: true,
      ),
      stats: AccountabilityStatsInfo(
        myStreakDays: 5,
        partnerStreakDays: 4,
        myCheckedInToday: false,
        partnerCheckedInToday: true,
        totalCheckins: 9,
      ),
      pendingPolicies: pendingPolicies,
      achievements: const {'achievements': []},
      leaderboardSummary: const {},
      relationshipSummary: const {},
      recentShares: const [],
      quickActions: const {
        'can_check_in': true,
        'can_nudge': true,
        'can_share': true,
        'can_chat': true,
        'can_open_dashboard': true,
      },
    );
  }
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: UserModel(
        id: 'me',
        username: 'me',
        email: 'me@example.com',
        nickname: 'Me',
        flameLevel: 1,
        flameBrightness: 0.2,
        depthPreference: 0.5,
        curiosityPreference: 0.5,
        isActive: true,
        createdAt: DateTime(2026, 4, 1, 9),
        updatedAt: DateTime(2026, 4, 21, 9),
      ),
    );
  }
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository()
      : super(_UnusedApiClient(), const FlutterSecureStorage());
}

class _UnusedRef implements Ref<Object?> {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == AuthInterceptor) {
      return AuthInterceptor(this) as T;
    }
    if (T == LoggingInterceptor) {
      return LoggingInterceptor() as T;
    }
    if (T == RetryInterceptor) {
      return RetryInterceptor(dio: Dio()) as T;
    }
    if (provider.toString().contains('RetryInterceptor')) {
      return RetryInterceptor(dio: Dio()) as T;
    }
    if (provider == authInterceptorProvider) {
      return AuthInterceptor(this) as T;
    }
    if (provider == loggingInterceptorProvider) {
      return LoggingInterceptor() as T;
    }
    if (provider == authRepositoryProvider) {
      return _UnusedAuthRepository() as T;
    }
    throw UnsupportedError('Unsupported provider in test: $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient extends ApiClient {
  _UnusedApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
