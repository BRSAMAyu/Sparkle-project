import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_interceptor.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/community/presentation/screens/accountability_screen.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('accepting invite lands on the active accountability workspace',
      (tester) async {
    final accountabilityRepo = _FakeAccountabilityRepository();
    final communityRepo = _FakeCommunityRepository();

    await _pumpHarness(
      tester,
      accountabilityRepo: accountabilityRepo,
      communityRepo: communityRepo,
    );

    expect(find.text('接受'), findsOneWidget);
    await tester.tap(find.text('接受'));
    await tester.pumpAndSettle();

    expect(accountabilityRepo.acceptedIds, ['pending-1']);
    expect(accountabilityRepo.overviewFetchCount, greaterThanOrEqualTo(1));
    expect(communityRepo.pendingRefreshCount, greaterThanOrEqualTo(1));
    expect(find.text('detail-route:active-9'), findsOneWidget);
  });

  testWidgets('declining invite refreshes state without blanking the screen',
      (tester) async {
    final accountabilityRepo = _FakeAccountabilityRepository();
    final communityRepo = _FakeCommunityRepository();

    await _pumpHarness(
      tester,
      accountabilityRepo: accountabilityRepo,
      communityRepo: communityRepo,
    );

    expect(find.text('拒绝'), findsOneWidget);
    await tester.tap(find.text('拒绝'));
    await tester.pumpAndSettle();

    expect(accountabilityRepo.declinedIds, ['pending-1']);
    expect(communityRepo.pendingRefreshCount, greaterThanOrEqualTo(1));
    expect(find.byType(AccountabilityScreen), findsOneWidget);
    expect(find.text('责任伙伴'), findsOneWidget);
    expect(find.text('接受'), findsNothing);
  });
}

Future<void> _pumpHarness(
  WidgetTester tester, {
  required _FakeAccountabilityRepository accountabilityRepo,
  required _FakeCommunityRepository communityRepo,
}) async {
  final router = GoRouter(
    initialLocation: CommunityRoutes.accountability,
    routes: [
      GoRoute(
        path: CommunityRoutes.accountability,
        builder: (context, state) => const AccountabilityScreen(),
      ),
      GoRoute(
        path: CommunityRoutes.accountabilityDetail,
        builder: (context, state) => Scaffold(
          body: Text('detail-route:${state.pathParameters['id']}'),
        ),
      ),
    ],
  );
  addTearDown(router.dispose);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        authProvider.overrideWith((ref) => _FakeAuthNotifier()),
        accountabilityRepositoryProvider.overrideWithValue(accountabilityRepo),
        communityRepositoryProvider.overrideWithValue(communityRepo),
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
  _FakeAccountabilityRepository() : super(_UnusedApiClient());

  final List<String> acceptedIds = <String>[];
  final List<String> declinedIds = <String>[];
  int overviewFetchCount = 0;
  bool _accepted = false;
  bool _declined = false;

  @override
  Future<List<AccountabilityPartnershipInfo>> getMyPartnerships() async {
    if (_declined) {
      return const <AccountabilityPartnershipInfo>[];
    }
    final pending = AccountabilityPartnershipInfo(
      id: 'pending-1',
      initiatorId: 'partner-1',
      partnerId: 'me',
      initiatorGoal: '一起完成星图任务卡',
      checkInDays: 1,
      status: _accepted
          ? AccountabilityStatus.active
          : AccountabilityStatus.pending,
      createdAt: DateTime(2026, 3, 29),
      startedAt: _accepted ? DateTime(2026, 3, 29, 9) : null,
      initiator: UserBrief(
        id: 'partner-1',
        username: 'alice',
        nickname: 'Alice',
      ),
      partner: UserBrief(
        id: 'me',
        username: 'me',
        nickname: 'Me',
      ),
    );
    if (_accepted) {
      return <AccountabilityPartnershipInfo>[
        AccountabilityPartnershipInfo(
          id: 'active-9',
          initiatorId: 'partner-1',
          partnerId: 'me',
          initiatorGoal: '一起完成星图任务卡',
          checkInDays: 1,
          status: AccountabilityStatus.active,
          createdAt: DateTime(2026, 3, 29),
          startedAt: DateTime(2026, 3, 29, 9),
          initiator: pending.initiator,
          partner: pending.partner,
        ),
      ];
    }
    return <AccountabilityPartnershipInfo>[pending];
  }

  @override
  Future<AccountabilityPartnershipInfo> respondToPartnership(
    String partnershipId, {
    required bool accept,
    String? partnerGoal,
  }) async {
    if (accept) {
      acceptedIds.add(partnershipId);
      _accepted = true;
      _declined = false;
      return AccountabilityPartnershipInfo(
        id: partnershipId,
        initiatorId: 'partner-1',
        partnerId: 'me',
        initiatorGoal: '一起完成星图任务卡',
        checkInDays: 1,
        status: AccountabilityStatus.active,
        createdAt: DateTime(2026, 3, 29),
        startedAt: DateTime(2026, 3, 29, 9),
      );
    }
    declinedIds.add(partnershipId);
    _accepted = false;
    _declined = true;
    return AccountabilityPartnershipInfo(
      id: partnershipId,
      initiatorId: 'partner-1',
      partnerId: 'me',
      initiatorGoal: '一起完成星图任务卡',
      checkInDays: 1,
      status: AccountabilityStatus.ended,
      createdAt: DateTime(2026, 3, 29),
      endedAt: DateTime(2026, 3, 29, 9, 5),
    );
  }

  @override
  Future<AccountabilityOverviewInfo> getOverview() async {
    overviewFetchCount += 1;
    return AccountabilityOverviewInfo(
      slotType: 'core',
      pendingPartnerships: _declined
          ? const <AccountabilityPartnershipInfo>[]
          : <AccountabilityPartnershipInfo>[
              AccountabilityPartnershipInfo(
                id: 'pending-1',
                initiatorId: 'partner-1',
                partnerId: 'me',
                initiatorGoal: '一起完成星图任务卡',
                checkInDays: 1,
                status: AccountabilityStatus.pending,
                createdAt: DateTime(2026, 3, 29),
              ),
            ],
      activePartnership: _accepted
          ? AccountabilityPartnershipInfo(
              id: 'active-9',
              initiatorId: 'partner-1',
              partnerId: 'me',
              initiatorGoal: '一起完成星图任务卡',
              checkInDays: 1,
              status: AccountabilityStatus.active,
              createdAt: DateTime(2026, 3, 29),
              startedAt: DateTime(2026, 3, 29, 9),
            )
          : null,
    );
  }
}

class _FakeCommunityRepository extends CommunityRepository {
  _FakeCommunityRepository() : super(_UnusedApiClient());

  int pendingRefreshCount = 0;

  @override
  Future<List<FriendshipInfo>> getPendingRequests() async {
    pendingRefreshCount += 1;
    return const <FriendshipInfo>[];
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
        flameBrightness: 0.5,
        depthPreference: 0.5,
        curiosityPreference: 0.5,
        isActive: true,
        createdAt: DateTime(2026, 3, 29),
        updatedAt: DateTime(2026, 3, 29),
      ),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
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
}
