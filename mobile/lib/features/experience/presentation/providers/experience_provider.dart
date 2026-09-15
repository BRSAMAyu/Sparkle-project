import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/experience/data/experience_models.dart';
import 'package:sparkle/features/experience/data/experience_repository.dart';

final understandingSnapshotProvider =
    FutureProvider.autoDispose<UnderstandingSnapshot>((ref) async {
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
