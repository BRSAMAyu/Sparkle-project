import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';
import 'package:sparkle/features/recovery/data/repositories/stuck_journey_repository.dart';

/// J-05 ·「我卡住了」统一恢复旅程控制器。
///
/// 状态机：loading → ready（问句或主判断）→ busy（答/纠正进行中）→
/// ready(新载荷)；error 可重试（重新 start）。任何一步失败都如实呈现
/// 错误态 + 重试，不静默降级、不伪造判断。
///
/// N9/N15 纪律：state 只存类型化错误类别（人话文案由 [uiErrorMessage]
/// 出 arb 词条），原始异常对象只进 debugPrint 日志，绝不进 UI 字段。
enum StuckJourneyStatus { loading, ready, error }

class StuckJourneyState {
  const StuckJourneyState({
    this.status = StuckJourneyStatus.loading,
    this.payload,
    this.busy = false,
    this.errorCategory,
  });

  final StuckJourneyStatus status;
  final StuckJourneyPayload? payload;
  final bool busy;
  final UiErrorCategory? errorCategory;

  StuckJourneyState copyWith({
    StuckJourneyStatus? status,
    StuckJourneyPayload? payload,
    bool? busy,
    UiErrorCategory? errorCategory,
  }) =>
      StuckJourneyState(
        status: status ?? this.status,
        payload: payload ?? this.payload,
        busy: busy ?? this.busy,
        errorCategory: errorCategory,
      );
}

class StuckJourneyController extends StateNotifier<StuckJourneyState> {
  StuckJourneyController(this._repo, this._request)
      : super(const StuckJourneyState()) {
    unawaited(_start());
  }

  final StuckJourneyRepository _repo;
  final StuckJourneyRequest _request;

  Future<void> _start() async {
    state = const StuckJourneyState();
    try {
      final payload = await _repo.startJourney(
        surface: _request.surface,
        goalId: _request.goalId,
        taskId: _request.taskId,
      );
      state = StuckJourneyState(
        status: StuckJourneyStatus.ready,
        payload: payload,
      );
    } catch (error) {
      // 原始异常只进日志（诊断面）；UI 消费类别化词条（N9/N15）。
      debugPrint(
        '[stuck-journey] start failed surface=${_request.surface} '
        'goal=${_request.goalId} task=${_request.taskId}: $error',
      );
      state = StuckJourneyState(
        status: StuckJourneyStatus.error,
        errorCategory: categorizeUiError(error),
      );
    }
  }

  Future<void> retry() => _start();

  /// 回答单问（branch_key 直传主路径）→ 收敛到主判断。
  Future<void> answer(String questionId, String branchKey) async {
    if (state.busy) return;
    state = state.copyWith(busy: true);
    try {
      final payload = await _repo.answerQuestion(
        surface: _request.surface,
        questionId: questionId,
        branchKey: branchKey,
        goalId: _request.goalId,
        taskId: _request.taskId,
      );
      state = StuckJourneyState(
        status: StuckJourneyStatus.ready,
        payload: payload,
      );
    } catch (error) {
      debugPrint('[stuck-journey] answer failed: $error');
      state = state.copyWith(
        busy: false,
        errorCategory: categorizeUiError(error),
      );
    }
  }

  /// 「不是这个原因」纠正 → 反馈环落库 + 按纠正重派生的输出。
  Future<void> correct(String frictionType, {String? interventionKey}) async {
    if (state.busy) return;
    state = state.copyWith(busy: true);
    try {
      final result = await _repo.correct(
        surface: _request.surface,
        frictionType: frictionType,
        interventionKey: interventionKey,
        goalId: _request.goalId,
        taskId: _request.taskId,
      );
      state = StuckJourneyState(
        status: StuckJourneyStatus.ready,
        payload: result.journey,
      );
    } catch (error) {
      debugPrint('[stuck-journey] correct failed: $error');
      state = state.copyWith(
        busy: false,
        errorCategory: categorizeUiError(error),
      );
    }
  }
}

final stuckJourneyProvider = StateNotifierProvider.autoDispose
    .family<StuckJourneyController, StuckJourneyState, StuckJourneyRequest>(
  (ref, request) =>
      StuckJourneyController(ref.watch(stuckJourneyRepositoryProvider), request),
);
