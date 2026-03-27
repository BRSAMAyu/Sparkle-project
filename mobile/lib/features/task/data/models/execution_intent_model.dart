enum ExecutionMode {
  human,
  agent,
  hybrid,
  unknown,
}

enum ExecutionIntentStatus {
  draft,
  ready,
  dispatched,
  running,
  waitingApproval,
  succeeded,
  partial,
  failed,
  canceled,
  timedOut,
  handedBack,
  unknown,
}

enum ExecutionTrustLevel {
  raw,
  validated,
  trusted,
  unknown,
}

ExecutionMode _parseExecutionMode(String? value) {
  switch (value) {
    case 'human':
      return ExecutionMode.human;
    case 'agent':
      return ExecutionMode.agent;
    case 'hybrid':
      return ExecutionMode.hybrid;
    default:
      return ExecutionMode.unknown;
  }
}

ExecutionIntentStatus _parseExecutionStatus(String? value) {
  switch (value) {
    case 'draft':
      return ExecutionIntentStatus.draft;
    case 'ready':
      return ExecutionIntentStatus.ready;
    case 'dispatched':
      return ExecutionIntentStatus.dispatched;
    case 'running':
      return ExecutionIntentStatus.running;
    case 'waiting_approval':
      return ExecutionIntentStatus.waitingApproval;
    case 'succeeded':
      return ExecutionIntentStatus.succeeded;
    case 'partial':
      return ExecutionIntentStatus.partial;
    case 'failed':
      return ExecutionIntentStatus.failed;
    case 'canceled':
      return ExecutionIntentStatus.canceled;
    case 'timed_out':
      return ExecutionIntentStatus.timedOut;
    case 'handed_back':
      return ExecutionIntentStatus.handedBack;
    default:
      return ExecutionIntentStatus.unknown;
  }
}

ExecutionTrustLevel _parseTrustLevel(String? value) {
  switch (value) {
    case 'raw':
      return ExecutionTrustLevel.raw;
    case 'validated':
      return ExecutionTrustLevel.validated;
    case 'trusted':
      return ExecutionTrustLevel.trusted;
    default:
      return ExecutionTrustLevel.unknown;
  }
}

DateTime? _tryParseDateTime(String? value) =>
    value == null ? null : DateTime.tryParse(value);

class ExecutionIntentModel {
  const ExecutionIntentModel({
    required this.id,
    required this.taskId,
    required this.executionMode,
    required this.executor,
    required this.status,
    required this.trustLevel,
    required this.goal,
    this.planId,
    this.externalRunId,
    this.errorCategory,
    this.errorMessage,
    this.dispatchedAt,
    this.completedAt,
    this.createdAt,
  });

  factory ExecutionIntentModel.fromJson(Map<String, dynamic> json) =>
      ExecutionIntentModel(
        id: json['id'] as String? ?? '',
        taskId: json['task_id'] as String? ?? '',
        planId: json['plan_id'] as String?,
        executionMode: _parseExecutionMode(json['execution_mode'] as String?),
        executor: json['executor'] as String? ?? 'manual',
        status: _parseExecutionStatus(json['status'] as String?),
        trustLevel: _parseTrustLevel(json['trust_level'] as String?),
        externalRunId: json['external_run_id'] as String?,
        goal: json['goal'] as String? ?? '',
        errorCategory: json['error_category'] as String?,
        errorMessage: json['error_message'] as String?,
        dispatchedAt: _tryParseDateTime(json['dispatched_at'] as String?),
        completedAt: _tryParseDateTime(json['completed_at'] as String?),
        createdAt: _tryParseDateTime(json['created_at'] as String?),
      );

  final String id;
  final String taskId;
  final String? planId;
  final ExecutionMode executionMode;
  final String executor;
  final ExecutionIntentStatus status;
  final ExecutionTrustLevel trustLevel;
  final String? externalRunId;
  final String goal;
  final String? errorCategory;
  final String? errorMessage;
  final DateTime? dispatchedAt;
  final DateTime? completedAt;
  final DateTime? createdAt;

  bool get isTerminal {
    switch (status) {
      case ExecutionIntentStatus.succeeded:
      case ExecutionIntentStatus.partial:
      case ExecutionIntentStatus.failed:
      case ExecutionIntentStatus.canceled:
      case ExecutionIntentStatus.timedOut:
      case ExecutionIntentStatus.handedBack:
        return true;
      case ExecutionIntentStatus.draft:
      case ExecutionIntentStatus.ready:
      case ExecutionIntentStatus.dispatched:
      case ExecutionIntentStatus.running:
      case ExecutionIntentStatus.waitingApproval:
      case ExecutionIntentStatus.unknown:
        return false;
    }
  }

  bool get isRunning {
    switch (status) {
      case ExecutionIntentStatus.dispatched:
      case ExecutionIntentStatus.running:
      case ExecutionIntentStatus.waitingApproval:
        return true;
      case ExecutionIntentStatus.draft:
      case ExecutionIntentStatus.ready:
      case ExecutionIntentStatus.succeeded:
      case ExecutionIntentStatus.partial:
      case ExecutionIntentStatus.failed:
      case ExecutionIntentStatus.canceled:
      case ExecutionIntentStatus.timedOut:
      case ExecutionIntentStatus.handedBack:
      case ExecutionIntentStatus.unknown:
        return false;
    }
  }

  bool get isWaitingApproval => status == ExecutionIntentStatus.waitingApproval;

  String get statusLabel {
    switch (status) {
      case ExecutionIntentStatus.draft:
        return '待准备';
      case ExecutionIntentStatus.ready:
        return '准备完成';
      case ExecutionIntentStatus.dispatched:
        return '已发送';
      case ExecutionIntentStatus.running:
        return '执行中';
      case ExecutionIntentStatus.waitingApproval:
        return '等待确认';
      case ExecutionIntentStatus.succeeded:
        return '执行成功';
      case ExecutionIntentStatus.partial:
        return '部分完成';
      case ExecutionIntentStatus.failed:
        return '执行失败';
      case ExecutionIntentStatus.canceled:
        return '已取消';
      case ExecutionIntentStatus.timedOut:
        return '执行超时';
      case ExecutionIntentStatus.handedBack:
        return '已交还';
      case ExecutionIntentStatus.unknown:
        return '状态未知';
    }
  }

  String get trustLabel {
    switch (trustLevel) {
      case ExecutionTrustLevel.raw:
        return '原始结果';
      case ExecutionTrustLevel.validated:
        return '已校验';
      case ExecutionTrustLevel.trusted:
        return '可信结果';
      case ExecutionTrustLevel.unknown:
        return '待评估';
    }
  }
}
