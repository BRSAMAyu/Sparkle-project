import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';
import 'package:sparkle/features/simulation/data/repositories/simulation_repository.dart';

class SimulationState {
  const SimulationState({
    this.isLoading = false,
    this.session,
    this.error,
    this.sessionId,
    this.engineState,
    this.progress = 0,
    this.liveParticipants = const [],
    this.liveRounds = const [],
    this.liveInsightSummary,
  });

  final bool isLoading;
  final SimulationSessionModel? session;
  final String? error;
  final String? sessionId;
  final String? engineState;
  final double progress;
  final List<SimulationParticipantModel> liveParticipants;
  final List<SimulationRoundModel> liveRounds;
  final String? liveInsightSummary;

  SimulationState copyWith({
    bool? isLoading,
    SimulationSessionModel? session,
    String? error,
    String? sessionId,
    String? engineState,
    double? progress,
    List<SimulationParticipantModel>? liveParticipants,
    List<SimulationRoundModel>? liveRounds,
    String? liveInsightSummary,
    bool clearError = false,
    bool clearSession = false,
    bool clearSessionId = false,
    bool clearLiveInsightSummary = false,
  }) =>
      SimulationState(
        isLoading: isLoading ?? this.isLoading,
        session: clearSession ? null : session ?? this.session,
        error: clearError ? null : error ?? this.error,
        sessionId: clearSessionId ? null : sessionId ?? this.sessionId,
        engineState: engineState ?? this.engineState,
        progress: progress ?? this.progress,
        liveParticipants: liveParticipants ?? this.liveParticipants,
        liveRounds: liveRounds ?? this.liveRounds,
        liveInsightSummary: clearLiveInsightSummary
            ? null
            : liveInsightSummary ?? this.liveInsightSummary,
      );
}

class SimulationNotifier extends StateNotifier<SimulationState> {
  SimulationNotifier(this._repository) : super(const SimulationState());

  final SimulationRepository _repository;

  Future<void> run({
    required String topic,
    required String scenarioKey,
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
    );
    try {
      await for (final event in _repository.streamSimulation(
        topic: topic,
        scenarioKey: scenarioKey,
      )) {
        _applyStreamEvent(event, topic: topic, scenarioKey: scenarioKey);
      }
      if (state.session == null) {
        final session = await _repository.runSimulation(
          topic: topic,
          scenarioKey: scenarioKey,
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
        );
      }
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
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
        );
        return;
      case 'participants':
        state = state.copyWith(
          sessionId: event.sessionId,
          engineState: event.state,
          progress: event.progress ?? state.progress,
          liveParticipants: event.participants,
          session: _draftSession(
            topic: topic,
            scenarioKey: scenarioKey,
            sessionId: event.sessionId,
            participants: event.participants,
            engineState: event.state,
          ),
        );
        return;
      case 'round':
        final updatedRounds = event.rounds.isNotEmpty
            ? event.rounds
            : [
                ...state.liveRounds,
                if (event.round != null) event.round!,
              ];
        state = state.copyWith(
          sessionId: event.sessionId,
          engineState: event.state,
          progress: event.progress ?? state.progress,
          liveRounds: updatedRounds,
          liveInsightSummary: '讨论已推进到第 ${updatedRounds.length} 轮，正在汇总关键分歧与共识。',
          session: _draftSession(
            topic: topic,
            scenarioKey: scenarioKey,
            sessionId: event.sessionId,
            participants: state.liveParticipants,
            rounds: updatedRounds,
            engineState: event.state,
            insightSummary: '讨论已推进到第 ${updatedRounds.length} 轮，正在汇总关键分歧与共识。',
          ),
        );
        return;
      case 'complete':
        final session = event.session;
        state = state.copyWith(
          isLoading: false,
          session: session,
          sessionId: session?.id ?? event.sessionId,
          engineState: session?.state ?? event.state,
          progress: event.progress ?? 1,
          liveParticipants: session?.participants ?? state.liveParticipants,
          liveRounds: session?.rounds ?? state.liveRounds,
          liveInsightSummary: session?.insightSummary ?? state.liveInsightSummary,
        );
        return;
      case 'error':
        state = state.copyWith(
          isLoading: false,
          error: event.message ?? '模拟生成失败',
        );
        return;
      case 'done':
        state = state.copyWith(
          isLoading: false,
          progress: state.progress == 0 ? 1 : state.progress,
        );
        return;
      default:
        return;
    }
  }

  SimulationSessionModel _draftSession({
    required String topic,
    required String scenarioKey,
    String? sessionId,
    List<SimulationParticipantModel>? participants,
    List<SimulationRoundModel>? rounds,
    String? engineState,
    String? insightSummary,
  }) =>
      SimulationSessionModel(
        id: sessionId ?? state.sessionId ?? '',
        scenarioKey: scenarioKey,
        state: engineState ?? state.engineState ?? 'RUNNING',
        topic: topic,
        participants: participants ?? state.liveParticipants,
        rounds: rounds ?? state.liveRounds,
        insightSummary: insightSummary ??
            state.liveInsightSummary ??
            '模拟进行中，正在汇总当前讨论洞察...',
      );
}

final simulationProvider =
    StateNotifierProvider<SimulationNotifier, SimulationState>(
  (ref) => SimulationNotifier(ref.watch(simulationRepositoryProvider)),
);
