/// V4-U10 · 资料→错题→练习→检验旅程的客户端载荷模型。
///
/// 契约真源 = `backend/app/core/learning_journey.py`（`learning_journey.v2`）。
/// 本文件只做**消费侧解析**，三条构造期红线（与服务端同构，缺一即断言失败）：
///
/// 1. **解析诚实**：[JourneyParseStatus.failed]/[unsupported] 一律不携带文本
///    （伪造解析在数据层不可能存在），必须挂手输替代标记；
/// 2. **来源可见**：[JourneySourceRef] 必有 id + 版本（来源badge 面数据）；
/// 3. **答案隔离**：检验题面经 [LearningCheckQuestion.sanitize] 红化门——
///    检测到任何答案键剥除即降级拒显（服务端契约违约不做半真呈现）。
library;

import 'package:sparkle/features/learning/data/learning_check_redaction.dart';

/// 旅程段（与服务端 JOURNEY_SEGMENTS 同词）。
enum LearningSegment { materials, errors, practice, independentCheck }

LearningSegment learningSegmentFromName(String? name) {
  switch (name) {
    case 'materials':
      return LearningSegment.materials;
    case 'errors':
      return LearningSegment.errors;
    case 'practice':
      return LearningSegment.practice;
    case 'independent_check':
      return LearningSegment.independentCheck;
    default:
      // 保守回落练习段：绝不把未到检验的用户推进检验空页。
      return LearningSegment.practice;
  }
}

/// 材料解析状态（与服务端 PARSE_STATUSES 同词）。
enum JourneyParseStatus { parsed, pending, failed, unsupported, manual }

JourneyParseStatus journeyParseStatusFromName(String? name) {
  switch (name) {
    case 'parsed':
      return JourneyParseStatus.parsed;
    case 'pending':
      return JourneyParseStatus.pending;
    case 'failed':
      return JourneyParseStatus.failed;
    case 'unsupported':
      return JourneyParseStatus.unsupported;
    case 'manual':
      return JourneyParseStatus.manual;
    default:
      return JourneyParseStatus.unsupported; // 未知状态按不支持处理（保守，不宣称已解析）
  }
}

/// 来源引用（来源badge：id + 版本 + 片段锚）。
class JourneySourceRef {
  const JourneySourceRef({
    required this.sourceId,
    required this.sourceVersion,
    this.fragmentAnchor,
    this.sourceKind = 'document',
  });

  factory JourneySourceRef.fromJson(Map<Object?, Object?> json) {
    final id = json['source_id'] as String? ?? '';
    final version = json['source_version'] as String? ?? '';
    assert(
      id.isNotEmpty && version.isNotEmpty,
      '来源引用必须携带 id 与版本（learning_journey.v2 契约）',
    );
    return JourneySourceRef(
      sourceId: id,
      sourceVersion: version,
      fragmentAnchor: json['fragment_anchor'] as String?,
      sourceKind: json['source_kind'] as String? ?? 'document',
    );
  }

  final String sourceId;
  final String sourceVersion;
  final String? fragmentAnchor;
  final String sourceKind;
}

/// 材料解析状态面（无文本键——伪造解析在本结构上不可能）。
class JourneyMaterialParse {
  const JourneyMaterialParse._({
    required this.status,
    required this.manualInputRequired,
    this.reason,
  });

  factory JourneyMaterialParse.fromJson(Map<Object?, Object?> json) {
    final status = journeyParseStatusFromName(json['status'] as String?);
    final manualRequired = json['manual_input_required'] as bool? ?? false;
    assert(
      // 解析诚实红线：失败/不支持的面不带文本、必须挂手输替代。
      !((status == JourneyParseStatus.failed || status == JourneyParseStatus.unsupported) &&
          !manualRequired),
      'failed/unsupported 解析面必须要求手输替代（learning_journey.v2）',
    );
    assert(
      // 面上根本没有 text 键可携带——若出现即契约违约。
      !json.containsKey('text'),
      '材料状态面不得携带文本载荷（learning_journey.v2）',
    );
    return JourneyMaterialParse._(
      status: status,
      manualInputRequired: manualRequired,
      reason: json['reason'] as String?,
    );
  }

  final JourneyParseStatus status;
  final bool manualInputRequired;
  final String? reason;

  bool get needsManualInput =>
      status == JourneyParseStatus.failed || status == JourneyParseStatus.unsupported;
}

/// 旅程材料条目。
class JourneyMaterial {
  const JourneyMaterial({
    required this.fileName,
    required this.mimeType,
    required this.source,
    required this.parse,
  });

  factory JourneyMaterial.fromJson(Map<Object?, Object?> json) => JourneyMaterial(
        fileName: json['file_name'] as String? ?? '',
        mimeType: json['mime_type'] as String? ?? '',
        source: JourneySourceRef.fromJson(json['source'] as Map<Object?, Object?>? ?? const {}),
        parse: JourneyMaterialParse.fromJson(json['parse'] as Map<Object?, Object?>? ?? const {}),
      );

  final String fileName;
  final String mimeType;
  final JourneySourceRef source;
  final JourneyMaterialParse parse;
}

/// 错题简报（最小暴露面：不含 correct_answer / user_answer / 解析）。
class JourneyErrorBrief {
  const JourneyErrorBrief({
    required this.id,
    required this.subjectCode,
    required this.questionText,
    required this.reviewCount,
    required this.source,
    this.chapter,
    this.masteryLevel,
  });

  factory JourneyErrorBrief.fromJson(Map<Object?, Object?> json) => JourneyErrorBrief(
        id: json['id'] as String? ?? '',
        subjectCode: json['subject_code'] as String? ?? '',
        questionText: json['question_text'] as String? ?? '',
        reviewCount: (json['review_count'] as num?)?.toInt() ?? 0,
        chapter: json['chapter'] as String?,
        masteryLevel: (json['mastery_level'] as num?)?.toDouble(),
        source: JourneySourceRef.fromJson(json['source'] as Map<Object?, Object?>? ?? const {}),
      );

  final String id;
  final String subjectCode;
  final String questionText;
  final int reviewCount;
  final String? chapter;
  final double? masteryLevel;
  final JourneySourceRef source;
}

/// 脚手架当前态（I07 链：example → attempt → independent_check）。
class JourneyScaffold {
  const JourneyScaffold({
    required this.stage,
    required this.hintLevel,
    required this.segment,
  });

  factory JourneyScaffold.fromJson(Map<Object?, Object?> json) => JourneyScaffold(
        stage: json['stage'] as String? ?? 'example',
        hintLevel: json['hint_level'] as String? ?? 'full',
        segment: learningSegmentFromName(json['segment'] as String?),
      );

  final String stage;
  final String hintLevel;
  final LearningSegment segment;
}

/// 目标上下文（旅程页头；从目标进入必带）。
class LearningJourneyContext {
  const LearningJourneyContext({required this.goalTaskId, required this.goalTitle});

  final String goalTaskId;
  final String goalTitle;

  /// 入口守卫：从目标跳入旅程必须携带非空上下文（验收1 的机制化——
  /// 空上下文的「目标入口」在起飞前即失败，而不是落地成无上下文空页）。
  static LearningJourneyContext fromLaunch({
    required String? goalTaskId,
    required String? goalTitle,
  }) {
    if (goalTaskId == null || goalTaskId.trim().isEmpty) {
      throw ArgumentError.value(goalTaskId, 'goalTaskId', '目标上下文缺失：不得从目标跳入无上下文工具页');
    }
    if (goalTitle == null || goalTitle.trim().isEmpty) {
      throw ArgumentError.value(goalTitle, 'goalTitle', '目标标题缺失：不得从目标跳入无上下文工具页');
    }
    return LearningJourneyContext(goalTaskId: goalTaskId.trim(), goalTitle: goalTitle.trim());
  }
}

/// 旅程装配视图（GET /learning-journey/tasks/{id} 的 `view`）。
class LearningJourneyView {
  const LearningJourneyView({
    required this.goalTaskId,
    required this.goalTitle,
    required this.scaffold,
    required this.materials,
    required this.errors,
    required this.evidenceSupported,
    required this.degraded,
    this.checkQuestion,
    this.warnings = const <String>[],
  });

  static LearningJourneyView fromJson(
    Map<Object?, Object?> json, {
    List<String> warnings = const <String>[],
  }) {
    final goal = json['goal'] as Map<Object?, Object?>? ?? const {};
    final check = json['check'] as Map<Object?, Object?>?;
    return LearningJourneyView(
      goalTaskId: goal['task_id'] as String? ?? '',
      goalTitle: goal['title'] as String? ?? '',
      scaffold: JourneyScaffold.fromJson(json['scaffold'] as Map<Object?, Object?>? ?? const {}),
      materials: ((json['materials'] as List<Object?>?) ?? const [])
          .whereType<Map<Object?, Object?>>()
          .map(JourneyMaterial.fromJson)
          .toList(growable: false),
      errors: ((json['errors'] as List<Object?>?) ?? const [])
          .whereType<Map<Object?, Object?>>()
          .map(JourneyErrorBrief.fromJson)
          .toList(growable: false),
      evidenceSupported:
          (json['practice'] as Map<Object?, Object?>?)?['evidence_supported'] as bool? ?? false,
      checkQuestion: check?['question'] as String?,
      degraded: false,
      warnings: warnings,
    );
  }

  final String goalTaskId;
  final String goalTitle;
  final JourneyScaffold scaffold;
  final List<JourneyMaterial> materials;
  final List<JourneyErrorBrief> errors;
  final bool evidenceSupported;
  final bool degraded;
  final String? checkQuestion;
  final List<String> warnings;
}

/// 检验题面（红化门后的可读面）。
class LearningCheckQuestion {
  const LearningCheckQuestion._({required this.question, required this.degraded});

  final String question;

  /// true = 服务端载荷检出答案材料（契约违约）——题面拒显，走降级文案。
  final bool degraded;

  /// 红化门入口：载荷先过 [redactIndependentCheck]，检出剥除即降级拒显
  /// （不把半红化载荷投递给用户可读状态）。
  static LearningCheckQuestion sanitize(Object? payload) {
    final (Object? clean, List<String> removed) = redactIndependentCheck(payload);
    if (removed.isNotEmpty) {
      return const LearningCheckQuestion._(question: '', degraded: true);
    }
    final Object? question = clean is Map ? clean['question'] : null;
    return LearningCheckQuestion._(
      question: question is String ? question : '',
      degraded: false,
    );
  }
}

/// 判分面允许的契约字段（learning_journey.v2；`correct` = bool 裁决字段，
/// 与 I07 答案键集同名不同面——嵌套面另过红化门探针）。
///
/// 口径如实（R1 N-6）：下方允许表 / `correct is bool` 校验均为 `assert`——
/// debug/test 生效、**release 跳过**。release 下的真实防线 = 服务端出口探针
/// （权威门）+ 本类运行时兜底（`correct is bool ? correct : null` 三元；
/// 契约外键无任何渲染路径）；[LearningCheckQuestion.sanitize] 是运行时红化
/// 逻辑，不受 assert 影响。
const Set<String> _allowedVerdictKeys = <String>{
  'schema_version',
  'graded',
  'correct',
  'reason',
  'feedback',
};

/// 检验判分结果（客户端可见面 = 零答案材料）。
class LearningCheckVerdict {
  const LearningCheckVerdict({
    required this.graded,
    required this.correct,
    required this.reason,
    this.feedback,
  });

  static LearningCheckVerdict fromJson(Map<Object?, Object?> json) {
    assert(
      // 允许表校验（比键黑名单更严）：判分面只允许契约字段出现——任何额外键
      // （如 `answer`）即契约违约。assert 仅 debug/test 生效（R1 N-6）；
      // release 由运行时兜底 + 服务端出口探针承担。嵌套标记节点另过红化门探针。
      json.keys.every(_allowedVerdictKeys.contains),
      '检验判分面携带契约外字段（learning_journey.v2 契约违约）',
    );
    assert(
      !containsIndependentCheckAnswer(json),
      '检验判分面泄漏答案材料（learning_journey.v2 契约违约）',
    );
    final correct = json['correct'];
    assert(
      correct == null || correct is bool,
      '判分面 correct 必须是 bool 裁决（不得借位携带答案材料）',
    );
    return LearningCheckVerdict(
      graded: json['graded'] as bool? ?? false,
      correct: correct is bool ? correct : null,
      reason: json['reason'] as String? ?? '',
      feedback: json['feedback'] as String?,
    );
  }

  final bool graded;
  final bool? correct;
  final String reason;
  final String? feedback;
}
