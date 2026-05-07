import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/insights/data/models/growth_dashboard.dart';
import 'package:sparkle/features/insights/data/repositories/growth_dashboard_repository.dart';

final growthDashboardProvider =
    AsyncNotifierProvider<GrowthDashboardNotifier, GrowthDashboard>(
  GrowthDashboardNotifier.new,
);

class GrowthDashboardNotifier extends AsyncNotifier<GrowthDashboard> {
  @override
  Future<GrowthDashboard> build() {
    return ref.watch(growthDashboardRepositoryProvider).getGrowthDashboard();
  }

  void updateEntryStatus(String entryId, String status) {
    final current = state.valueOrNull;
    if (current == null) {
      return;
    }
    state = AsyncData(current.updateEntryStatus(entryId, status));
    // Persist to backend (fire-and-forget; refresh on next load if it fails)
    ref.read(growthDashboardRepositoryProvider).updateChronicleEntryStatus(entryId, status);
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(growthDashboardRepositoryProvider).getGrowthDashboard(),
    );
  }
}
