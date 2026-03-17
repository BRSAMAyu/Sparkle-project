import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';

// ─── My Partnerships ──────────────────────────────────────────────────────────

final myPartnershipsProvider = StateNotifierProvider.autoDispose<
    MyPartnershipsNotifier,
    AsyncValue<List<AccountabilityPartnershipInfo>>>((ref) {
  return MyPartnershipsNotifier(
      ref.watch(accountabilityRepositoryProvider),);
});

class MyPartnershipsNotifier extends StateNotifier<
    AsyncValue<List<AccountabilityPartnershipInfo>>> {
  MyPartnershipsNotifier(this._repo) : super(const AsyncValue.loading()) {
    load();
  }

  final AccountabilityRepository _repo;

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final list = await _repo.getMyPartnerships();
      state = AsyncValue.data(list);
    } catch (e, s) {
      state = AsyncValue.error(e, s);
    }
  }

  Future<void> endPartnership(String partnershipId) async {
    await _repo.endPartnership(partnershipId);
    state.whenData((list) {
      state = AsyncValue.data(
          list.where((p) => p.id != partnershipId).toList(),);
    });
  }

  Future<AccountabilityPartnershipInfo> requestPartnership({
    required String partnerId,
    required String initiatorGoal,
    int checkInDays = 1,
  }) async {
    final p = await _repo.requestPartnership(
      partnerId: partnerId,
      initiatorGoal: initiatorGoal,
      checkInDays: checkInDays,
    );
    state.whenData((list) => state = AsyncValue.data([...list, p]));
    return p;
  }
}

// ─── Partnership Stats (per ID) ───────────────────────────────────────────────

final partnershipStatsProvider = FutureProvider.autoDispose
    .family<AccountabilityStatsInfo, String>((ref, partnershipId) async {
  final repo = ref.watch(accountabilityRepositoryProvider);
  return repo.getStats(partnershipId);
});

// ─── Partnership Timeline (per ID) ────────────────────────────────────────────

final partnershipTimelineProvider = FutureProvider.autoDispose
    .family<List<AccountabilityCheckinInfo>, String>((ref, partnershipId) async {
  final repo = ref.watch(accountabilityRepositoryProvider);
  return repo.getTimeline(partnershipId);
});
