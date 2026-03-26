import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';
import 'package:sparkle/features/theater/data/repositories/theater_repository.dart';

final theaterOverlayProvider = StateProvider<TheaterGalaxyOverlay?>(
  (ref) => null,
);

class TheaterState {
  const TheaterState({
    this.isLoading = false,
    this.isSavingSnapshot = false,
    this.isAdopting = false,
    this.prediction,
    this.selectedRouteId,
    this.timelineIndex = 0,
    this.whatIfResult,
    this.snapshot,
    this.adoptionResult,
    this.accuracySummary,
    this.error,
  });

  final bool isLoading;
  final bool isSavingSnapshot;
  final bool isAdopting;
  final TheaterPrediction? prediction;
  final String? selectedRouteId;
  final int timelineIndex;
  final TheaterWhatIfResult? whatIfResult;
  final TheaterSnapshot? snapshot;
  final TheaterAdoptionResult? adoptionResult;
  final TheaterAccuracySummary? accuracySummary;
  final String? error;

  TheaterPathOption? get selectedRoute {
    final currentPrediction = prediction;
    if (currentPrediction == null) {
      return null;
    }
    for (final route in currentPrediction.paths) {
      if (route.id == selectedRouteId) {
        return route;
      }
    }
    return currentPrediction.paths.isNotEmpty
        ? currentPrediction.paths.first
        : null;
  }

  TheaterState copyWith({
    bool? isLoading,
    bool? isSavingSnapshot,
    bool? isAdopting,
    TheaterPrediction? prediction,
    String? selectedRouteId,
    int? timelineIndex,
    TheaterWhatIfResult? whatIfResult,
    TheaterSnapshot? snapshot,
    TheaterAdoptionResult? adoptionResult,
    TheaterAccuracySummary? accuracySummary,
    String? error,
    bool clearPrediction = false,
    bool clearWhatIf = false,
    bool clearSnapshot = false,
    bool clearAdoption = false,
    bool clearAccuracy = false,
    bool clearError = false,
  }) =>
      TheaterState(
        isLoading: isLoading ?? this.isLoading,
        isSavingSnapshot: isSavingSnapshot ?? this.isSavingSnapshot,
        isAdopting: isAdopting ?? this.isAdopting,
        prediction: clearPrediction ? null : prediction ?? this.prediction,
        selectedRouteId: selectedRouteId ?? this.selectedRouteId,
        timelineIndex: timelineIndex ?? this.timelineIndex,
        whatIfResult: clearWhatIf ? null : whatIfResult ?? this.whatIfResult,
        snapshot: clearSnapshot ? null : snapshot ?? this.snapshot,
        adoptionResult:
            clearAdoption ? null : adoptionResult ?? this.adoptionResult,
        accuracySummary:
            clearAccuracy ? null : accuracySummary ?? this.accuracySummary,
        error: clearError ? null : error ?? this.error,
      );
}

class TheaterNotifier extends StateNotifier<TheaterState> {
  TheaterNotifier(this._repository, this._ref) : super(const TheaterState());

  final TheaterRepository _repository;
  final Ref _ref;

  Future<void> generatePrediction({
    required String topic,
    String? targetNodeId,
    int horizonDays = 14,
  }) async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      clearWhatIf: true,
      clearSnapshot: true,
      clearAdoption: true,
      clearAccuracy: true,
    );
    try {
      final prediction = await _repository.generatePrediction(
        topic: topic,
        targetNodeId: targetNodeId,
        horizonDays: horizonDays,
      );
      final selectedRouteId =
          prediction.paths.isNotEmpty ? prediction.paths.first.id : null;
      state = state.copyWith(
        isLoading: false,
        prediction: prediction,
        selectedRouteId: selectedRouteId,
        timelineIndex: 0,
      );
      _syncOverlay();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void selectRoute(String routeId) {
    state = state.copyWith(selectedRouteId: routeId, clearWhatIf: true);
    _syncOverlay();
  }

  void setTimelineIndex(int index) {
    state = state.copyWith(timelineIndex: index);
  }

  Future<void> runWhatIfForStep(String stepNodeId) async {
    final prediction = state.prediction;
    final route = state.selectedRoute;
    if (prediction == null || route == null) {
      return;
    }
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final result = await _repository.simulateWhatIf(
        predictionId: prediction.predictionId,
        routeId: route.id,
        skipNodeId: stepNodeId,
      );
      state = state.copyWith(
        isLoading: false,
        whatIfResult: result,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> saveSnapshot({String? note}) async {
    final prediction = state.prediction;
    final route = state.selectedRoute;
    if (prediction == null || route == null) {
      return;
    }
    state = state.copyWith(isSavingSnapshot: true, clearError: true);
    try {
      final snapshot = await _repository.saveSnapshot(
        predictionId: prediction.predictionId,
        routeId: route.id,
        note: note,
      );
      state = state.copyWith(
        isSavingSnapshot: false,
        snapshot: snapshot,
      );
    } catch (e) {
      state = state.copyWith(isSavingSnapshot: false, error: e.toString());
    }
  }

  Future<void> adoptSelectedRoute() async {
    final prediction = state.prediction;
    final route = state.selectedRoute;
    if (prediction == null || route == null) {
      return;
    }
    state = state.copyWith(isAdopting: true, clearError: true);
    try {
      final adoption = await _repository.adoptRoute(
        predictionId: prediction.predictionId,
        routeId: route.id,
      );
      state = state.copyWith(
        isAdopting: false,
        adoptionResult: adoption,
      );
    } catch (e) {
      state = state.copyWith(isAdopting: false, error: e.toString());
    }
  }

  Future<void> refreshAccuracy() async {
    final prediction = state.prediction;
    if (prediction == null) {
      return;
    }
    try {
      final summary = await _repository.getAccuracy(prediction.predictionId);
      state = state.copyWith(accuracySummary: summary);
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  void clearOverlay() {
    _ref.read(theaterOverlayProvider.notifier).state = null;
  }

  void _syncOverlay() {
    final route = state.selectedRoute;
    final prediction = state.prediction;
    if (prediction == null || route == null) {
      _ref.read(theaterOverlayProvider.notifier).state = null;
      return;
    }

    final nodeRiskLevels = <String, String>{};
    final predictedMastery = <String, double>{};
    for (final step in route.steps) {
      nodeRiskLevels[step.nodeId] = step.riskLevel;
      predictedMastery[step.nodeId] = step.predictedMastery;
    }

    final focusNodeIds = route.steps.map((step) => step.nodeId).toList();
    final highlightEdgeIds = <String>[];
    for (var index = 0; index < route.steps.length - 1; index++) {
      final source = route.steps[index].nodeId;
      final target = route.steps[index + 1].nodeId;
      highlightEdgeIds.add('${source}_${target}_prerequisite');
    }
    _ref.read(theaterOverlayProvider.notifier).state = TheaterGalaxyOverlay(
      title: route.title,
      focusNodeIds: focusNodeIds,
      highlightEdgeIds: highlightEdgeIds,
      nodeRiskLevels: nodeRiskLevels,
      predictedMasteryByNodeId: predictedMastery,
    );
  }
}

final theaterProvider = StateNotifierProvider<TheaterNotifier, TheaterState>(
  (ref) => TheaterNotifier(ref.watch(theaterRepositoryProvider), ref),
);
