import 'package:sparkle/core/services/i18n_service.dart';

enum ExecutionMode {
  human,
  agent,
  hybrid,
  unknown,
}

enum ExecutionIntentStatus {
  draft,
  ready,
  queued,
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
    case 'queued':
      return ExecutionIntentStatus.queued;
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
    this.targetEnv,
    this.templateId,
    this.templateName,
    this.strategyVariant,
    this.targetNodeId,
    this.targetNodeLabel,
    this.approvalPolicy,
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
        targetEnv: json['target_env'] as String?,
        status: _parseExecutionStatus(json['status'] as String?),
        trustLevel: _parseTrustLevel(json['trust_level'] as String?),
        templateId: json['template_id'] as String?,
        templateName: json['template_name'] as String?,
        strategyVariant: json['strategy_variant'] as String?,
        targetNodeId: json['target_node_id'] as String?,
        targetNodeLabel: json['target_node_label'] as String?,
        approvalPolicy: json['approval_policy'] as String?,
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
  final String? targetEnv;
  final ExecutionIntentStatus status;
  final ExecutionTrustLevel trustLevel;
  final String? templateId;
  final String? templateName;
  final String? strategyVariant;
  final String? targetNodeId;
  final String? targetNodeLabel;
  final String? approvalPolicy;
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
      case ExecutionIntentStatus.queued:
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
      case ExecutionIntentStatus.queued:
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
    final l10n = I18nService.instance.l10n;
    switch (status) {
      case ExecutionIntentStatus.draft:
        return l10n.executionStatusDraft;
      case ExecutionIntentStatus.ready:
        return l10n.executionStatusReady;
      case ExecutionIntentStatus.queued:
        return l10n.executionStatusQueued;
      case ExecutionIntentStatus.dispatched:
        return l10n.executionStatusDispatched;
      case ExecutionIntentStatus.running:
        return l10n.executionStatusRunning;
      case ExecutionIntentStatus.waitingApproval:
        return l10n.executionStatusWaitingApproval;
      case ExecutionIntentStatus.succeeded:
        return l10n.executionStatusSucceeded;
      case ExecutionIntentStatus.partial:
        return l10n.executionStatusPartial;
      case ExecutionIntentStatus.failed:
        return l10n.executionStatusFailed;
      case ExecutionIntentStatus.canceled:
        return l10n.executionStatusCanceled;
      case ExecutionIntentStatus.timedOut:
        return l10n.executionStatusTimedOut;
      case ExecutionIntentStatus.handedBack:
        return l10n.executionStatusHandedBack;
      case ExecutionIntentStatus.unknown:
        return l10n.executionStatusUnknown;
    }
  }

  String get trustLabel {
    final l10n = I18nService.instance.l10n;
    switch (trustLevel) {
      case ExecutionTrustLevel.raw:
        return l10n.executionTrustRaw;
      case ExecutionTrustLevel.validated:
        return l10n.executionTrustValidated;
      case ExecutionTrustLevel.trusted:
        return l10n.executionTrustTrusted;
      case ExecutionTrustLevel.unknown:
        return l10n.executionTrustUnknown;
    }
  }
}
