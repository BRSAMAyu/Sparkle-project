/// V4-U01 · `episode_resume_view.v1`（V4-I01 读模型）的移动端消费投影。
///
/// 契约真源：`backend/app/core/episode_resume_view.py`（冻结字段集 + 封闭
/// 词表 + `resume_view_stale_reason` 过期语义）。本模型是首页接续面的
/// **唯一**解析入口，纪律与 I01 逐字对齐：
///
/// - **它是读模型的投影，不是第二真源**：视图说什么就显示什么；任何字段
///   都不落本地持久层，退出即弃（B05 §5「带 TTL，不落第二真值表」）；
/// - **fail-closed**：schema_version 非 `episode_resume_view.v1`、必需键
///   缺失（goal/task ref、expires_at、freshness）→ [EpisodeResumeViewData.tryParse]
///   返回 null，调用方按「无接续上下文」隐藏，绝不当数据渲染；
/// - **未知键忽略**（B05 §8 双读纪律：旧客户端忽略未知可选字段），但
///   不依赖冻结字段集之外的任何键；
/// - **子结构词表越界不连坐**：last_valid_outcome / last_confirmed_step /
///   pending_human_step / why_now 任一子结构校验失败 → 仅该子结构置 null
///   （对齐 I01 §4.1 字段级降级），视图其余部分照常消费；
/// - **过期判定**：[episodeResumeStaleReason] 是 backend
///   `resume_view_stale_reason` 的客户端可判定子集——只判 `expires_at`；
///   `memory_epoch_changed` 需要当前 epoch 权威（移动端读侧无此真源），
///   不判（I01：过期后重算是权威出口）。过期视图只允许「说明不确定性」，
///   不允许静默接续（B05 §9 反例「过期 EpisodeResumeView 自动接续」）。
library;

/// 当前支持的接续视图契约版本（冻结；与 backend EPISODE_RESUME_VIEW_SCHEMA_VERSION 逐字一致）。
const String kEpisodeResumeViewSchemaVersion = 'episode_resume_view.v1';

/// context_receipt_ref 的封闭 scheme（backend CONTEXT_SELECTION_REF_SCHEME）。
const String kContextSelectionRefScheme = 'context_selection';

/// step_ref 允许的封闭 scheme（backend STEP_REF_SCHEMES）。
const Set<String> kResumeStepRefSchemes = <String>{'task', 'subtask'};

/// D-02 TruthClass 全 5 值 1:1（backend TRUTH_CLASS_VALUES；demo 透传不排除，
/// 呈现端对 demo 显式标注——本投影保留原值，由渲染层决定是否标注）。
const Set<String> kResumeTruthClassValues = <String>{
  'actual',
  'self_reported',
  'estimated',
  'demo',
  'unknown',
};

/// 类型化降级词表（backend RESUME_DEGRADE_REASONS 封闭五值；view=null 时
/// 响应携带的 reason_code 落这里，词表外原样保留供诊断，不猜语义）。
const Set<String> kResumeDegradeReasons = <String>{
  'object_not_found',
  'cross_object_access',
  'goal_unresolved',
  'goal_changed_requires_calibration',
  'context_receipt_missing',
};

/// `scheme://path` → scheme（与 backend _ref_scheme 同判）。
String? _refSchemeOf(String ref) {
  final index = ref.indexOf('://');
  if (index <= 0) {
    return null;
  }
  return ref.substring(0, index);
}

DateTime? _parseIso(Object? raw) {
  if (raw is! String || raw.isEmpty) {
    return null;
  }
  return DateTime.tryParse(raw);
}

/// `episode_resume_view.v1` 的封闭解析结果（fail-closed：结构损坏整体降级）。
class EpisodeResumeViewData {
  const EpisodeResumeViewData({
    required this.goalRef,
    required this.taskRef,
    required this.expiresAt,
    required this.computedAt,
    required this.memoryEpochAtCompute,
    required this.contextReceiptRef,
    this.runRef,
    this.lastOutcome,
    this.lastConfirmedStep,
    this.pendingHumanStep,
    this.whyNowStatement,
    this.whyNowConfidenceBand,
  });

  /// `goal://<id>`（冻结字段，非空）。
  final String goalRef;

  /// `task://<id>`（冻结字段，非空；与 cockpit 当前任务的绑定判定依据）。
  final String taskRef;

  /// `run://<id>` 或 null。
  final String? runRef;

  /// 上次有效结果（词表越界 → null，字段级降级）。
  final ResumeOutcomeView? lastOutcome;

  /// 上次确认步骤（scheme 越界/空描述 → null，字段级降级）。
  final ResumeStepView? lastConfirmedStep;

  /// 待人类步骤（空描述 → null，字段级降级）。
  final ResumePendingStepView? pendingHumanStep;

  /// why_now 陈述（I01 §4.1 字段级降级 → null；v1 行恒 null）。
  final String? whyNowStatement;

  /// why_now 置信档（四值封闭；词表外归 null 不显示）。
  final String? whyNowConfidenceBand;

  /// 视图过期时刻（冻结字段；缺失即解析失败）。
  final DateTime expiresAt;

  /// 计算时刻（freshness 三键之一）。
  final DateTime computedAt;

  /// 计算时钉住的 memory epoch。
  final int memoryEpochAtCompute;

  /// 本轮 ContextSelectionReceipt ref（context_selection://…）。
  final String contextReceiptRef;

  /// view.task_ref 的 task id（`task://<id>` → id；scheme 不符返回 null）。
  String? get taskId {
    if (_refSchemeOf(taskRef) != 'task') {
      return null;
    }
    final id = taskRef.substring('task://'.length);
    return id.isEmpty ? null : id;
  }

  /// 接续端点响应的 `view` 子对象 → 投影。结构损坏（版本不符/必需键缺失）
  /// → null（fail-closed，「无接续上下文」）。
  static EpisodeResumeViewData? tryParse(Map<String, dynamic> payload) {
    if (payload['schema_version']?.toString() != kEpisodeResumeViewSchemaVersion) {
      return null;
    }
    final goalRef = payload['goal_ref']?.toString() ?? '';
    final taskRef = payload['task_ref']?.toString() ?? '';
    if (goalRef.isEmpty || taskRef.isEmpty) {
      return null;
    }
    final expiresAt = _parseIso(payload['expires_at']);
    if (expiresAt == null) {
      return null;
    }
    final freshnessRaw = payload['freshness'];
    if (freshnessRaw is! Map) {
      return null;
    }
    final freshness = Map<String, dynamic>.from(freshnessRaw);
    final computedAt = _parseIso(freshness['computed_at']);
    final receiptRef = freshness['context_receipt_ref']?.toString() ?? '';
    final epochRaw = freshness['memory_epoch_at_compute'];
    if (computedAt == null ||
        receiptRef.isEmpty ||
        _refSchemeOf(receiptRef) != kContextSelectionRefScheme ||
        epochRaw is! num) {
      return null;
    }
    return EpisodeResumeViewData(
      goalRef: goalRef,
      taskRef: taskRef,
      expiresAt: expiresAt,
      computedAt: computedAt,
      memoryEpochAtCompute: epochRaw.toInt(),
      contextReceiptRef: receiptRef,
      runRef: _nullableString(payload['run_ref']),
      lastOutcome: _parseOutcome(payload['last_valid_outcome']),
      lastConfirmedStep: _parseStep(payload['last_confirmed_step']),
      pendingHumanStep: _parsePending(payload['pending_human_step']),
      whyNowStatement: _parseWhyNow(payload['why_now']),
      whyNowConfidenceBand: _whyBandOf(payload['why_now']),
    );
  }

  static String? _nullableString(Object? raw) {
    final value = raw?.toString() ?? '';
    return value.isEmpty ? null : value;
  }

  /// 子结构词表越界 → null（字段级降级，不连坐）。
  static ResumeOutcomeView? _parseOutcome(Object? raw) {
    if (raw == null) {
      return null;
    }
    if (raw is! Map) {
      return null;
    }
    final map = Map<String, dynamic>.from(raw);
    final outcomeRef = map['outcome_ref']?.toString() ?? '';
    final truthClass = map['truth_class']?.toString() ?? '';
    if (_refSchemeOf(outcomeRef) != 'outcome' ||
        !kResumeTruthClassValues.contains(truthClass)) {
      return null;
    }
    return ResumeOutcomeView(
      outcomeRef: outcomeRef,
      truthClass: truthClass,
      recordedAt: _parseIso(map['recorded_at']),
    );
  }

  static ResumeStepView? _parseStep(Object? raw) {
    if (raw == null) {
      return null;
    }
    if (raw is! Map) {
      return null;
    }
    final map = Map<String, dynamic>.from(raw);
    final stepRef = map['step_ref']?.toString() ?? '';
    final description = map['description']?.toString() ?? '';
    final scheme = _refSchemeOf(stepRef);
    if (!kResumeStepRefSchemes.contains(scheme) ||
        stepRef.substring('${scheme ?? ''}://'.length).isEmpty ||
        description.isEmpty) {
      return null;
    }
    return ResumeStepView(
      stepRef: stepRef,
      description: description,
      confirmedAt: _parseIso(map['confirmed_at']),
      versionToken: _nullableString(map['version_token']),
    );
  }

  static ResumePendingStepView? _parsePending(Object? raw) {
    if (raw == null) {
      return null;
    }
    if (raw is! Map) {
      return null;
    }
    final map = Map<String, dynamic>.from(raw);
    final description = map['description']?.toString() ?? '';
    if (description.isEmpty) {
      return null;
    }
    return ResumePendingStepView(
      description: description,
      cognitiveOwnership: _nullableString(map['cognitive_ownership']),
      executionMode: _nullableString(map['execution_mode']),
    );
  }

  static String? _parseWhyNow(Object? raw) {
    if (raw is! Map) {
      return null;
    }
    final statement = Map<String, dynamic>.from(raw)['statement']?.toString() ?? '';
    return statement.isEmpty ? null : statement;
  }

  static String? _whyBandOf(Object? raw) {
    if (raw is! Map) {
      return null;
    }
    final band = Map<String, dynamic>.from(raw)['confidence_band']?.toString() ?? '';
    const bands = <String>{'high', 'medium', 'low', 'unknown'};
    return bands.contains(band) ? band : null;
  }
}

/// 上次有效结果投影（truth_class 为封闭五值成员；recorded_at 可 null）。
class ResumeOutcomeView {
  const ResumeOutcomeView({
    required this.outcomeRef,
    required this.truthClass,
    required this.recordedAt,
  });

  final String outcomeRef;
  final String truthClass;
  final DateTime? recordedAt;
}

/// 上次确认步骤投影（step_ref scheme ∈ {task, subtask}）。
class ResumeStepView {
  const ResumeStepView({
    required this.stepRef,
    required this.description,
    required this.confirmedAt,
    required this.versionToken,
  });

  final String stepRef;
  final String description;
  final DateTime? confirmedAt;

  /// X-03 action_command.version_token 透传（present → 并发校验由执行面既有链路承担）。
  final String? versionToken;
}

/// 待人类步骤投影（X-01 CognitiveOwnership / ExecutionMode 原样透传）。
class ResumePendingStepView {
  const ResumePendingStepView({
    required this.description,
    required this.cognitiveOwnership,
    required this.executionMode,
  });

  final String description;
  final String? cognitiveOwnership;
  final String? executionMode;
}

/// 过期/陈旧判定：backend `resume_view_stale_reason` 的客户端可判定子集。
///
/// 返回 null = 仍新鲜；`"expires_at_passed"` = 视图过期——消费方只允许呈现
/// 不确定性说明，不得静默接续（I01 §5 + B05 §9 反例钉死）。
/// `memory_epoch_changed` 分支需当前 epoch 权威，移动端读侧无此真源，不判
/// （limitation 已披露；权威出口是 I01 按需重算）。
String? episodeResumeStaleReason(
  EpisodeResumeViewData view, {
  required DateTime now,
}) {
  if (!now.isBefore(view.expiresAt)) {
    return 'expires_at_passed';
  }
  return null;
}
