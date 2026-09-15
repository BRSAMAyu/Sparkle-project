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

  Map<String, dynamic> toJson() => <String, dynamic>{
        'node_name': nodeName,
        'mastery_score': masteryScore,
      };
}

class LearningPatternDatum {
  const LearningPatternDatum({
    required this.patternName,
    this.description,
    this.solutionText,
    this.confidence,
  });

  factory LearningPatternDatum.fromJson(Map<String, dynamic> json) =>
      LearningPatternDatum(
        patternName: json['pattern_name']?.toString() ?? '',
        description: json['description']?.toString(),
        solutionText: json['solution_text']?.toString(),
        confidence: (json['confidence'] as num?)?.toDouble(),
      );

  final String patternName;
  final String? description;
  final String? solutionText;
  final double? confidence;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'pattern_name': patternName,
        if (description != null) 'description': description,
        if (solutionText != null) 'solution_text': solutionText,
        if (confidence != null) 'confidence': confidence,
      };
}

class LearningTimelineDatum {
  const LearningTimelineDatum({
    required this.nodeName,
    this.studyMinutes = 0,
    this.masteryDelta,
    this.createdAt,
  });

  factory LearningTimelineDatum.fromJson(Map<String, dynamic> json) =>
      LearningTimelineDatum(
        nodeName: json['node_name']?.toString() ?? '',
        studyMinutes: (json['study_minutes'] as num?)?.toInt() ??
            (json['minutes'] as num?)?.toInt() ??
            0,
        masteryDelta: (json['mastery_delta'] as num?)?.toDouble(),
        createdAt: json['created_at']?.toString(),
      );

  final String nodeName;
  final int studyMinutes;
  final double? masteryDelta;
  final String? createdAt;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'node_name': nodeName,
        'study_minutes': studyMinutes,
        if (masteryDelta != null) 'mastery_delta': masteryDelta,
        if (createdAt != null) 'created_at': createdAt,
      };
}

class LearningReportDiagnosticCard {
  const LearningReportDiagnosticCard({
    required this.id,
    required this.title,
    required this.headline,
    required this.summary,
    this.evidence = const <String>[],
    this.severity = 'info',
    this.ctaLabel,
    this.deepLink,
    this.tag,
  });

  factory LearningReportDiagnosticCard.fromJson(Map<String, dynamic> json) =>
      LearningReportDiagnosticCard(
        id: json['id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        headline: json['headline']?.toString() ?? '',
        summary: json['summary']?.toString() ?? '',
        evidence: (json['evidence'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        severity: json['severity']?.toString() ?? 'info',
        ctaLabel: json['cta_label']?.toString(),
        deepLink: json['deep_link']?.toString(),
        tag: json['tag']?.toString(),
      );

  final String id;
  final String title;
  final String headline;
  final String summary;
  final List<String> evidence;
  final String severity;
  final String? ctaLabel;
  final String? deepLink;
  final String? tag;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'title': title,
        'headline': headline,
        'summary': summary,
        'evidence': evidence,
        'severity': severity,
        if (ctaLabel != null) 'cta_label': ctaLabel,
        if (deepLink != null) 'deep_link': deepLink,
        if (tag != null) 'tag': tag,
      };
}

class LearningReportActionCard {
  const LearningReportActionCard({
    required this.id,
    required this.title,
    required this.summary,
    required this.ctaLabel,
    required this.deepLink,
    this.kind = 'generic',
    this.priority = 'medium',
    this.badge,
  });

  factory LearningReportActionCard.fromJson(Map<String, dynamic> json) =>
      LearningReportActionCard(
        id: json['id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        summary: json['summary']?.toString() ?? '',
        ctaLabel: json['cta_label']?.toString() ?? '',
        deepLink: json['deep_link']?.toString() ?? '',
        kind: json['kind']?.toString() ?? 'generic',
        priority: json['priority']?.toString() ?? 'medium',
        badge: json['badge']?.toString(),
      );

  final String id;
  final String title;
  final String summary;
  final String ctaLabel;
  final String deepLink;
  final String kind;
  final String priority;
  final String? badge;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'id': id,
        'title': title,
        'summary': summary,
        'cta_label': ctaLabel,
        'deep_link': deepLink,
        'kind': kind,
        'priority': priority,
        if (badge != null) 'badge': badge,
      };
}

class LearningTrendPoint {
  const LearningTrendPoint({
    required this.label,
    required this.averageMastery,
    this.studyMinutes = 0,
    this.masteryDelta = 0,
  });

  factory LearningTrendPoint.fromJson(Map<String, dynamic> json) =>
      LearningTrendPoint(
        label: json['label']?.toString() ?? '',
        averageMastery: (json['average_mastery'] as num?)?.toDouble() ?? 0,
        studyMinutes: (json['study_minutes'] as num?)?.toInt() ?? 0,
        masteryDelta: (json['mastery_delta'] as num?)?.toDouble() ?? 0,
      );

  final String label;
  final double averageMastery;
  final int studyMinutes;
  final double masteryDelta;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'label': label,
        'average_mastery': averageMastery,
        'study_minutes': studyMinutes,
        'mastery_delta': masteryDelta,
      };
}

class LearningTrendComparison {
  const LearningTrendComparison({
    required this.label,
    required this.summary,
    this.deltaMastery = 0,
    this.deltaStudyMinutes = 0,
    this.direction = 'flat',
  });

  factory LearningTrendComparison.fromJson(Map<String, dynamic> json) =>
      LearningTrendComparison(
        label: json['label']?.toString() ?? '',
        summary: json['summary']?.toString() ?? '',
        deltaMastery: (json['delta_mastery'] as num?)?.toDouble() ?? 0,
        deltaStudyMinutes: (json['delta_study_minutes'] as num?)?.toInt() ?? 0,
        direction: json['direction']?.toString() ?? 'flat',
      );

  final String label;
  final String summary;
  final double deltaMastery;
  final int deltaStudyMinutes;
  final String direction;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'label': label,
        'summary': summary,
        'delta_mastery': deltaMastery,
        'delta_study_minutes': deltaStudyMinutes,
        'direction': direction,
      };
}

class LearningReportTrendOverview {
  const LearningReportTrendOverview({
    required this.headline,
    required this.summary,
    this.status = 'ready',
    this.message,
    this.historyPoints = const <LearningTrendPoint>[],
    this.comparisons = const <LearningTrendComparison>[],
  });

  factory LearningReportTrendOverview.fromJson(Map<String, dynamic> json) =>
      LearningReportTrendOverview(
        status: json['status']?.toString() ?? 'ready',
        message: json['message']?.toString(),
        headline: json['headline']?.toString() ?? '',
        summary: json['summary']?.toString() ?? '',
        historyPoints: (json['history_points'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(LearningTrendPoint.fromJson)
            .toList(),
        comparisons: (json['comparisons'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(LearningTrendComparison.fromJson)
            .toList(),
      );

  final String status;
  final String? message;
  final String headline;
  final String summary;
  final List<LearningTrendPoint> historyPoints;
  final List<LearningTrendComparison> comparisons;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'status': status,
        if (message != null) 'message': message,
        'headline': headline,
        'summary': summary,
        'history_points': historyPoints.map((item) => item.toJson()).toList(),
        'comparisons': comparisons.map((item) => item.toJson()).toList(),
      };
}

class LearningReportTriggerSummary {
  const LearningReportTriggerSummary({
    required this.mode,
    required this.title,
    required this.summary,
    this.dataStatus,
  });

  factory LearningReportTriggerSummary.fromJson(Map<String, dynamic> json) =>
      LearningReportTriggerSummary(
        mode: json['mode']?.toString() ?? 'manual',
        title: json['title']?.toString() ?? '',
        summary: json['summary']?.toString() ?? '',
        dataStatus: json['data_status']?.toString(),
      );

  final String mode;
  final String title;
  final String summary;
  final String? dataStatus;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'mode': mode,
        'title': title,
        'summary': summary,
        if (dataStatus != null) 'data_status': dataStatus,
      };
}

class LearningReport {
  const LearningReport({
    required this.reportId,
    required this.markdown,
    required this.sections,
    required this.mastery,
    this.patterns = const <LearningPatternDatum>[],
    this.timeline = const <LearningTimelineDatum>[],
    this.diagnosisCards = const <LearningReportDiagnosticCard>[],
    this.actionCards = const <LearningReportActionCard>[],
    this.trendOverview,
    this.triggerSummary,
    this.dataStatus,
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
        patterns: (json['patterns'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(LearningPatternDatum.fromJson)
            .toList(),
        timeline: (json['timeline'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(LearningTimelineDatum.fromJson)
            .toList(),
        diagnosisCards: (json['diagnosis_cards'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(LearningReportDiagnosticCard.fromJson)
            .toList(),
        actionCards: (json['action_cards'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(LearningReportActionCard.fromJson)
            .toList(),
        trendOverview: json['trend_overview'] is Map<String, dynamic>
            ? LearningReportTrendOverview.fromJson(
                json['trend_overview'] as Map<String, dynamic>,
              )
            : null,
        triggerSummary: json['trigger_summary'] is Map<String, dynamic>
            ? LearningReportTriggerSummary.fromJson(
                json['trigger_summary'] as Map<String, dynamic>,
              )
            : null,
        dataStatus: json['trigger_summary'] is Map<String, dynamic>
            ? (json['trigger_summary'] as Map<String, dynamic>)['data_status']
                ?.toString()
            : null,
      );

  final String reportId;
  final String markdown;
  final List<String> sections;
  final List<LearningMasteryDatum> mastery;
  final List<LearningPatternDatum> patterns;
  final List<LearningTimelineDatum> timeline;
  final List<LearningReportDiagnosticCard> diagnosisCards;
  final List<LearningReportActionCard> actionCards;
  final LearningReportTrendOverview? trendOverview;
  final LearningReportTriggerSummary? triggerSummary;
  final String? dataStatus;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'report_id': reportId,
        'markdown': markdown,
        'sections': sections,
        'mastery': mastery.map((item) => item.toJson()).toList(),
        'patterns': patterns.map((item) => item.toJson()).toList(),
        'timeline': timeline.map((item) => item.toJson()).toList(),
        'diagnosis_cards': diagnosisCards.map((item) => item.toJson()).toList(),
        'action_cards': actionCards.map((item) => item.toJson()).toList(),
        if (trendOverview != null) 'trend_overview': trendOverview!.toJson(),
        if (triggerSummary != null) 'trigger_summary': triggerSummary!.toJson(),
        if (dataStatus != null) 'data_status': dataStatus,
      };
}
