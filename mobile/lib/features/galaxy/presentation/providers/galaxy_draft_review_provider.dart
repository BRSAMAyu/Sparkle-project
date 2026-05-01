import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_draft_review_models.dart';
import 'package:sparkle/features/galaxy/data/repositories/galaxy_draft_repository.dart';

class GalaxyDraftReviewState {
  const GalaxyDraftReviewState({
    this.batches = const AsyncValue.loading(),
    this.dismissedPromptBatchIds = const <String>{},
  });

  final AsyncValue<List<GalaxyDraftBatch>> batches;
  final Set<String> dismissedPromptBatchIds;

  GalaxyDraftReviewState copyWith({
    AsyncValue<List<GalaxyDraftBatch>>? batches,
    Set<String>? dismissedPromptBatchIds,
  }) {
    return GalaxyDraftReviewState(
      batches: batches ?? this.batches,
      dismissedPromptBatchIds:
          dismissedPromptBatchIds ?? this.dismissedPromptBatchIds,
    );
  }

  List<GalaxyDraftBatch> get queue => batches.valueOrNull ?? const [];

  int get pendingBatchCount => queue.length;

  int get pendingDraftCount =>
      queue.fold<int>(0, (sum, batch) => sum + batch.drafts.length);

  GalaxyDraftBatch? get promptBatch {
    for (final batch in queue) {
      if (!dismissedPromptBatchIds.contains(batch.id)) {
        return batch;
      }
    }
    return null;
  }

  GalaxyDraftBatch? batchById(String? batchId) {
    if (batchId == null || batchId.isEmpty) {
      return queue.isEmpty ? null : queue.first;
    }
    for (final batch in queue) {
      if (batch.id == batchId) {
        return batch;
      }
    }
    return null;
  }
}

class GalaxyDraftReviewNotifier extends StateNotifier<GalaxyDraftReviewState> {
  GalaxyDraftReviewNotifier(this._repository)
      : super(const GalaxyDraftReviewState()) {
    unawaited(refresh());
  }

  final GalaxyDraftRepository _repository;

  Future<void> refresh() async {
    state = state.copyWith(batches: const AsyncValue.loading());
    try {
      final batches = await _repository.listPendingDrafts();
      final validDismissals = state.dismissedPromptBatchIds
          .where((batchId) => batches.any((batch) => batch.id == batchId))
          .toSet();
      state = state.copyWith(
        batches: AsyncValue.data(batches),
        dismissedPromptBatchIds: validDismissals,
      );
    } on Exception catch (error, stackTrace) {
      state = state.copyWith(
        batches: AsyncValue.error(error, stackTrace),
      );
    }
  }

  void dismissPrompt(String batchId) {
    state = state.copyWith(
      dismissedPromptBatchIds: {
        ...state.dismissedPromptBatchIds,
        batchId,
      },
    );
  }

  void restorePrompt(String batchId) {
    final updated = {...state.dismissedPromptBatchIds}..remove(batchId);
    state = state.copyWith(dismissedPromptBatchIds: updated);
  }

  void completeBatch(String batchId) {
    final current = state.queue;
    final updated = current.where((batch) => batch.id != batchId).toList();
    final dismissed = {...state.dismissedPromptBatchIds}..remove(batchId);
    state = state.copyWith(
      batches: AsyncValue.data(updated),
      dismissedPromptBatchIds: dismissed,
    );
  }
}

final galaxyDraftReviewProvider =
    StateNotifierProvider<GalaxyDraftReviewNotifier, GalaxyDraftReviewState>(
  (ref) => GalaxyDraftReviewNotifier(
    ref.watch(galaxyDraftRepositoryProvider),
  ),
);
