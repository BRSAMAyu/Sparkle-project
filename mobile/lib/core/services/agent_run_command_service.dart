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
  /// 返回服务端 run 投影（``step_replay=true`` 表示幂等重放：该步骤此前已
  /// 完成，本次未再次 resume——UI 据此提示「已经确认过了」而非报错）。
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
