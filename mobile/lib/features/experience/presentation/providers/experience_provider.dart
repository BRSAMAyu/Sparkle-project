import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/experience/data/experience_models.dart';
import 'package:sparkle/features/experience/data/experience_repository.dart';

final understandingSnapshotProvider =
    FutureProvider.autoDispose<UnderstandingSnapshot>((ref) async {
  // Demo contract: demo data never fails (B-04-L-01, V3-FIX-376 补完). The
  // golden home first screen receipt card (UnderstandingSnapshotCard) watches
  // THIS twin provider — not the home understanding_snapshot_provider that
  // wt686 gated — so the demo first screen still rendered 「加载失败」. Degrade
  // to the built-in empty snapshot in demo mode; the card renders its honest
  // empty state for it (fallback narrative line). Non-demo path untouched.
  if (DemoDataService.isDemoMode) {
    return const UnderstandingSnapshot(
      active: false,
      status: 'sensing',
      summary: '',
      confidence: 0,
      evidence: [],
      memoryClaims: [],
      openQuestions: [],
    );
  }
  final repository = ref.watch(experienceRepositoryProvider);
  return repository.getUnderstandingSnapshot();
});

final experienceGrowthDashboardProvider =
    FutureProvider.autoDispose<ExperienceGrowthDashboard>((ref) async {
  final repository = ref.watch(experienceRepositoryProvider);
  return repository.getGrowthDashboard();
});

final currentGoalDetailSnapshotProvider =
    FutureProvider.autoDispose<GoalDetailSnapshot>((ref) async {
  final repository = ref.watch(experienceRepositoryProvider);
  return repository.getGoalDetail();
});

final communityAccountabilitySnapshotProvider =
    FutureProvider.autoDispose<CommunityAccountabilitySnapshot>((ref) async {
  final repository = ref.watch(experienceRepositoryProvider);
  return repository.getCommunityAccountability();
});
