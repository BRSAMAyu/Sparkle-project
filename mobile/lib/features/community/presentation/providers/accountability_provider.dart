import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';

// ─── My Partnerships ──────────────────────────────────────────────────────────

final myPartnershipsProvider = StateNotifierProvider.autoDispose<
    MyPartnershipsNotifier, AsyncValue<List<AccountabilityPartnershipInfo>>>(
  (ref) => MyPartnershipsNotifier(
    ref.watch(accountabilityRepositoryProvider),
  ),
);

final accountabilityOverviewProvider =
    FutureProvider.autoDispose<AccountabilityOverviewInfo>((ref) async {
  final repo = ref.watch(accountabilityRepositoryProvider);
  return repo.getOverview();
});

final accountabilityDashboardProvider = FutureProvider.autoDispose
    .family<AccountabilityDashboardInfo, String>((ref, partnershipId) async {
  final repo = ref.watch(accountabilityRepositoryProvider);
  return repo.getDashboard(partnershipId);
});

class MyPartnershipsNotifier
    extends StateNotifier<AsyncValue<List<AccountabilityPartnershipInfo>>> {
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
        list.where((p) => p.id != partnershipId).toList(),
      );
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
    .family<List<AccountabilityCheckinInfo>, String>(
        (ref, partnershipId) async {
  final repo = ref.watch(accountabilityRepositoryProvider);
  return repo.getTimeline(partnershipId);
});

// ─── Partnership Heatmap (per ID) ───────────────────────────────────────────────

final partnershipHeatmapProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String>((ref, partnershipId) async {
  final repo = ref.watch(accountabilityRepositoryProvider);
  return repo.getHeatmap(partnershipId);
});

final partnershipHeatmapYearProvider =
    Provider.family<int, int>((ref, _) => DateTime.now().year);

// ─── Achievements ────────────────────────────────────────────────────────────────

final accountabilityAchievementsProvider =
    FutureProvider.autoDispose((ref) async {
  final repo = ref.watch(accountabilityRepositoryProvider);
  return repo.getAchievements();
});

final partnershipAchievementsProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String>((ref, partnershipId) async {
  final repo = ref.watch(accountabilityRepositoryProvider);
  return repo.getPartnershipAchievements(partnershipId);
});

// ─── Check-in Interactions ───────────────────────────────────────────────────────

class CheckinInteractionState {
  const CheckinInteractionState({
    this.liked = false,
    this.likes = 0,
    this.encouragements = const [],
  });

  final bool liked;
  final int likes;
  final List<EncouragementMessage> encouragements;

  CheckinInteractionState copyWith({
    bool? liked,
    int? likes,
    List<EncouragementMessage>? encouragements,
  }) =>
      CheckinInteractionState(
        liked: liked ?? this.liked,
        likes: likes ?? this.likes,
        encouragements: encouragements ?? this.encouragements,
      );
}

final checkinInteractionProvider = StateProvider.autoDispose
    .family<CheckinInteractionState, String>(
        (ref, checkinId) => const CheckinInteractionState());

// ─── Actions ────────────────────────────────────────────────────────────────────

class AccountabilityActions {
  const AccountabilityActions();

  Future<Map<String, dynamic>> likeCheckin(
    WidgetRef ref,
    String checkinId,
  ) async {
    final repo = ref.read(accountabilityRepositoryProvider);
    final result = await repo.likeCheckin(checkinId);

    // Update the interaction state
    ref.read(checkinInteractionProvider(checkinId).notifier).state =
        CheckinInteractionState(
      liked: true,
      likes: result['likes'] as int? ?? 0,
      encouragements:
          ref.read(checkinInteractionProvider(checkinId)).encouragements,
    );

    return result;
  }

  Future<Map<String, dynamic>> encourageCheckin(
    WidgetRef ref,
    String checkinId,
    String message,
  ) async {
    final repo = ref.read(accountabilityRepositoryProvider);
    final result = await repo.encourageCheckin(checkinId, message);

    // Update the interaction state
    final currentState = ref.read(checkinInteractionProvider(checkinId));
    ref.read(checkinInteractionProvider(checkinId).notifier).state =
        currentState.copyWith(
      encouragements: [
        ...currentState.encouragements,
        EncouragementMessage(
          id: result['encouragement']['id'] as String,
          userId: result['encouragement']['user_id'] as String,
          message: result['encouragement']['message'] as String,
          createdAt: DateTime.parse(
            result['encouragement']['created_at'] as String,
          ),
        ),
      ],
    );

    return result;
  }

  Future<Map<String, dynamic>> nudgePartner(
    WidgetRef ref,
    String partnershipId, {
    String? message,
  }) async {
    final repo = ref.read(accountabilityRepositoryProvider);
    return repo.nudgePartner(partnershipId, message: message);
  }

  Future<void> dismissInAppHint(
    WidgetRef ref,
    String notificationId,
  ) async {
    final repo = ref.read(accountabilityRepositoryProvider);
    await repo.dismissInAppHint(notificationId);
    ref.invalidate(accountabilityOverviewProvider);
  }
}

final accountabilityActionsProvider =
    Provider<AccountabilityActions>((ref) => const AccountabilityActions());
