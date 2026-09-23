import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/core/services/app_event_stream_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/data/repositories/simulation_repository.dart';

class SimulationState {
  const SimulationState({
    this.isLoading = false,
    this.isContinuing = false,
    this.isLoadingRecommendations = false,
    this.session,
    this.error,
    this.sessionId,
    this.engineState,
    this.progress = 0,
    this.recommendedSeeds = const [],
    this.liveParticipants = const [],
    this.liveRounds = const [],
    this.liveInsightSummary,
    this.liveInteractionPrompt,
    this.liveSuggestedReplies = const [],
    this.activeInteraction,
    this.livePlannedRoundCount = 0,
    this.liveFacilitationStyle,
  });

  final bool isLoading;
  final bool isContinuing;
  final bool isLoadingRecommendations;
  final SimulationSessionModel? session;

  /// N15（A-SPEC3）：UI 可达错误字段只存类型化类别（渲染侧经
  /// error_lexicon owner 出人话）；原始异常细节只进 debugPrint 日志。
  final UiErrorCategory? error;
  final String? sessionId;
  final String? engineState;
  final double progress;
  final List<SimulationSeedModel> recommendedSeeds;
  final List<SimulationParticipantModel> liveParticipants;
  final List<SimulationRoundModel> liveRounds;
  final String? liveInsightSummary;
  final String? liveInteractionPrompt;
  final List<String> liveSuggestedReplies;
  final SimulationInteractionModel? activeInteraction;
  final int livePlannedRoundCount;
  final String? liveFacilitationStyle;

  bool get isAwaitingUserInput => engineState == 'WAITING_FOR_USER';

  SimulationState copyWith({
    bool? isLoading,
    bool? isContinuing,
    bool? isLoadingRecommendations,
    SimulationSessionModel? session,
    UiErrorCategory? error,
    String? sessionId,
    String? engineState,
    double? progress,
    List<SimulationSeedModel>? recommendedSeeds,
    List<SimulationParticipantModel>? liveParticipants,
    List<SimulationRoundModel>? liveRounds,
    String? liveInsightSummary,
    String? liveInteractionPrompt,
    List<String>? liveSuggestedReplies,
    SimulationInteractionModel? activeInteraction,
    int? livePlannedRoundCount,
    String? liveFacilitationStyle,
    bool clearError = false,
    bool clearSession = false,
    bool clearSessionId = false,
    bool clearLiveInsightSummary = false,
    bool clearLiveInteractionPrompt = false,
    bool clearActiveInteraction = false,
    bool clearLiveFacilitationStyle = false,
  }) =>
      SimulationState(
        isLoading: isLoading ?? this.isLoading,
        isContinuing: isContinuing ?? this.isContinuing,
        isLoadingRecommendations:
            isLoadingRecommendations ?? this.isLoadingRecommendations,
        session: clearSession ? null : session ?? this.session,
        error: clearError ? null : error ?? this.error,
        sessionId: clearSessionId ? null : sessionId ?? this.sessionId,
        engineState: engineState ?? this.engineState,
        progress: progress ?? this.progress,
        recommendedSeeds: recommendedSeeds ?? this.recommendedSeeds,
        liveParticipants: liveParticipants ?? this.liveParticipants,
        liveRounds: liveRounds ?? this.liveRounds,
        liveInsightSummary: clearLiveInsightSummary
            ? null
            : liveInsightSummary ?? this.liveInsightSummary,
        liveInteractionPrompt: clearLiveInteractionPrompt
            ? null
            : liveInteractionPrompt ?? this.liveInteractionPrompt,
        liveSuggestedReplies: liveSuggestedReplies ?? this.liveSuggestedReplies,
        activeInteraction: clearActiveInteraction
            ? null
            : activeInteraction ?? this.activeInteraction,
        livePlannedRoundCount:
            livePlannedRoundCount ?? this.livePlannedRoundCount,
        liveFacilitationStyle: clearLiveFacilitationStyle
            ? null
            : liveFacilitationStyle ?? this.liveFacilitationStyle,
      );
}

class SimulationNotifier extends StateNotifier<SimulationState> {
  SimulationNotifier(this._repository, this._ref)
      : super(const SimulationState());

  final SimulationRepository _repository;
  final Ref _ref;

  void _hydrateFromSession(
    SimulationSessionModel session, {
    bool clearError = false,
    UiErrorCategory? error,
  }) {
    state = state.copyWith(
      isLoading: false,
      isContinuing: false,
      session: session,
      sessionId: session.id,
      engineState: session.state,
      progress: 1,
      liveParticipants: session.participants,
      liveRounds: session.rounds,
      liveInsightSummary: session.insightSummary,
      liveInteractionPrompt: session.interactionPrompt,
      liveSuggestedReplies: session.suggestedReplies,
      activeInteraction: session.pendingInteraction,
      livePlannedRoundCount: session.plannedRoundCount,
      liveFacilitationStyle: session.facilitationStyle,
      clearError: clearError,
      error: error,
    );
  }

  Future<bool> _recoverSession(String? sessionId) async {
    final normalizedSessionId = (sessionId ?? '').trim();
    if (normalizedSessionId.isEmpty) {
      return false;
    }
    try {
      final session = await _repository.getSession(normalizedSessionId);
      // 恢复成功即回到实时会话，不再借错误横幅播报恢复提示（N15：
      // error 位只承载错误类别；「已恢复」是成功态，由恢复后的会话本体自证）。
      _hydrateFromSession(session, clearError: true);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> loadRecommendedSeeds({
    String? scenarioKey,
    int limit = 3,
    bool silent = false,
  }) async {
    state = state.copyWith(
      isLoadingRecommendations: !silent,
      clearError: true,
    );
    try {
      final seeds = await _repository.getRecommendedSeeds(
        scenarioKey: scenarioKey,
        limit: limit,
      );
      state = state.copyWith(
        isLoadingRecommendations: false,
        recommendedSeeds: seeds,
      );
    } catch (e) {
      debugPrint('[simulation] load recommendations failed: $e');
      state = state.copyWith(
        isLoadingRecommendations: false,
        error: categorizeUiError(e),
      );
    }
  }

  Future<void> run({
    required String topic,
    required String scenarioKey,
    int? plannedRoundCount,
    List<String>? participantNames,
    String facilitationStyle = 'balanced',
  }) async {
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      clearSession: true,
      clearSessionId: true,
      engineState: 'PREPARING',
      progress: 0,
      liveParticipants: const [],
      liveRounds: const [],
      clearLiveInsightSummary: true,
      clearLiveInteractionPrompt: true,
      liveSuggestedReplies: const [],
      clearActiveInteraction: true,
      livePlannedRoundCount: plannedRoundCount ?? 0,
      liveFacilitationStyle: facilitationStyle,
    );
    try {
      unawaited(
        _ref.read(appEventStreamServiceProvider).recordSimulationStarted(
              topic: topic,
              scenarioKey: scenarioKey,
            ),
      );
    } catch (_) {
      // Telemetry should never block the simulation experience.
    }
    try {
      await for (final event in _repository.streamSimulation(
        topic: topic,
        scenarioKey: scenarioKey,
        plannedRoundCount: plannedRoundCount,
        participantNames: participantNames,
        facilitationStyle: facilitationStyle,
      )) {
        _applyStreamEvent(event, topic: topic, scenarioKey: scenarioKey);
      }
      if (state.session == null) {
        final session = await _repository.runSimulation(
          topic: topic,
          scenarioKey: scenarioKey,
          plannedRoundCount: plannedRoundCount,
          participantNames: participantNames,
          facilitationStyle: facilitationStyle,
        );
        state = state.copyWith(
          isLoading: false,
          session: session,
          sessionId: session.id,
          engineState: session.state,
          progress: 1,
          liveParticipants: session.participants,
          liveRounds: session.rounds,
          liveInsightSummary: session.insightSummary,
          liveInteractionPrompt: session.interactionPrompt,
          liveSuggestedReplies: session.suggestedReplies,
          activeInteraction: session.pendingInteraction,
          livePlannedRoundCount: session.plannedRoundCount,
          liveFacilitationStyle: session.facilitationStyle,
        );
      }
      if (state.isLoading) {
        state = state.copyWith(isLoading: false);
      }
    } catch (e) {
      final recovered = await _recoverSession(state.sessionId);
      if (!recovered) {
        debugPrint('[simulation] realtime load failed: $e');
        state = state.copyWith(
            isLoading: false, error: categorizeUiError(e));
      }
    }
  }

  Future<void> restoreSession(String sessionId) async {
    final normalizedSessionId = sessionId.trim();
    if (normalizedSessionId.isEmpty) {
      return;
    }
    state = state.copyWith(
      isLoading: true,
      clearError: true,
      engineState: 'RESTORING',
    );
    try {
      final session = await _repository.getSession(normalizedSessionId);
      _hydrateFromSession(session, clearError: true);
    } catch (e) {
      debugPrint('[simulation] restore session failed: $e');
      state = state.copyWith(
        isLoading: false,
        error: categorizeUiError(e),
      );
    }
  }

  Future<bool> continueSimulation(
    String userResponse, {
    int? plannedRoundCount,
  }) async {
    final sessionId = state.sessionId ?? state.session?.id;
    final topic = state.session?.topic ?? '';
    final scenarioKey = state.session?.scenarioKey ?? 'study_group';
    if ((sessionId ?? '').isEmpty || userResponse.trim().isEmpty) {
      return false;
    }

    state = state.copyWith(
      isLoading: true,
      isContinuing: true,
      clearError: true,
      engineState: 'RUNNING',
      clearLiveInteractionPrompt: true,
      liveSuggestedReplies: const [],
      clearActiveInteraction: true,
    );

    try {
      await for (final event in _repository.continueSimulationStream(
        sessionId: sessionId!,
        userResponse: userResponse.trim(),
        plannedRoundCount: plannedRoundCount,
      )) {
        _applyStreamEvent(event, topic: topic, scenarioKey: scenarioKey);
      }
      if (state.session == null || state.session?.id != sessionId) {
        final session = await _repository.continueSimulation(
          sessionId: sessionId,
          userResponse: userResponse.trim(),
          plannedRoundCount: plannedRoundCount,
        );
        state = state.copyWith(
          isLoading: false,
          isContinuing: false,
          session: session,
          sessionId: session.id,
          engineState: session.state,
          progress: 1,
          liveParticipants: session.participants,
          liveRounds: session.rounds,
          liveInsightSummary: session.insightSummary,
          liveInteractionPrompt: session.interactionPrompt,
          liveSuggestedReplies: session.suggestedReplies,
          activeInteraction: session.pendingInteraction,
          livePlannedRoundCount: session.plannedRoundCount,
          liveFacilitationStyle: session.facilitationStyle,
        );
      }
      if (state.isLoading || state.isContinuing) {
        state = state.copyWith(
          isLoading: false,
          isContinuing: false,
        );
      }
      return true;
    } catch (e) {
      final recovered = await _recoverSession(sessionId);
      if (!recovered) {
        debugPrint('[simulation] continue stream failed: $e');
        state = state.copyWith(
          isLoading: false,
          isContinuing: false,
          error: categorizeUiError(e),
        );
      }
      return recovered;
    }
  }

  void _applyStreamEvent(
    SimulationStreamEventModel event, {
    required String topic,
    required String scenarioKey,
  }) {
    switch (event.event) {
      case 'status':
        state = state.copyWith(
          sessionId: event.sessionId,
          engineState: event.state,
          progress: event.progress ?? state.progress,
          livePlannedRoundCount:
              event.plannedRoundCount ?? state.livePlannedRoundCount,
          liveFacilitationStyle:
              event.facilitationStyle ?? state.liveFacilitationStyle,
        );
        return;
      case 'participants':
        _applyLiveSessionState(
          topic: topic,
          scenarioKey: scenarioKey,
          sessionId: event.sessionId,
          engineState: event.state,
          progress: event.progress ?? state.progress,
          participants: event.participants,
          interactionPrompt: event.interactionPrompt,
          suggestedReplies: event.suggestedReplies,
          pendingInteraction: event.interaction,
          plannedRoundCount:
              event.plannedRoundCount ?? state.livePlannedRoundCount,
          facilitationStyle:
              event.facilitationStyle ?? state.liveFacilitationStyle,
        );
        return;
      case 'round':
        final updatedRounds = event.rounds.isNotEmpty
            ? event.rounds
            : [
                ...state.liveRounds,
                if (event.round != null) event.round!,
              ];
        _applyLiveSessionState(
          topic: topic,
          scenarioKey: scenarioKey,
          sessionId: event.sessionId,
          engineState: event.state,
          progress: event.progress ?? state.progress,
          rounds: updatedRounds,
          insightSummary: S.simRoundProgressSummary(updatedRounds.length),
          interactionPrompt:
              event.interactionPrompt ?? state.liveInteractionPrompt,
          suggestedReplies: event.suggestedReplies.isNotEmpty
              ? event.suggestedReplies
              : state.liveSuggestedReplies,
          pendingInteraction: event.interaction ?? state.activeInteraction,
          plannedRoundCount:
              event.plannedRoundCount ?? state.livePlannedRoundCount,
          facilitationStyle:
              event.facilitationStyle ?? state.liveFacilitationStyle,
        );
        return;
      case 'insight':
        _applyLiveSessionState(
          topic: topic,
          scenarioKey: scenarioKey,
          sessionId: event.sessionId,
          engineState: event.state,
          progress: event.progress ?? state.progress,
          insightSummary: event.message ?? state.liveInsightSummary,
          plannedRoundCount:
              event.plannedRoundCount ?? state.livePlannedRoundCount,
          facilitationStyle:
              event.facilitationStyle ?? state.liveFacilitationStyle,
        );
        return;
      case 'interaction':
        final interaction = event.interaction;
        final interactionReplies =
            interaction?.suggestedReplies ?? const <String>[];
        _applyLiveSessionState(
          topic: topic,
          scenarioKey: scenarioKey,
          sessionId: event.sessionId,
          isLoading: false,
          isContinuing: false,
          engineState: event.state,
          progress: event.progress ?? state.progress,
          participants: event.participants.isNotEmpty
              ? event.participants
              : state.liveParticipants,
          rounds: event.rounds.isNotEmpty ? event.rounds : state.liveRounds,
          interactionPrompt: interaction?.prompt ??
              event.interactionPrompt ??
              state.liveInteractionPrompt,
          suggestedReplies: interactionReplies.isNotEmpty
              ? interactionReplies
              : (event.suggestedReplies.isNotEmpty
                  ? event.suggestedReplies
                  : state.liveSuggestedReplies),
          pendingInteraction: interaction,
          plannedRoundCount:
              event.plannedRoundCount ?? state.livePlannedRoundCount,
          facilitationStyle:
              event.facilitationStyle ?? state.liveFacilitationStyle,
        );
        return;
      case 'complete':
        final session = event.session;
        state = state.copyWith(
          isLoading: false,
          isContinuing: false,
          session: session,
          sessionId: session?.id ?? event.sessionId,
          engineState: session?.state ?? event.state,
          progress: event.progress ?? 1,
          liveParticipants: session?.participants ?? state.liveParticipants,
          liveRounds: session?.rounds ?? state.liveRounds,
          liveInsightSummary:
              session?.insightSummary ?? state.liveInsightSummary,
          liveInteractionPrompt:
              session?.interactionPrompt ?? state.liveInteractionPrompt,
          liveSuggestedReplies: (session?.suggestedReplies.isNotEmpty ?? false)
              ? session!.suggestedReplies
              : state.liveSuggestedReplies,
          activeInteraction:
              session?.pendingInteraction ?? state.activeInteraction,
          livePlannedRoundCount: session?.plannedRoundCount ??
              event.plannedRoundCount ??
              state.livePlannedRoundCount,
          liveFacilitationStyle: session?.facilitationStyle ??
              event.facilitationStyle ??
              state.liveFacilitationStyle,
        );
        return;
      case 'error':
        debugPrint('[simulation] engine error event: ${event.message}');
        state = state.copyWith(
          isLoading: false,
          isContinuing: false,
          // 后端事件文本不进 UI（N15）；统一落服务故障类别。
          error: UiErrorCategory.serviceDegraded,
        );
        return;
      case 'done':
        state = state.copyWith(
          isLoading: false,
          isContinuing: false,
          progress: state.progress == 0 ? 1 : state.progress,
        );
        return;
      default:
        return;
    }
  }

  void _applyLiveSessionState({
    required String topic,
    required String scenarioKey,
    String? sessionId,
    bool? isLoading,
    bool? isContinuing,
    String? engineState,
    double? progress,
    List<SimulationParticipantModel>? participants,
    List<SimulationRoundModel>? rounds,
    String? insightSummary,
    String? interactionPrompt,
    List<String>? suggestedReplies,
    SimulationInteractionModel? pendingInteraction,
    int? plannedRoundCount,
    String? facilitationStyle,
  }) {
    final nextSession = _draftSession(
      topic: topic,
      scenarioKey: scenarioKey,
      sessionId: sessionId,
      participants: participants,
      rounds: rounds,
      engineState: engineState,
      insightSummary: insightSummary,
      interactionPrompt: interactionPrompt,
      suggestedReplies: suggestedReplies,
      pendingInteraction: pendingInteraction,
      plannedRoundCount: plannedRoundCount,
      facilitationStyle: facilitationStyle,
    );

    state = state.copyWith(
      isLoading: isLoading,
      isContinuing: isContinuing,
      sessionId: nextSession.id,
      engineState: nextSession.state,
      progress: progress ?? state.progress,
      liveParticipants: nextSession.participants,
      liveRounds: nextSession.rounds,
      liveInsightSummary: nextSession.insightSummary,
      liveInteractionPrompt: nextSession.interactionPrompt,
      liveSuggestedReplies: nextSession.suggestedReplies,
      activeInteraction: nextSession.pendingInteraction,
      livePlannedRoundCount: nextSession.plannedRoundCount,
      liveFacilitationStyle: nextSession.facilitationStyle,
      session: nextSession,
    );
  }

  SimulationSessionModel _draftSession({
    required String topic,
    required String scenarioKey,
    String? sessionId,
    List<SimulationParticipantModel>? participants,
    List<SimulationRoundModel>? rounds,
    String? engineState,
    String? insightSummary,
    String? interactionPrompt,
    List<String>? suggestedReplies,
    SimulationInteractionModel? pendingInteraction,
    int? plannedRoundCount,
    String? facilitationStyle,
  }) =>
      (state.session ??
              SimulationSessionModel(
                id: state.sessionId ?? '',
                scenarioKey: scenarioKey,
                state: state.engineState ?? 'RUNNING',
                topic: topic,
                participants: state.liveParticipants,
                rounds: state.liveRounds,
                insightSummary:
                    state.liveInsightSummary ?? S.simDraftInsightSummary,
                interactionPrompt: state.liveInteractionPrompt,
                suggestedReplies: state.liveSuggestedReplies,
                pendingInteraction: state.activeInteraction,
                plannedRoundCount: state.livePlannedRoundCount,
                facilitationStyle: state.liveFacilitationStyle ?? 'balanced',
              ))
          .copyWith(
        id: sessionId ?? state.sessionId ?? state.session?.id ?? '',
        scenarioKey: scenarioKey,
        state: engineState ?? state.engineState ?? state.session?.state,
        topic: topic,
        participants: participants ?? state.liveParticipants,
        rounds: rounds ?? state.liveRounds,
        insightSummary: insightSummary ??
            state.liveInsightSummary ??
            state.session?.insightSummary,
        interactionPrompt: interactionPrompt ?? state.liveInteractionPrompt,
        suggestedReplies: suggestedReplies ?? state.liveSuggestedReplies,
        pendingInteraction: pendingInteraction ?? state.activeInteraction,
        plannedRoundCount: plannedRoundCount ?? state.livePlannedRoundCount,
        facilitationStyle:
            facilitationStyle ?? state.liveFacilitationStyle ?? 'balanced',
      );
}

final simulationProvider =
    StateNotifierProvider<SimulationNotifier, SimulationState>(
  (ref) => SimulationNotifier(
    ref.watch(simulationRepositoryProvider),
    ref,
  ),
);
