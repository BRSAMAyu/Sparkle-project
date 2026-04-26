import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';

class LearningPortfolioNotifier extends AutoDisposeAsyncNotifier<LearningPortfolioResult> {
  @override
  Future<LearningPortfolioResult> build() async {
    final repository = ref.watch(examSprintRepositoryProvider);
    final userId = ref.watch(currentUserProvider)?.id;
    return repository.fetchLearningPortfolio(userId: userId);
  }

  Future<void> loadMore() async {
    final current = state.valueOrNull;
    if (current == null || !current.hasMore) return;

    state = const AsyncLoading();
    try {
      final repository = ref.read(examSprintRepositoryProvider);
      final userId = ref.read(currentUserProvider)?.id;
      final nextPage = current.currentPage + 1;
      final result = await repository.fetchLearningPortfolio(
        userId: userId,
        page: nextPage,
      );
      state = AsyncData(current.merge(result));
    } catch (e, st) {
      state = AsyncError(e, st);
    }
  }
}

final learningPortfolioProvider = AsyncNotifierProvider.autoDispose<
    LearningPortfolioNotifier, LearningPortfolioResult>(
  LearningPortfolioNotifier.new,
);
