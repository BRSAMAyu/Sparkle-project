import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/plan/data/repositories/plan_repository.dart';

/// CP-01-MOBILE：计划人工确认的会话内状态。
///
/// 为什么是会话级而非挂在 [PlanModel]：GET /plans/{id} 的响应契约不含
/// confirmed_at（后端 CP-01 仅新增 confirm 端点，未扩资源 schema），客户端
/// 无法从拉取侧得知已确认态；确认事实只能由本端点的幂等 200 摘要给出。
/// 因此确认后本地记录 confirmed_at，本次会话内呈现已确认态；重复点击由
/// 后端幂等兜底（already_confirmed 不当错误）。
enum PlanConfirmOutcome { confirmed, alreadyConfirmed, failed }

class PlanConfirmState {
  const PlanConfirmState({
    this.inFlight = false,
    this.confirmed = false,
    this.confirmedAt,
    this.error,
  });

  /// 请求在途（按钮禁用，防双击重放）。
  final bool inFlight;

  /// 已确认（来自后端 200 摘要的幂等事实，独立于时间戳是否可解析）。
  final bool confirmed;

  /// 确认时间（来自后端摘要；重复确认时为首次确认时间戳）。
  final DateTime? confirmedAt;

  /// 最近一次失败的原因摘要（供错误面呈现）。
  final String? error;

  bool get isConfirmed => confirmed;

  PlanConfirmState copyWith({
    bool? inFlight,
    bool? confirmed,
    DateTime? confirmedAt,
    String? error,
    bool clearError = false,
  }) =>
      PlanConfirmState(
        inFlight: inFlight ?? this.inFlight,
        confirmed: confirmed ?? this.confirmed,
        confirmedAt: confirmedAt ?? this.confirmedAt,
        error: clearError ? null : error ?? this.error,
      );
}

class PlanConfirmNotifier extends StateNotifier<PlanConfirmState> {
  PlanConfirmNotifier(this._repository) : super(const PlanConfirmState());

  final PlanRepository _repository;

  /// 返回确认结果供 UI 反馈；failed 时错误详情在 [PlanConfirmState.error]。
  Future<PlanConfirmOutcome> confirm(String planId) async {
    if (state.inFlight) return PlanConfirmOutcome.failed;
    state = state.copyWith(inFlight: true, clearError: true);
    try {
      final result = await _repository.confirmPlan(planId);
      if (!mounted) return PlanConfirmOutcome.failed;
      state = PlanConfirmState(confirmed: true, confirmedAt: result.confirmedAt);
      return result.alreadyConfirmed
          ? PlanConfirmOutcome.alreadyConfirmed
          : PlanConfirmOutcome.confirmed;
    } catch (e) {
      if (!mounted) return PlanConfirmOutcome.failed;
      state = state.copyWith(inFlight: false, error: e.toString());
      return PlanConfirmOutcome.failed;
    }
  }
}

/// 按计划 id 家族化的确认状态（详情屏头卡消费）。
final planConfirmProvider =
    StateNotifierProvider.family<PlanConfirmNotifier, PlanConfirmState, String>(
  (ref, planId) => PlanConfirmNotifier(ref.watch(planRepositoryProvider)),
);
