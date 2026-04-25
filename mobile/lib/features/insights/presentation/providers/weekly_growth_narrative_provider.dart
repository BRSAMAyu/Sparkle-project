import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';
import 'package:sparkle/features/insights/data/repositories/growth_narrative_repository.dart';

final weeklyGrowthNarrativeProvider =
    FutureProvider<WeeklyGrowthNarrative>((ref) async {
  final repository = ref.watch(growthNarrativeRepositoryProvider);
  return repository.getWeeklyNarrative();
});
