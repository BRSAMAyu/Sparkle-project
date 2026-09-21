import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

/// X-07 · run 步骤 wire 投影（只读；真源是服务端 ``agent_runs.steps``）。
///
/// owner 词表与 U-04 ``ProposalTurnOwnership`` / 服务端 ``app/core/run_steps.py``
/// StepOwner 同名对齐（"human"/"agent"/"hybrid"）——「轮到谁」从持久化推导，
/// HUMAN（你做）态自此可达（解 U-04 P2：此前 ownership 只能由 authMode 推导）。
class AgentRunStepView {
  const AgentRunStepView({
    required this.stepId,
    required this.ordinal,
    required this.owner,
    required this.completed,
    this.label,
    this.completionKind,
    this.artifactRefs = const <AgentRunArtifactRef>[],
  });

  factory AgentRunStepView.fromJson(Map<String, dynamic> json) =>
      AgentRunStepView(
        stepId: (json['step_id'] ?? '').toString(),
        ordinal: (json['ordinal'] as num?)?.toInt() ?? 0,
        owner: (json['owner'] ?? json['ownership'] ?? 'hybrid').toString(),
        completed: json['completed'] as bool? ?? false,
        label: json['label']?.toString(),
        completionKind:
            (json['completion_condition'] is Map
                ? (json['completion_condition'] as Map)['kind']
                : null)
                ?.toString(),
        artifactRefs: _parseArtifacts(json['artifacts']),
      );

  static List<AgentRunArtifactRef> _parseArtifacts(Object? raw) {
    if (raw is! List) return const <AgentRunArtifactRef>[];
    return raw
        .whereType<Map<dynamic, dynamic>>()
        .map(
          (e) => AgentRunArtifactRef(
            scheme: (e['scheme'] ?? '').toString(),
            ref: (e['ref'] ?? '').toString(),
          ),
        )
        .toList(growable: false);
  }

  final String stepId;
  final int ordinal;

  /// "human" | "agent" | "hybrid"（封闭词表，越表按 hybrid 诚实降级）。
  final String owner;
  final bool completed;
  final String? label;

  /// 完成条件 kind：agent_output / user_confirmation / user_edit。
  final String? completionKind;
  final List<AgentRunArtifactRef> artifactRefs;
}

/// 步骤产物引用（scheme://ref 语义；本体留在既有机制——proposal receipt /
/// 工具账本 / 证据库，run 内只持引用）。
class AgentRunArtifactRef {
  const AgentRunArtifactRef({required this.scheme, required this.ref});

  final String scheme;
  final String ref;

  String get label => '$scheme://$ref';
}

/// 「当前 awaiting step」投影（服务端从持久化推导；App 冷启动直接消费）。
///
/// ``state``：awaiting（等你做）/ expired（等待窗口已过）/ cancelled（已取消）
/// ——取消与过期显式可见，绝不伪装成可继续。
class AgentRunAwaitingStep {
  const AgentRunAwaitingStep({
    required this.stepId,
    required this.ordinal,
    required this.owner,
    required this.state,
    this.label,
    this.prompt,
    this.expiresAt,
    this.artifactRefs = const <AgentRunArtifactRef>[],
  });

  factory AgentRunAwaitingStep.fromJson(Map<String, dynamic> json) =>
      AgentRunAwaitingStep(
        stepId: (json['step_id'] ?? '').toString(),
        ordinal: (json['ordinal'] as num?)?.toInt() ?? 0,
        owner: (json['owner'] ?? json['ownership'] ?? 'hybrid').toString(),
        state: (json['state'] ?? '').toString(),
        label: json['label']?.toString(),
        prompt: json['prompt']?.toString(),
        expiresAt: json['expires_at']?.toString(),
        artifactRefs: AgentRunStepView._parseArtifacts(json['artifacts']),
      );

  final String stepId;
  final int ordinal;
  final String owner;

  /// "awaiting" | "expired" | "cancelled"。
  final String state;
  final String? label;
  final String? prompt;
  final String? expiresAt;
  final List<AgentRunArtifactRef> artifactRefs;

  bool get isAwaiting => state == 'awaiting';
  bool get isExpired => state == 'expired';
  bool get isCancelled => state == 'cancelled';
}

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
    this.steps = const <AgentRunStepView>[],
    this.awaitingStep,
  });

  factory AgentRunView.fromJson(Map<String, dynamic> json) {
    final stepsRaw = json['steps'];
    final awaitingRaw = json['awaiting_step'];
    return AgentRunView(
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
      steps: stepsRaw is List
          ? stepsRaw
              .whereType<Map<dynamic, dynamic>>()
              .map((e) => AgentRunStepView.fromJson(Map<String, dynamic>.from(e)))
              .toList(growable: false)
          : const <AgentRunStepView>[],
      awaitingStep: awaitingRaw is Map<String, dynamic>
          ? AgentRunAwaitingStep.fromJson(awaitingRaw)
          : null,
    );
  }

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

  /// X-07 · hybrid 步骤计划（含 owner/completed；只读投影）。
  final List<AgentRunStepView> steps;

  /// X-07 · 推导的「当前 awaiting step」（通知点击/冷启动重开的恢复锚点）。
  final AgentRunAwaitingStep? awaitingStep;

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
