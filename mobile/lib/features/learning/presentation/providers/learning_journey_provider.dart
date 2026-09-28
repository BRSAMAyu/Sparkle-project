import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/learning/data/learning_journey_models.dart';
import 'package:sparkle/features/learning/data/learning_journey_repository.dart';

/// 旅程网络面（测试可注入：override 本 provider 即可换假仓库）。
final Provider<LearningJourneyRepository> learningJourneyRepositoryProvider =
    Provider<LearningJourneyRepository>((Ref ref) => LearningJourneyRepository(Dio()));

/// 旅程页状态（装配视图 + 检验入口面 + 手输替代草稿）。
class LearningJourneyState {
  const LearningJourneyState({
    this.view,
    this.error,
    this.loading = false,
    this.checkQuestion,
    this.checkHoldReason,
    this.verdict,
    this.submitting = false,
    this.manualInputs = const <String, String>{},
  });

  final LearningJourneyView? view;
  final String? error;
  final bool loading;

  /// 检验入口放行后的题面（红化门产物；degraded=true 时 UI 走降级文案）。
  final LearningCheckQuestion? checkQuestion;
  final String? checkHoldReason;
  final LearningCheckVerdict? verdict;
  final bool submitting;

  /// 材料手输替代草稿（key = source_id；OCR 失败/不支持的文本替代，零伪造）。
  final Map<String, String> manualInputs;

  bool get hasContext => view != null;

  LearningJourneyState copyWith({
    LearningJourneyView? view,
    String? error,
    bool? loading,
    LearningCheckQuestion? checkQuestion,
    String? checkHoldReason,
    LearningCheckVerdict? verdict,
    bool? submitting,
    Map<String, String>? manualInputs,
    bool clearCheck = false,
    bool clearVerdict = false,
    bool clearHold = false,
  }) =>
      LearningJourneyState(
        view: view ?? this.view,
        error: error ?? this.error,
        loading: loading ?? this.loading,
        checkQuestion: clearCheck ? null : (checkQuestion ?? this.checkQuestion),
        checkHoldReason: clearHold ? null : (checkHoldReason ?? this.checkHoldReason),
        verdict: clearVerdict ? null : (verdict ?? this.verdict),
        submitting: submitting ?? this.submitting,
        manualInputs: manualInputs ?? this.manualInputs,
      );
}

/// 旅程状态机（目标上下文 → 装配 → 资料/错题/练习/检验）。
class LearningJourneyNotifier extends StateNotifier<LearningJourneyState> {
  LearningJourneyNotifier(this._repository, this._context)
      : super(const LearningJourneyState(loading: true)) {
    unawaited(_load());
  }

  final LearningJourneyRepository _repository;
  final LearningJourneyContext _context;

  LearningJourneyContext get journeyContext => _context;

  Future<void> _load() async {
    state = state.copyWith(loading: true);
    try {
      final view = await _repository.getJourney(goalTaskId: _context.goalTaskId);
      state = state.copyWith(view: view, loading: false);
    } on LearningJourneyRepositoryException catch (error) {
      state = state.copyWith(loading: false, error: error.message);
    } catch (_) {
      state = state.copyWith(loading: false, error: 'learningJourneyLoadFailed');
    }
  }

  Future<void> reload() => _load();

  /// 用户显式选择「检验」：证据不支持 → holdReason（原地，不进检验空页）。
  Future<void> requestCheck() async {
    state = state.copyWith(submitting: true, clearVerdict: true, clearHold: true);
    try {
      final result = await _repository.enterCheck(goalTaskId: _context.goalTaskId);
      state = state.copyWith(
        submitting: false,
        checkQuestion: result.available ? result.question : null,
        checkHoldReason: result.available ? null : (result.holdReason ?? 'HOLD.evidence_not_supported'),
      );
    } on LearningJourneyRepositoryException catch (error) {
      state = state.copyWith(submitting: false, error: error.message);
    }
  }

  /// 提交检验答案：判分面零答案材料（答案留在服务端权威）。
  Future<void> submitCheckAnswer(String answer) async {
    if (answer.trim().isEmpty || state.checkQuestion == null) {
      return;
    }
    state = state.copyWith(submitting: true);
    try {
      final verdict = await _repository.submitCheck(
        goalTaskId: _context.goalTaskId,
        answer: answer,
      );
      state = state.copyWith(submitting: false, verdict: verdict);
    } on LearningJourneyRepositoryException catch (error) {
      state = state.copyWith(submitting: false, error: error.message);
    }
  }

  /// 材料手输替代（OCR 失败/不支持的文本替代路径；永不伪造解析结果）。
  void saveManualInput(String sourceId, String text) {
    if (text.trim().isEmpty) {
      return;
    }
    final next = <String, String>{...state.manualInputs, sourceId: text.trim()};
    state = state.copyWith(manualInputs: next);
  }
}

final learningJourneyProvider =
    StateNotifierProvider.family<LearningJourneyNotifier, LearningJourneyState, LearningJourneyContext>(
  (Ref ref, LearningJourneyContext context) =>
      LearningJourneyNotifier(ref.watch(learningJourneyRepositoryProvider), context),
);
