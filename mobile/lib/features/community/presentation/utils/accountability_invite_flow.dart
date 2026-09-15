import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';

String normalizeAccountabilityInviteError(Object error) {
  final rawMessage = error.toString();
  if (rawMessage.startsWith('Exception: ')) {
    return rawMessage.substring('Exception: '.length);
  }
  return rawMessage;
}

String resolveAcceptedAccountabilityRoute({
  required AccountabilityPartnershipInfo updated,
  AccountabilityOverviewInfo? overview,
}) {
  final activeId = overview?.activePartnership?.id;
  final targetId = (activeId != null && activeId.isNotEmpty)
      ? activeId
      : (updated.status == AccountabilityStatus.active ? updated.id : '');
  if (targetId.isEmpty) {
    return CommunityRoutes.accountability;
  }
  return CommunityRoutes.accountabilityDetail.replaceFirst(':id', targetId);
}

class AccountabilityInviteAcceptResolution {
  const AccountabilityInviteAcceptResolution({
    required this.updated,
    this.overview,
  });

  final AccountabilityPartnershipInfo updated;
  final AccountabilityOverviewInfo? overview;

  String get route => resolveAcceptedAccountabilityRoute(
        updated: updated,
        overview: overview,
      );
}

Future<AccountabilityInviteAcceptResolution>
    acceptAccountabilityInviteWithRefresh({
  required AccountabilityRepository repository,
  required String partnershipId,
  required Future<void> Function() reloadPartnerships,
  required Future<void> Function() refreshPendingRequests,
  required void Function() invalidateOverview,
}) async {
  final updated = await repository.respondToPartnership(
    partnershipId,
    accept: true,
  );
  await reloadPartnerships();
  await refreshPendingRequests();
  invalidateOverview();

  AccountabilityOverviewInfo? freshOverview;
  try {
    freshOverview = await repository.getOverview();
  } catch (_) {}

  return AccountabilityInviteAcceptResolution(
    updated: updated,
    overview: freshOverview,
  );
}

Future<void> declineAccountabilityInviteWithRefresh({
  required AccountabilityRepository repository,
  required String partnershipId,
  required Future<void> Function() reloadPartnerships,
  required Future<void> Function() refreshPendingRequests,
  required void Function() invalidateOverview,
}) async {
  await repository.respondToPartnership(partnershipId, accept: false);
  await reloadPartnerships();
  await refreshPendingRequests();
  invalidateOverview();
}

Future<String?> resolveExistingAccountabilityRouteOnConflict(
  AccountabilityRepository repository,
) async {
  try {
    final activePartnership = await repository
        .getOverview()
        .then((overview) => overview.activePartnership);
    if (activePartnership == null || activePartnership.id.isEmpty) {
      return null;
    }
    return CommunityRoutes.accountabilityDetail
        .replaceFirst(':id', activePartnership.id);
  } catch (_) {
    return null;
  }
}
