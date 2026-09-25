// J-05 ·「我卡住了」统一恢复旅程的数据模型。
//
// 全部字段容错解析（后端缺席字段 → 缺省，不抛）：旅程面是派生视图，
// 后端载荷形状演进时旧客户端保持可渲染。零 mock fallback——解析失败
// 的顶层载荷按错误态呈现，不伪造数据。

/// 旅程入口请求（三面差异化 context 的载体）。
class StuckJourneyRequest {
  const StuckJourneyRequest({
    required this.surface,
    this.goalId,
    this.taskId,
  });

  final String surface;
  final String? goalId;
  final String? taskId;

  @override
  bool operator ==(Object other) =>
      other is StuckJourneyRequest &&
      other.surface == surface &&
      other.goalId == goalId &&
      other.taskId == taskId;

  @override
  int get hashCode => Object.hash(surface, goalId, taskId);
}

/// 单问的分支选项（branch_key 直传主路径）。
class StuckJourneyBranchOption {
  const StuckJourneyBranchOption({
    required this.key,
    required this.label,
  });

  factory StuckJourneyBranchOption.fromJson(Map<String, dynamic> json) =>
      StuckJourneyBranchOption(
        key: (json['key'] ?? '').toString(),
        label: (json['label'] ?? '').toString(),
      );

  final String key;
  final String label;
}

/// ≤1 个高价值问题（context 驱动选择；载荷缺 question = 直接出判断）。
class StuckJourneyQuestion {
  const StuckJourneyQuestion({
    required this.id,
    required this.text,
    required this.options,
  });


  /// 缺席语义用可空静态解析（factory 构造器不能返回 null）。
  static StuckJourneyQuestion? fromJson(Map<String, dynamic>? json) {
    if (json == null || json.isEmpty) return null;
    final id = (json['question_id'] ?? '').toString();
    if (id.isEmpty) return null;
    final rawOptions = (json['branch_options'] as List?) ?? const <dynamic>[];
    return StuckJourneyQuestion(
      id: id,
      text: (json['text'] ?? '').toString(),
      options: rawOptions
          .whereType<Map<dynamic, dynamic>>()
          .map(
            (item) => StuckJourneyBranchOption.fromJson(
              Map<String, dynamic>.from(item),
            ),
          )
          .toList(growable: false),
    );
  }

  final String id;
  final String text;
  final List<StuckJourneyBranchOption> options;
}

/// 主 intervention（A-01 目录键 + 提名序；展示文案在 l10n 层映射）。
class StuckJourneyIntervention {
  const StuckJourneyIntervention({
    required this.type,
    required this.frictionType,
    required this.uncertain,
    required this.adjustedByCorrection,
  });

  /// 缺席语义用可空静态解析（factory 构造器不能返回 null）。
  static StuckJourneyIntervention? fromJson(Map<String, dynamic>? json) {
    if (json == null || json.isEmpty) return null;
    final type = (json['type'] ?? '').toString();
    if (type.isEmpty) return null;
    return StuckJourneyIntervention(
      type: type,
      frictionType: (json['friction_type'] ?? '').toString(),
      uncertain: json['uncertain'] == true,
      adjustedByCorrection: json['adjusted_by_correction'] == true,
    );
  }

  final String type;
  final String frictionType;
  final bool uncertain;
  final bool adjustedByCorrection;
}

/// 真实 context 投影（Goal/Task 行原样 + 近期失败计数）。
class StuckJourneyContextData {
  const StuckJourneyContextData({
    this.goalTitle,
    this.taskTitle,
    this.recentFailureCount = 0,
    this.daysSinceProgress,
  });

  factory StuckJourneyContextData.fromJson(Map<String, dynamic>? json) {
    if (json == null) return const StuckJourneyContextData();
    final goal = json['goal'];
    final task = json['task'];
    final failures = json['recent_failures'];
    final days = json['days_since_progress'];
    String? goalTitle;
    if (goal is Map) {
      final value = (goal['title'] ?? '').toString();
      goalTitle = value.isEmpty ? null : value;
    }
    String? taskTitle;
    if (task is Map) {
      final value = (task['title'] ?? '').toString();
      taskTitle = value.isEmpty ? null : value;
    }
    return StuckJourneyContextData(
      goalTitle: goalTitle,
      taskTitle: taskTitle,
      recentFailureCount:
          failures is Map ? (failures['count'] as num?)?.toInt() ?? 0 : 0,
      daysSinceProgress: days is num ? days.toInt() : null,
    );
  }

  final String? goalTitle;
  final String? taskTitle;
  final int recentFailureCount;
  final int? daysSinceProgress;
}

/// 一次旅程派生输出（start/answer/correct 共用）。
class StuckJourneyPayload {
  const StuckJourneyPayload({
    required this.surface,
    required this.outcome,
    required this.frictionType,
    required this.context,
    this.question,
    this.mainIntervention,
    this.uncertain = false,
    this.correctionActive = false,
    this.correctedThisTurn = false,
  });

  factory StuckJourneyPayload.fromJson(Map<String, dynamic> json) {
    final receipt = json['receipt'];
    final annotations = json['annotations'];
    return StuckJourneyPayload(
      surface: (json['surface'] ?? '').toString(),
      outcome: (json['outcome'] ?? '').toString(),
      frictionType: (json['friction_type'] ?? '').toString(),
      context: StuckJourneyContextData.fromJson(
        json['context'] is Map
            ? Map<String, dynamic>.from(json['context'] as Map)
            : null,
      ),
      question: StuckJourneyQuestion.fromJson(
        json['question'] is Map
            ? Map<String, dynamic>.from(json['question'] as Map)
            : null,
      ),
      mainIntervention: StuckJourneyIntervention.fromJson(
        json['main_intervention'] is Map
            ? Map<String, dynamic>.from(json['main_intervention'] as Map)
            : null,
      ),
      uncertain: json['uncertain'] == true,
      correctionActive: receipt is Map && receipt['correction_active'] == true,
      correctedThisTurn:
          annotations is Map && annotations['corrected_this_turn'] == true,
    );
  }

  final String surface;
  final String outcome;
  final String frictionType;
  final StuckJourneyContextData context;
  final StuckJourneyQuestion? question;
  final StuckJourneyIntervention? mainIntervention;
  final bool uncertain;
  final bool correctionActive;
  final bool correctedThisTurn;
}

/// 纠正回执（correct 响应；journey = 按纠正重派生的输出）。
class StuckJourneyCorrectionResult {
  const StuckJourneyCorrectionResult({required this.journey});

  factory StuckJourneyCorrectionResult.fromJson(Map<String, dynamic> json) =>
      StuckJourneyCorrectionResult(
        journey: StuckJourneyPayload.fromJson(
          json['journey'] is Map
              ? Map<String, dynamic>.from(json['journey'] as Map)
              : const <String, dynamic>{},
        ),
      );

  final StuckJourneyPayload journey;
}
