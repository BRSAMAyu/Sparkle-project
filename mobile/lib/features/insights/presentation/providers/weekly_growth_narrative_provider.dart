import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/insights/data/models/weekly_growth_narrative.dart';
import 'package:sparkle/features/insights/data/repositories/growth_narrative_repository.dart';

final weeklyGrowthNarrativeWeekKeyProvider =
    Provider.autoDispose<String>((ref) {
  final now = DateTime.now();
  final anchor = DateTime(now.year, now.month, now.day)
      .subtract(Duration(days: now.weekday - 1));
  return '${anchor.year}-${anchor.month}-${anchor.day}';
});

final weeklyGrowthNarrativeProvider =
    FutureProvider.autoDispose<WeeklyGrowthNarrative>((ref) async {
  ref.watch(weeklyGrowthNarrativeWeekKeyProvider);
  final repository = ref.watch(growthNarrativeRepositoryProvider);
  return repository.getWeeklyNarrative();
});
