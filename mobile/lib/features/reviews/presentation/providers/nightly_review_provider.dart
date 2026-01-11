import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/reviews/data/models/nightly_review_payload.dart';
import 'package:sparkle/features/reviews/data/repositories/nightly_review_repository.dart';

final nightlyReviewProvider = FutureProvider<NightlyReviewPayload?>((ref) async {
  final repository = ref.watch(nightlyReviewRepositoryProvider);
  return repository.getLatest();
});

final nightlyReviewActionsProvider = Provider<NightlyReviewActions>((ref) {
  return NightlyReviewActions(ref);
});

class NightlyReviewActions {
  NightlyReviewActions(this._ref);
  final Ref _ref;

  Future<void> markReviewed(String reviewId) async {
    final repository = _ref.read(nightlyReviewRepositoryProvider);
    await repository.markReviewed(reviewId);
    _ref.invalidate(nightlyReviewProvider);
  }
}
