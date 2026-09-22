/// D-COMM-5：小队错题卡分享（`/community/squads/{id}/shared-errors`）模型。
///
/// 后端契约（app/schemas/community_shared_errors.py）：
/// - 分享请求体**只有 error_id**——内容一律服务端从 error_records 取，
///   客户端不可伪造、不可选字段；
/// - 响应是服务端白名单投影：题目/科目/知识点/错因/掌握度快照——
///   **不含** correct_answer / user_answer / 解题思路（备考互助≠抄答案），
///   本模型因此不建模任何答案字段，展示层不渲染不存在的字段；
/// - 分享幂等：同错题已在册则原样返回既有分享（201 语义）。
/// 手写 fromJson（只读视图契约，不进 build_runner）。
class SharedKnowledgeNode {
  const SharedKnowledgeNode({
    required this.id,
    required this.name,
    this.isPrimary = false,
  });

  factory SharedKnowledgeNode.fromJson(Map<String, dynamic> json) =>
      SharedKnowledgeNode(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        isPrimary: json['is_primary'] == true,
      );

  final String id;
  final String name;
  final bool isPrimary;
}

class SharedErrorEntry {
  const SharedErrorEntry({
    required this.shareId,
    required this.sharerId,
    required this.errorId,
    required this.subjectCode,
    required this.masteryLevel,
    required this.reviewCount,
    required this.createdAt,
    this.sharerName,
    this.questionText,
    this.chapter,
    this.knowledgeNodes = const [],
    this.errorType,
    this.rootCause,
    this.note,
    this.masteryDelta,
  });

  factory SharedErrorEntry.fromJson(Map<String, dynamic> json) {
    final nodes = (json['knowledge_nodes'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(SharedKnowledgeNode.fromJson)
        .toList();
    return SharedErrorEntry(
      shareId: json['share_id'] as String? ?? '',
      sharerId: json['sharer_id'] as String? ?? '',
      sharerName: json['sharer_name'] as String?,
      errorId: json['error_id'] as String? ?? '',
      questionText: json['question_text'] as String?,
      subjectCode: json['subject_code'] as String? ?? '',
      chapter: json['chapter'] as String?,
      knowledgeNodes: nodes,
      errorType: json['error_type'] as String?,
      rootCause: json['root_cause'] as String?,
      note: json['note'] as String?,
      masteryLevel: (json['mastery_level'] as num?)?.toDouble() ?? 0.0,
      masteryDelta: (json['mastery_delta'] as num?)?.toDouble(),
      reviewCount: (json['review_count'] as num?)?.toInt() ?? 0,
      createdAt: _parseDate(json['created_at']),
    );
  }

  final String shareId;
  final String sharerId;

  /// 分享者昵称或用户名（缺失为 null——互助要可找到人，但模型不造假名）。
  final String? sharerName;
  final String errorId;

  /// 题目文本（可空：图片题等场景为 null——展示层不渲染该行，不造占位）。
  final String? questionText;
  final String subjectCode;
  final String? chapter;
  final List<SharedKnowledgeNode> knowledgeNodes;

  /// 错因分类/根因（服务端快照，诚实呈现卡点；可空不渲染）。
  final String? errorType;
  final String? rootCause;

  /// 分享者附言（可空）。
  final String? note;

  /// 分享时刻掌握度快照 0.0-1.0。
  final double masteryLevel;

  /// 分享时刻掌握度变化（负=诊断扣分；可空不渲染）。
  final double? masteryDelta;
  final int reviewCount;
  final DateTime? createdAt;
}

class SharedErrorList {
  const SharedErrorList({
    required this.squadId,
    required this.total,
    required this.items,
  });

  factory SharedErrorList.fromJson(Map<String, dynamic> json) {
    final items = (json['items'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(SharedErrorEntry.fromJson)
        .toList();
    return SharedErrorList(
      squadId: json['squad_id'] as String? ?? '',
      total: (json['total'] as num?)?.toInt() ?? 0,
      items: items,
    );
  }

  final String squadId;

  /// 在册分享总数（分页在全集上计）。
  final int total;
  final List<SharedErrorEntry> items;
}

DateTime? _parseDate(Object? raw) =>
    raw is String ? DateTime.tryParse(raw)?.toUtc() : null;
