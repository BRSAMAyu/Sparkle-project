class GalaxyNodeErrorItem {
  const GalaxyNodeErrorItem({
    required this.id,
    this.questionText,
    this.questionImageUrl,
    this.subjectCode,
    this.chapter,
    this.masteryLevel = 0,
    this.reviewCount = 0,
    this.analysisSummary,
    this.createdAt,
    this.lastReviewedAt,
  });

  factory GalaxyNodeErrorItem.fromJson(Map<String, dynamic> json) =>
      GalaxyNodeErrorItem(
        id: json['id']?.toString() ?? '',
        questionText: json['question_text']?.toString(),
        questionImageUrl: json['question_image_url']?.toString(),
        subjectCode: json['subject_code']?.toString(),
        chapter: json['chapter']?.toString(),
        masteryLevel: (json['mastery_level'] as num?)?.toDouble() ?? 0,
        reviewCount: (json['review_count'] as num?)?.toInt() ?? 0,
        analysisSummary: json['analysis_summary']?.toString(),
        createdAt: DateTime.tryParse(json['created_at']?.toString() ?? ''),
        lastReviewedAt:
            DateTime.tryParse(json['last_reviewed_at']?.toString() ?? ''),
      );

  final String id;
  final String? questionText;
  final String? questionImageUrl;
  final String? subjectCode;
  final String? chapter;
  final double masteryLevel;
  final int reviewCount;
  final String? analysisSummary;
  final DateTime? createdAt;
  final DateTime? lastReviewedAt;
}

class GalaxyNodeHistory {
  const GalaxyNodeHistory({
    required this.nodeId,
    required this.nodeLabel,
    required this.mastery,
    required this.studyCount,
    this.resolvedNodeId,
    this.lastStudiedAt,
    this.relatedErrors = const [],
  });

  factory GalaxyNodeHistory.fromJson(Map<String, dynamic> json) {
    final rawMastery = (json['mastery'] as num?)?.toDouble() ?? 0;
    final normalizedMastery = rawMastery > 1 ? rawMastery / 100 : rawMastery;
    return GalaxyNodeHistory(
      nodeId: json['node_id']?.toString() ?? '',
      resolvedNodeId: json['resolved_node_id']?.toString(),
      nodeLabel: json['node_label']?.toString() ??
          json['label']?.toString() ??
          json['node_id']?.toString() ??
          '',
      mastery: normalizedMastery.clamp(0.0, 1.0).toDouble(),
      lastStudiedAt:
          DateTime.tryParse(json['last_studied_at']?.toString() ?? ''),
      studyCount: (json['study_count'] as num?)?.toInt() ?? 0,
      relatedErrors: (json['related_errors'] as List<dynamic>? ?? const [])
          .whereType<Map>()
          .map((item) => GalaxyNodeErrorItem.fromJson(
                Map<String, dynamic>.from(item),
              ))
          .toList(growable: false),
    );
  }

  final String nodeId;
  final String? resolvedNodeId;
  final String nodeLabel;
  final double mastery;
  final DateTime? lastStudiedAt;
  final int studyCount;
  final List<GalaxyNodeErrorItem> relatedErrors;

  bool get hasStudied => mastery > 0 || studyCount > 0;
  int get masteryPercent => (mastery * 100).round().clamp(0, 100);
}
