/// CP-01：`POST /plans/{id}/confirm` 的确认摘要响应。
///
/// 后端语义（commit 308400d1）：首次确认返回 `already_confirmed:false` 与
/// 确认时间戳；重复确认幂等返回 `already_confirmed:true` 且保留首次时间戳；
/// 他人/不存在/软删统一 404。手写 fromJson（一次性摘要契约，非资源模型，
/// 对齐 PlanPhaseBundle 的手写解析风格，不进 build_runner）。
class PlanConfirmResult {
  const PlanConfirmResult({
    required this.planId,
    required this.alreadyConfirmed,
    this.confirmedAt,
    this.message,
  });

  factory PlanConfirmResult.fromJson(Map<String, dynamic> json) {
    final confirmedAtRaw = json['confirmed_at'];
    return PlanConfirmResult(
      planId: '${json['plan_id'] ?? ''}',
      alreadyConfirmed: json['already_confirmed'] == true,
      confirmedAt: confirmedAtRaw is String ? DateTime.tryParse(confirmedAtRaw) : null,
      message: json['message'] is String ? json['message'] as String : null,
    );
  }

  final String planId;
  final bool alreadyConfirmed;
  final DateTime? confirmedAt;
  final String? message;
}
