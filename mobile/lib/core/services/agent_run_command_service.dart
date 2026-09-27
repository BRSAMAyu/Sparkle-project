import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

/// X-07 · Agent Run 命令面（用户确认/编辑触发 resume + 取消）.
///
/// 真源分工：run 状态与步骤完成戳的唯一写入权威是引擎
/// ``app/services/agent_run_service.py``；网关 `/runs/*path` 纯代理；本服务
/// 只做命令转发，**不重建**幂等语义——幂等键由 [runStepActionIdempotencyKey]
/// 按 (runId, stepId, action) **确定性推导**：重建/重进/重开后同一步骤的同
/// 一动作仍得到同一个键，服务端据此 first-wins（步骤已有完成戳 → 重放
/// no-op），「用户操作两次不会 resume 两次」。
class AgentRunCommandService {
  AgentRunCommandService(this._ref);

  final Ref _ref;

  ApiClient get _client => _ref.read(apiClientProvider);

  /// 用户完成 awaiting step（确认/编辑）→ 完成戳 + resume 同事务.
  ///
  /// 返回服务端 run 投影（``step_replay=not result.applied``，runs.py）：
  /// ``step_replay=true`` 表示幂等重放——该步骤此前已完成，本次未再次 resume。
  ///
  /// **消费现状（V3-FIX-379① 撤承诺裁决）**：本命令面当前零调用点——移动端
  /// 唯一 awaiting-step 面（J-06 hybrid journey sheet）交付确认走
  /// `/journey/hybrid/{runId}/outcome/confirm`（任务完成 + outcome 捕获与
  /// 完成戳同在该端点，generic step-complete 不承载），其幂等重放由服务端
  /// `_confirmed_replay` 直接回 200 + 终态 SUCCEEDED 投影，sheet 渲染完成面、
  /// 无错误面——「已经确认过了」需求已被现行端点覆盖。本方法保留为 X-07
  /// 命令能力层（379③ 恢复锚点族；零消费≠死代码）；未来挂载面必须消费
  /// `step_replay`——true 时呈现「已经确认过了」而非报错，该要求随挂载卡
  /// 承接，本文档不再许诺不存在的 UI 行为。
  Future<Map<String, dynamic>> completeStep(
    String runId,
    String stepId, {
    required String idempotencyKey,
    String action = 'confirm',
    String? note,
  }) async {
    final response = await _client.post<Map<String, dynamic>>(
      ApiEndpoints.runStepComplete(runId, stepId),
      data: <String, dynamic>{
        'idempotency_key': idempotencyKey,
        'action': action,
        if (note != null) 'note': note,
      },
    );
    return response.data ?? const <String, dynamic>{};
  }

  /// 用户取消 run（user_cancelled；等待中/执行中均可，终态封闭不可逆）.
  Future<Map<String, dynamic>> cancelRun(
    String runId, {
    String? idempotencyKey,
  }) async {
    final response = await _client.post<Map<String, dynamic>>(
      ApiEndpoints.agentRunCancel(runId),
      data: <String, dynamic>{
        'reason': 'user_cancelled',
        if (idempotencyKey != null) 'idempotency_key': idempotencyKey,
      },
    );
    return response.data ?? const <String, dynamic>{};
  }
}

/// 稳定幂等键推导（X-09 语义的移动端对齐；U-04 `u04:<proposalId>:<action>`
/// 同款推导式）。同一 (run, step, action) 恒同键 → 服务端重放收敛。
String runStepActionIdempotencyKey(String runId, String stepId, String action) =>
    'x07:$runId:$stepId:$action';

final agentRunCommandServiceProvider =
    Provider<AgentRunCommandService>(AgentRunCommandService.new);
