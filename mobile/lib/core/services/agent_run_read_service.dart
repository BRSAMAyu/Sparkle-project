import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

/// X-05 · Unified Agent Run —— 只读消费服务。
///
/// 权威 run 状态在服务端 ``agent_runs``（引擎单一权威端点 ``GET /api/v1/runs``）。
/// 本服务与 provider 的缓存**可丢弃可重建**：App 杀进程重开后按 run_id（或
/// active 过滤）重新拉取即恢复（AGENT_RUNTIME.md §5「客户端不是 runtime
/// owner」）。App 内存永不作为第二真源——本文件没有任何本地持久化。
class AgentRunView {
  const AgentRunView({
    required this.runId,
    required this.status,
    required this.isTerminal,
    required this.objective,
    this.kind,
    this.taskId,
    this.intentId,
    this.waitKind,
    this.currentStage,
    this.stepsDone = 0,
    this.stepsTotal,
    this.terminalReason,
    this.errorMessage,
    this.updatedAt,
  });

  factory AgentRunView.fromJson(Map<String, dynamic> json) => AgentRunView(
        runId: json['run_id'] as String,
        status: json['status'] as String? ?? 'QUEUED',
        isTerminal: json['is_terminal'] as bool? ?? false,
        objective: json['objective'] as String? ?? '',
        kind: json['kind'] as String?,
        taskId: json['task_id'] as String?,
        intentId: json['intent_id'] as String?,
        waitKind: json['wait_kind'] as String?,
        currentStage: json['current_stage'] as String?,
        stepsDone: (json['steps_done'] as num?)?.toInt() ?? 0,
        stepsTotal: (json['steps_total'] as num?)?.toInt(),
        terminalReason: json['terminal_reason'] as String?,
        errorMessage: json['error_message'] as String?,
        updatedAt: json['updated_at'] as String?,
      );

  final String runId;
  final String status;
  final bool isTerminal;

  /// UI 阶段呈现（AGENT_RUNTIME.md §8：显示阶段而非 chain-of-thought）。
  final String objective;
  final String? kind;
  final String? taskId;
  final String? intentId;
  final String? waitKind;
  final String? currentStage;
  final int stepsDone;
  final int? stepsTotal;
  final String? terminalReason;
  final String? errorMessage;
  final String? updatedAt;

  bool get isAwaitingUser =>
      status == 'AWAITING_USER' || status == 'AWAITING_APPROVAL';

  String get stageLabel {
    if (isAwaitingUser) {
      return waitKind == 'approval' ? '等你确认' : '等你补充';
    }
    if (status == 'EXECUTING' && stepsTotal != null) {
      return '正在执行 $stepsDone/$stepsTotal';
    }
    return currentStage ?? status;
  }
}

class AgentRunReadService {
  AgentRunReadService(this._ref);

  final Ref _ref;

  /// 权威读取：按 run_id（App 重开后唯一需要携带的东西）。
  Future<AgentRunView?> fetchRun(String runId) async {
    final client = _ref.read(apiClientProvider);
    try {
      final response = await client.get<Map<String, dynamic>>(ApiEndpoints.agentRun(runId));
      final data = response.data?['run'];
      if (data is Map<String, dynamic>) {
        return AgentRunView.fromJson(data);
      }
      return null;
    } on Exception {
      return null;
    }
  }

  /// 找回活跃 run（不记得 run_id 的重开旅程）。
  Future<List<AgentRunView>> fetchActiveRuns({String? taskId}) async {
    final client = _ref.read(apiClientProvider);
    try {
      final query = <String, dynamic>{'active': true};
      if (taskId != null) {
        query['task_id'] = taskId;
      }
      final response = await client.get<Map<String, dynamic>>(
        ApiEndpoints.agentRuns,
        queryParameters: query,
      );
      final items = response.data?['items'];
      if (items is List) {
        return items
            .whereType<Map<String, dynamic>>()
            .map(AgentRunView.fromJson)
            .toList(growable: false);
      }
      return const [];
    } on Exception {
      return const [];
    }
  }
}

final agentRunReadServiceProvider =
    Provider<AgentRunReadService>(AgentRunReadService.new);

/// 可丢弃可重建的 run 状态缓存：杀进程即消失，重开经 [AgentRunReadService]
/// 重新拉取。UI 通过 invalidate/refresh 触发重查，不本地写状态。
final agentRunViewProvider =
    FutureProvider.autoDispose.family<AgentRunView?, String>((ref, runId) async {
  final service = ref.watch(agentRunReadServiceProvider);
  return service.fetchRun(runId);
});

final activeAgentRunsProvider = FutureProvider.autoDispose<List<AgentRunView>>(
  (ref) => ref.watch(agentRunReadServiceProvider).fetchActiveRuns(),
);
