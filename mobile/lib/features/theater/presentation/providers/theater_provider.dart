import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/data/repositories/galaxy_repository.dart';
import 'package:sparkle/features/galaxy/presentation/providers/galaxy_provider.dart';
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
    this.isPromotingNode = false,
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
  final bool isPromotingNode;
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
    bool? isPromotingNode,
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
        isPromotingNode: isPromotingNode ?? this.isPromotingNode,
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

  String _resolveErrorMessage(
    Object error, {
    required String fallbackMessage,
  }) {
    if (error is TheaterRepositoryException) {
      if (error.isTimeout) {
        return '这次推演花的时间有点长。你可以把目标说得更具体一点，或者稍后再试。';
      }
      return error.message;
    }
    return fallbackMessage;
  }

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
      unawaited(
        _ref.read(appEventStreamServiceProvider).recordTheaterGenerated(
              predictionId: prediction.predictionId,
              topic: prediction.topic,
              targetNodeId: prediction.targetNodeId,
              pathCount: prediction.paths.length,
            ),
      );
      _syncOverlay();
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _resolveErrorMessage(
          e,
          fallbackMessage: '这次推演没有成功生成，你可以稍后再试。',
        ),
      );
    }
  }

  void selectRoute(String routeId) {
    state = state.copyWith(
      selectedRouteId: routeId,
      timelineIndex: 0,
      clearWhatIf: true,
    );
    _syncOverlay();
  }

  void setTimelineIndex(int index) {
    state = state.copyWith(timelineIndex: index);
  }

  Future<void> runWhatIfForStep(String stepNodeId) async {
    await runWhatIfForSteps(<String>[stepNodeId]);
  }

  Future<void> runWhatIfForSteps(List<String> stepNodeIds) async {
    final prediction = state.prediction;
    final route = state.selectedRoute;
    final normalizedStepIds = stepNodeIds
        .map((item) => item.trim())
        .where((item) => item.isNotEmpty)
        .toList();
    if (prediction == null || route == null || normalizedStepIds.isEmpty) {
      return;
    }
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final result = await _repository.simulateWhatIf(
        predictionId: prediction.predictionId,
        routeId: route.id,
        skipNodeIds: normalizedStepIds,
      );
      state = state.copyWith(
        isLoading: false,
        whatIfResult: result,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _resolveErrorMessage(
          e,
          fallbackMessage: '这次假设推演没有成功生成，你可以稍后再试。',
        ),
      );
    }
  }

  Future<void> recordActualOutcome({
    double? actualCompletionRate,
    double? actualMastery,
  }) async {
    final prediction = state.prediction;
    if (prediction == null) {
      return;
    }
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final summary = await _repository.recordActuals(
        predictionId: prediction.predictionId,
        actualCompletionRate: actualCompletionRate,
        actualMastery: actualMastery,
      );
      state = state.copyWith(
        isLoading: false,
        accuracySummary: summary,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: _resolveErrorMessage(
          e,
          fallbackMessage: '记录推演结果失败，你可以稍后再试。',
        ),
      );
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
      state = state.copyWith(
        isSavingSnapshot: false,
        error: _resolveErrorMessage(
          e,
          fallbackMessage: '保存推演快照失败，你可以稍后再试。',
        ),
      );
    }
  }

  Future<void> adoptSelectedRoute() async {
    await adoptSelectedRouteWithSource();
  }

  Future<void> adoptSelectedRouteWithSource({
    String? sourceChatSessionId,
  }) async {
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
        sourceChatSessionId: sourceChatSessionId,
      );
      state = state.copyWith(
        isAdopting: false,
        adoptionResult: adoption,
      );
      unawaited(
        _ref.read(appEventStreamServiceProvider).recordRouteAdopted(
              predictionId: prediction.predictionId,
              routeId: route.id,
              planId: adoption.planId,
            ),
      );
    } catch (e) {
      state = state.copyWith(
        isAdopting: false,
        error: _resolveErrorMessage(
          e,
          fallbackMessage: '采纳这条推演路径失败了，你可以稍后再试。',
        ),
      );
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
      state = state.copyWith(
        error: _resolveErrorMessage(
          e,
          fallbackMessage: '读取推演准确度失败，你可以稍后再试。',
        ),
      );
    }
  }

  void clearError() {
    state = state.copyWith(clearError: true);
  }

  void clearOverlay() {
    _ref.read(theaterOverlayProvider.notifier).state = null;
  }

  Future<TheaterNodePromotionResult?> promoteNodeToGalaxy(
    String theaterNodeId,
  ) async {
    final prediction = state.prediction;
    if (prediction == null) {
      return null;
    }
    state = state.copyWith(isPromotingNode: true, clearError: true);
    try {
      final result = await _repository.promoteNodeToGalaxy(
        predictionId: prediction.predictionId,
        theaterNodeId: theaterNodeId,
      );
      final updatedPrediction = _applyPromotion(prediction, result);
      state = state.copyWith(
        isPromotingNode: false,
        prediction: updatedPrediction,
      );
      _ref
        ..invalidate(galaxyRepositoryProvider)
        ..invalidate(enhancedGalaxyRepositoryProvider)
        ..invalidate(galaxyProvider);
      _syncOverlay();
      return result;
    } catch (e) {
      state = state.copyWith(
        isPromotingNode: false,
        error: _resolveErrorMessage(
          e,
          fallbackMessage: '将节点同步到知识星图失败，你可以稍后再试。',
        ),
      );
      return null;
    }
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
    final mappedNodeIds = <String>[];
    for (final step in route.steps) {
      final mappedNodeId = (step.mappedGalaxyNodeId ?? '').trim();
      if (mappedNodeId.isEmpty) {
        continue;
      }
      mappedNodeIds.add(mappedNodeId);
      nodeRiskLevels[mappedNodeId] = step.riskLevel;
      predictedMastery[mappedNodeId] = step.predictedMastery;
    }

    if (mappedNodeIds.isEmpty) {
      _ref.read(theaterOverlayProvider.notifier).state = null;
      return;
    }

    final focusNodeIds = mappedNodeIds.toSet().toList();
    final highlightEdgeIds = <String>[];
    for (var index = 0; index < route.steps.length - 1; index++) {
      final source = (route.steps[index].mappedGalaxyNodeId ?? '').trim();
      final target = (route.steps[index + 1].mappedGalaxyNodeId ?? '').trim();
      if (source.isEmpty || target.isEmpty) {
        continue;
      }
      highlightEdgeIds.add('${source}_${target}_prerequisite');
    }
    _ref.read(theaterOverlayProvider.notifier).state = TheaterGalaxyOverlay(
      title: route.title,
      topic: prediction.topic,
      focusNodeIds: focusNodeIds,
      highlightEdgeIds: highlightEdgeIds,
      nodeRiskLevels: nodeRiskLevels,
      predictedMasteryByNodeId: predictedMastery,
    );
  }

  TheaterPrediction _applyPromotion(
    TheaterPrediction prediction,
    TheaterNodePromotionResult result,
  ) {
    final updatedNodes = prediction.graphNodes
        .map(
          (node) => node.id == result.theaterNodeId
              ? node.copyWith(
                  mappedGalaxyNodeId: result.galaxyNodeId,
                  clearCandidateStatus: true,
                )
              : node,
        )
        .toList(growable: false);
    final updatedPaths = prediction.paths
        .map(
          (path) => path.copyWith(
            steps: path.steps
                .map(
                  (step) => step.nodeId == result.theaterNodeId
                      ? step.copyWith(
                          mappedGalaxyNodeId: result.galaxyNodeId,
                        )
                      : step,
                )
                .toList(growable: false),
          ),
        )
        .toList(growable: false);
    return prediction.copyWith(
      graphNodes: updatedNodes,
      paths: updatedPaths,
    );
  }
}

final theaterProvider = StateNotifierProvider<TheaterNotifier, TheaterState>(
  (ref) => TheaterNotifier(ref.watch(theaterRepositoryProvider), ref),
);
