import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/behavior_pattern_model.dart';
import 'package:sparkle/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/data/repositories/cognitive_repository.dart';

class CognitiveState {

  CognitiveState({
    this.isLoading = false,
    this.fragments = const [],
    this.patterns = const [],
    this.error,
  });
  final bool isLoading;
  final List<CognitiveFragmentModel> fragments;
  final List<BehaviorPatternModel> patterns;
  final String? error;

  CognitiveState copyWith({
    bool? isLoading,
    List<CognitiveFragmentModel>? fragments,
    List<BehaviorPatternModel>? patterns,
    String? error,
  }) => CognitiveState(
      isLoading: isLoading ?? this.isLoading,
      fragments: fragments ?? this.fragments,
      patterns: patterns ?? this.patterns,
      error: error, // If passed null, it stays null (optional reset logic needed if intended)
    );
}

class CognitiveNotifier extends StateNotifier<CognitiveState> {

  CognitiveNotifier(this._repository) : super(CognitiveState());
  final CognitiveRepository _repository;

  Future<void> loadFragments() async {
    state = state.copyWith(isLoading: true);
    try {
      final fragments = await _repository.getFragments();
      state = state.copyWith(isLoading: false, fragments: fragments);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> loadPatterns() async {
    state = state.copyWith(isLoading: true);
    try {
      final patterns = await _repository.getBehaviorPatterns();
      state = state.copyWith(isLoading: false, patterns: patterns);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> createFragment({
    required String content,
    required String sourceType,
    String? taskId,
  }) async {
    state = state.copyWith(isLoading: true);
    try {
      final newFragment = await _repository.createFragment(
        CognitiveFragmentCreate(
          content: content,
          sourceType: sourceType,
          taskId: taskId,
        ),
      );
      
      // Add to list
      state = state.copyWith(
        isLoading: false,
        fragments: [newFragment, ...state.fragments],
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
      rethrow; // Rethrow to let UI handle success/failure feedback
    }
  }
}

final cognitiveProvider = StateNotifierProvider<CognitiveNotifier, CognitiveState>((ref) {
  final repository = ref.watch(cognitiveRepositoryProvider);
  return CognitiveNotifier(repository);
});
