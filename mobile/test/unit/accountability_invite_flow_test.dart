import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_interceptor.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';
import 'package:sparkle/features/community/presentation/utils/accountability_invite_flow.dart';

void main() {
  group('accountability invite flow helpers', () {
    test('prefers active partnership route after accepting invite', () {
      final updated = AccountabilityPartnershipInfo(
        id: 'pending-1',
        initiatorId: 'initiator',
        partnerId: 'partner',
        initiatorGoal: 'goal',
        checkInDays: 1,
        status: AccountabilityStatus.active,
        createdAt: DateTime(2026, 3, 29),
      );
      final overview = AccountabilityOverviewInfo(
        slotType: 'core',
        activePartnership: AccountabilityPartnershipInfo(
          id: 'active-42',
          initiatorId: 'initiator',
          partnerId: 'partner',
          initiatorGoal: 'goal',
          checkInDays: 1,
          status: AccountabilityStatus.active,
          createdAt: DateTime(2026, 3, 29),
        ),
        pendingPartnerships: const [],
      );

      expect(
        resolveAcceptedAccountabilityRoute(
          updated: updated,
          overview: overview,
        ),
        CommunityRoutes.accountabilityDetail.replaceFirst(':id', 'active-42'),
      );
    });

    test('falls back to accountability home when no active route is available',
        () {
      final updated = AccountabilityPartnershipInfo(
        id: 'pending-1',
        initiatorId: 'initiator',
        partnerId: 'partner',
        initiatorGoal: 'goal',
        checkInDays: 1,
        status: AccountabilityStatus.pending,
        createdAt: DateTime(2026, 3, 29),
      );

      expect(
        resolveAcceptedAccountabilityRoute(updated: updated),
        CommunityRoutes.accountability,
      );
    });

    test('normalizes repository exception prefix for user feedback', () {
      expect(
        normalizeAccountabilityInviteError(Exception('boom')),
        'boom',
      );
      expect(
        normalizeAccountabilityInviteError('plain error'),
        'plain error',
      );
    });

    test('accept helper refreshes state and prefers overview active route',
        () async {
      final repo = _FakeAccountabilityRepository(
        accepted: AccountabilityPartnershipInfo(
          id: 'pending-1',
          initiatorId: 'i',
          partnerId: 'p',
          initiatorGoal: 'goal',
          checkInDays: 1,
          status: AccountabilityStatus.active,
          createdAt: DateTime(2026, 3, 29),
        ),
        overview: AccountabilityOverviewInfo(
          slotType: 'core',
          activePartnership: AccountabilityPartnershipInfo(
            id: 'active-7',
            initiatorId: 'i',
            partnerId: 'p',
            initiatorGoal: 'goal',
            checkInDays: 1,
            status: AccountabilityStatus.active,
            createdAt: DateTime(2026, 3, 29),
          ),
        ),
      );
      var reloadCount = 0;
      var refreshCount = 0;
      var invalidated = false;

      final resolution = await acceptAccountabilityInviteWithRefresh(
        repository: repo,
        partnershipId: 'pending-1',
        reloadPartnerships: () async => reloadCount += 1,
        refreshPendingRequests: () async => refreshCount += 1,
        invalidateOverview: () => invalidated = true,
      );

      expect(repo.lastRespondAccept, isTrue);
      expect(reloadCount, 1);
      expect(refreshCount, 1);
      expect(invalidated, isTrue);
      expect(
        resolution.route,
        CommunityRoutes.accountabilityDetail.replaceFirst(':id', 'active-7'),
      );
    });

    test('decline helper refreshes all dependent providers', () async {
      final repo = _FakeAccountabilityRepository(
        accepted: AccountabilityPartnershipInfo(
          id: 'pending-1',
          initiatorId: 'i',
          partnerId: 'p',
          initiatorGoal: 'goal',
          checkInDays: 1,
          status: AccountabilityStatus.ended,
          createdAt: DateTime(2026, 3, 29),
        ),
      );
      var reloadCount = 0;
      var refreshCount = 0;
      var invalidated = false;

      await declineAccountabilityInviteWithRefresh(
        repository: repo,
        partnershipId: 'pending-1',
        reloadPartnerships: () async => reloadCount += 1,
        refreshPendingRequests: () async => refreshCount += 1,
        invalidateOverview: () => invalidated = true,
      );

      expect(repo.lastRespondAccept, isFalse);
      expect(reloadCount, 1);
      expect(refreshCount, 1);
      expect(invalidated, isTrue);
    });

    test('conflict helper returns active workspace route when available',
        () async {
      final route = await resolveExistingAccountabilityRouteOnConflict(
        _FakeAccountabilityRepository(
          accepted: AccountabilityPartnershipInfo(
            id: 'pending-1',
            initiatorId: 'i',
            partnerId: 'p',
            initiatorGoal: 'goal',
            checkInDays: 1,
            status: AccountabilityStatus.pending,
            createdAt: DateTime(2026, 3, 29),
          ),
          overview: AccountabilityOverviewInfo(
            slotType: 'core',
            activePartnership: AccountabilityPartnershipInfo(
              id: 'active-9',
              initiatorId: 'i',
              partnerId: 'p',
              initiatorGoal: 'goal',
              checkInDays: 1,
              status: AccountabilityStatus.active,
              createdAt: DateTime(2026, 3, 29),
            ),
          ),
        ),
      );

      expect(
        route,
        CommunityRoutes.accountabilityDetail.replaceFirst(':id', 'active-9'),
      );
    });
  });
}

class _FakeAccountabilityRepository extends AccountabilityRepository {
  _FakeAccountabilityRepository({
    required this.accepted,
    this.overview,
  }) : super(_UnusedApiClient());

  final AccountabilityPartnershipInfo accepted;
  final AccountabilityOverviewInfo? overview;
  bool? lastRespondAccept;

  @override
  Future<AccountabilityPartnershipInfo> respondToPartnership(
    String partnershipId, {
    required bool accept,
    String? partnerGoal,
  }) async {
    lastRespondAccept = accept;
    return accepted;
  }

  @override
  Future<AccountabilityOverviewInfo> getOverview() async {
    if (overview == null) {
      throw Exception('no overview');
    }
    return overview!;
  }
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
    throw UnsupportedError('Unsupported provider in test: $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient extends ApiClient {
  _UnusedApiClient() : super(_UnusedRef());
}
