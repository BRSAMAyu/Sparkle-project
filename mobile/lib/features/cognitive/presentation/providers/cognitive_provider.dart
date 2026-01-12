import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/cognitive_repository.dart';
import 'package:sparkle/features/cognitive/data/repositories/i_cognitive_repository.dart';

export 'package:sparkle/features/cognitive/data/repositories/cognitive_repository.dart'
    show cognitiveRepositoryProvider;

class CognitiveState {
  const CognitiveState({
    this.isLoading = false,
    this.patterns = const [],
    this.fragments = const [],
    this.error,
  });

  final bool isLoading;
  final List<BehaviorPatternModel> patterns;
  final List<CognitiveFragmentModel> fragments;
  final String? error;

  CognitiveState copyWith({
    bool? isLoading,
    List<BehaviorPatternModel>? patterns,
    List<CognitiveFragmentModel>? fragments,
    String? error,
    bool clearError = false,
  }) =>
      CognitiveState(
        isLoading: isLoading ?? this.isLoading,
        patterns: patterns ?? this.patterns,
        fragments: fragments ?? this.fragments,
        error: clearError ? null : error ?? this.error,
      );
}

class CognitiveNotifier extends StateNotifier<CognitiveState> {
  CognitiveNotifier(this._repository) : super(const CognitiveState());

  final ICognitiveRepository _repository;

  Future<void> loadPatterns() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final patterns = await _repository.getBehaviorPatterns();
      state = state.copyWith(isLoading: false, patterns: patterns);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> loadFragments({int limit = 20, int skip = 0}) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final fragments =
          await _repository.getFragments(limit: limit, skip: skip);
      state = state.copyWith(isLoading: false, fragments: fragments);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<CognitiveFragmentModel?> createFragment({
    required String content,
    required String sourceType,
    String? taskId,
  }) async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final fragment = await _repository.createFragment(
        CognitiveFragmentCreate(
          content: content,
          sourceType: sourceType,
          taskId: taskId,
        ),
      );
      state = state.copyWith(
        isLoading: false,
        fragments: [fragment, ...state.fragments],
      );
      return fragment;
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      return null;
    }
  }
}

final cognitiveProvider =
    StateNotifierProvider<CognitiveNotifier, CognitiveState>((ref) {
  final repository = ref.watch(cognitiveRepositoryProvider);
  return CognitiveNotifier(repository);
});
