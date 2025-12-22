import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/data/repositories/cognitive_repository.dart';

class CognitiveState {
  final bool isLoading;
  final List<CognitiveFragmentModel> fragments;
  final String? error;

  CognitiveState({
    this.isLoading = false,
    this.fragments = const [],
    this.error,
  });

  CognitiveState copyWith({
    bool? isLoading,
    List<CognitiveFragmentModel>? fragments,
    String? error,
  }) {
    return CognitiveState(
      isLoading: isLoading ?? this.isLoading,
      fragments: fragments ?? this.fragments,
      error: error, // If passed null, it stays null (optional reset logic needed if intended)
    );
  }
}

class CognitiveNotifier extends StateNotifier<CognitiveState> {
  final CognitiveRepository _repository;

  CognitiveNotifier(this._repository) : super(CognitiveState());

  Future<void> loadFragments() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final fragments = await _repository.getFragments();
      state = state.copyWith(isLoading: false, fragments: fragments);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> createFragment({
    required String content,
    required String sourceType,
    String? taskId,
  }) async {
    state = state.copyWith(isLoading: true, error: null);
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
