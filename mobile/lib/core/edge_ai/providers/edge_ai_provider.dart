import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/edge_inference_service.dart';
import '../models/edge_state_schema.dart';

/// Holds the latest inferred state from the edge model.
final edgeAIStateProvider = StateNotifierProvider<EdgeAINotifier, AsyncValue<EdgeState?>>((ref) {
  final service = ref.watch(edgeInferenceServiceProvider);
  return EdgeAINotifier(service);
});

class EdgeAINotifier extends StateNotifier<AsyncValue<EdgeState?>> {
  final EdgeInferenceService _service;

  EdgeAINotifier(this._service) : super(const AsyncValue.data(null));

  /// Triggers a fresh analysis cycle.
  Future<void> refresh() async {
    state = const AsyncValue.loading();
    try {
      final result = await _service.runAnalysis();
      state = AsyncValue.data(result);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  /// Initializes the service (downloads/loads model).
  Future<void> init() async {
    await _service.initialize();
  }
}
