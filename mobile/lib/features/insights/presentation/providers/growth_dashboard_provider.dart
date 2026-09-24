import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/insights/data/models/growth_dashboard.dart';
import 'package:sparkle/features/insights/data/repositories/growth_dashboard_repository.dart';

final growthDashboardProvider =
    AsyncNotifierProvider<GrowthDashboardNotifier, GrowthDashboard>(
  GrowthDashboardNotifier.new,
);

class GrowthDashboardNotifier extends AsyncNotifier<GrowthDashboard> {
  @override
  Future<GrowthDashboard> build() => ref.watch(growthDashboardRepositoryProvider).getGrowthDashboard();

  void updateEntryStatus(String entryId, String status) {
    final current = state.valueOrNull;
    if (current == null) {
      return;
    }
    state = AsyncData(current.updateEntryStatus(entryId, status));
    // F7-14: fire-and-forget 持久化必须 catch，失败时打日志；
    // 下次 load/refresh 仍会从服务端重新对齐（见 build/refresh）。
    unawaited(
      ref
          .read(growthDashboardRepositoryProvider)
          .updateChronicleEntryStatus(entryId, status)
          .catchError((Object e) {
        debugPrint(
          'updateChronicleEntryStatus($entryId, $status) failed: $e',
        );
      }),
    );
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(growthDashboardRepositoryProvider).getGrowthDashboard(),
    );
  }
}
