import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/community/data/models/community_accountability_hub_model.dart';
import 'package:sparkle/features/community/data/repositories/community_accountability_repository.dart';

final accountabilityHubProvider = StateNotifierProvider<
    AccountabilityHubNotifier, AsyncValue<CommunityAccountabilityHub>>(
  (ref) => AccountabilityHubNotifier(
    ref.watch(communityAccountabilityRepositoryProvider),
  ),
);

class AccountabilityHubNotifier
    extends StateNotifier<AsyncValue<CommunityAccountabilityHub>> {
  AccountabilityHubNotifier(this._repository)
      : super(const AsyncValue.loading()) {
    unawaited(refresh());
  }

  final CommunityAccountabilityRepository _repository;

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    try {
      state = AsyncValue.data(await _repository.getHub());
    } catch (error, stackTrace) {
      state = AsyncValue.error(error, stackTrace);
    }
  }

  void setReminderBoundary(String commitmentId, bool allowReminders) {
    final hub = state.valueOrNull;
    if (hub == null) return;
    state = AsyncValue.data(
      hub.copyWith(
        myCommitments: [
          for (final item in hub.myCommitments)
            if (item.id == commitmentId)
              item.copyWith(allowPartnerReminders: allowReminders)
            else
              item,
        ],
      ),
    );
  }

  void restoreCommitment(CommitmentCardPayload commitment) {
    final hub = state.valueOrNull;
    if (hub == null) return;
    state = AsyncValue.data(
      hub.copyWith(
        myCommitments: [
          for (final item in hub.myCommitments)
            if (item.id == commitment.id) commitment else item,
        ],
      ),
    );
  }
}
