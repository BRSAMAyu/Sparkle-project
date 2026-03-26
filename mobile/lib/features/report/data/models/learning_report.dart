class LearningMasteryDatum {
  const LearningMasteryDatum({
    required this.nodeName,
    required this.masteryScore,
  });

  factory LearningMasteryDatum.fromJson(Map<String, dynamic> json) =>
      LearningMasteryDatum(
        nodeName: json['node_name']?.toString() ?? '',
        masteryScore: (json['mastery_score'] as num?)?.toDouble() ?? 0,
      );

  final String nodeName;
  final double masteryScore;
}

class LearningReport {
  const LearningReport({
    required this.reportId,
    required this.markdown,
    required this.sections,
    required this.mastery,
  });

  factory LearningReport.fromJson(Map<String, dynamic> json) => LearningReport(
        reportId: json['report_id']?.toString() ?? '',
        markdown: json['markdown']?.toString() ?? '',
        sections: (json['sections'] as List<dynamic>? ?? const [])
            .map((e) => e.toString())
            .toList(),
        mastery: (json['mastery'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(LearningMasteryDatum.fromJson)
            .toList(),
      );

  final String reportId;
  final String markdown;
  final List<String> sections;
  final List<LearningMasteryDatum> mastery;
}
