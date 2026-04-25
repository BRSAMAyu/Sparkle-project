import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';

final learningPortfolioProvider =
    FutureProvider.autoDispose<LearningPortfolioResult>((ref) async {
  final repository = ref.watch(examSprintRepositoryProvider);
  final userId = ref.watch(currentUserProvider)?.id;
  return repository.fetchLearningPortfolio(userId: userId);
});
