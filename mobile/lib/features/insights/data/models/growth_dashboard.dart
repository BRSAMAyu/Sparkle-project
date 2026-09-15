import 'package:sparkle/core/services/i18n_service.dart';

class GrowthDashboard {
  const GrowthDashboard({
    required this.chronicleEntries,
    required this.weeklyNarrative,
    required this.timeDistribution,
    required this.efficiencyMetrics,
    required this.weaknessRadar,
    required this.knowledgeChanges,
    required this.planStability,
    required this.modelUpdates,
  });

  factory GrowthDashboard.fromJson(Map<String, dynamic> json) {
    return GrowthDashboard(
      chronicleEntries: _list(json['chronicle_entries'])
          .map(GrowthChronicleEntry.fromJson)
          .toList(growable: false),
      weeklyNarrative: WeeklyDashboardNarrative.fromJson(
        _map(json['weekly_narrative']),
      ),
      timeDistribution: _list(json['time_distribution'])
          .map(TimeDistributionItem.fromJson)
          .toList(growable: false),
      efficiencyMetrics: EfficiencyMetrics.fromJson(
        _map(json['efficiency_metrics']),
      ),
      weaknessRadar: _list(json['weakness_radar'])
          .map(WeaknessRadarItem.fromJson)
          .toList(growable: false),
      knowledgeChanges: _list(json['knowledge_changes'])
          .map(KnowledgeChangeItem.fromJson)
          .toList(growable: false),
      planStability: PlanStability.fromJson(_map(json['plan_stability'])),
      modelUpdates: _list(json['model_updates'])
          .map(ModelUpdateItem.fromJson)
          .toList(growable: false),
    );
  }

  factory GrowthDashboard.placeholder() {
    final l10n = S;
    return GrowthDashboard(
      chronicleEntries: [
        GrowthChronicleEntry(
          id: 'demo-turning-point',
          entryType: 'turning_point',
          title: l10n.growthPlaceholderTurningPointTitle,
          narrative: l10n.growthPlaceholderTurningPointNarrative,
          evidenceRefs: const ['demo-focus-session', 'demo-task-review'],
          timestamp: DateTime.now().toIso8601String(),
          userStatus: 'pending',
          confidence: 0.74,
        ),
      ],
      weeklyNarrative: WeeklyDashboardNarrative(
        title: l10n.growthPlaceholderWeeklyTitle,
        story: l10n.growthPlaceholderWeeklyStory,
        keyInsights: [
          l10n.growthPlaceholderInsight1,
          l10n.growthPlaceholderInsight2,
        ],
        rejectedInsights: const [],
        nextWeekSuggestion: l10n.growthPlaceholderSuggestion,
      ),
      timeDistribution: const [
        TimeDistributionItem(category: 'LEARNING', hours: 3.5, trend: 'up'),
        TimeDistributionItem(
            category: 'ERROR_FIX', hours: 1.2, trend: 'steady'),
        TimeDistributionItem(
            category: 'REFLECTION', hours: 0.6, trend: 'steady'),
      ],
      efficiencyMetrics: const EfficiencyMetrics(
        tasksCompleted: 8,
        avgCompletionTime: 28,
        onTimeRate: 0.82,
      ),
      weaknessRadar: const [
        WeaknessRadarItem(
            area: 'Algebra', currentScore: 0.42, targetScore: 0.78, gap: 0.36),
        WeaknessRadarItem(
            area: 'Reading', currentScore: 0.58, targetScore: 0.78, gap: 0.2),
        WeaknessRadarItem(
            area: 'Review', currentScore: 0.63, targetScore: 0.78, gap: 0.15),
      ],
      knowledgeChanges: const [
        KnowledgeChangeItem(
          nodeLabel: 'Quadratic equations',
          masteryBefore: 0.48,
          masteryAfter: 0.61,
          reason: 'task_complete',
        ),
      ],
      planStability: const PlanStability(
        interruptions: 2,
        adjustments: 3,
        abandonmentRate: 0.08,
      ),
      modelUpdates: [
        ModelUpdateItem(
          triggerEvent: l10n.growthPlaceholderTriggerEvent,
          whatSparkleLearned: l10n.growthPlaceholderLearned,
          whatChanged: l10n.growthPlaceholderChanged,
          whatWasNotWritten: l10n.growthPlaceholderNotWritten,
        ),
      ],
    );
  }

  final List<GrowthChronicleEntry> chronicleEntries;
  final WeeklyDashboardNarrative weeklyNarrative;
  final List<TimeDistributionItem> timeDistribution;
  final EfficiencyMetrics efficiencyMetrics;
  final List<WeaknessRadarItem> weaknessRadar;
  final List<KnowledgeChangeItem> knowledgeChanges;
  final PlanStability planStability;
  final List<ModelUpdateItem> modelUpdates;

  GrowthDashboard updateEntryStatus(String entryId, String status) {
    return GrowthDashboard(
      chronicleEntries: chronicleEntries
          .map(
            (entry) => entry.id == entryId
                ? entry.copyWith(userStatus: status)
                : entry,
          )
          .toList(growable: false),
      weeklyNarrative: weeklyNarrative,
      timeDistribution: timeDistribution,
      efficiencyMetrics: efficiencyMetrics,
      weaknessRadar: weaknessRadar,
      knowledgeChanges: knowledgeChanges,
      planStability: planStability,
      modelUpdates: modelUpdates,
    );
  }
}

class GrowthChronicleEntry {
  const GrowthChronicleEntry({
    required this.id,
    required this.entryType,
    required this.title,
    required this.narrative,
    required this.evidenceRefs,
    required this.timestamp,
    required this.userStatus,
    required this.confidence,
  });

  factory GrowthChronicleEntry.fromJson(Map<String, dynamic> json) {
    return GrowthChronicleEntry(
      id: json['entry_id']?.toString() ?? json['id']?.toString() ?? '',
      entryType: json['entry_type']?.toString() ?? 'milestone',
      title: json['title']?.toString() ?? '',
      narrative: json['narrative']?.toString() ?? '',
      evidenceRefs: _strings(json['evidence_refs']),
      timestamp: json['timestamp']?.toString() ?? '',
      userStatus: json['user_status']?.toString() ?? 'pending',
      confidence: _double(json['confidence'], fallback: 0.5),
    );
  }

  final String id;
  final String entryType;
  final String title;
  final String narrative;
  final List<String> evidenceRefs;
  final String timestamp;
  final String userStatus;
  final double confidence;

  GrowthChronicleEntry copyWith({String? userStatus, String? narrative}) {
    return GrowthChronicleEntry(
      id: id,
      entryType: entryType,
      title: title,
      narrative: narrative ?? this.narrative,
      evidenceRefs: evidenceRefs,
      timestamp: timestamp,
      userStatus: userStatus ?? this.userStatus,
      confidence: confidence,
    );
  }
}

class WeeklyDashboardNarrative {
  const WeeklyDashboardNarrative({
    required this.title,
    required this.story,
    required this.keyInsights,
    required this.rejectedInsights,
    required this.nextWeekSuggestion,
  });

  factory WeeklyDashboardNarrative.fromJson(Map<String, dynamic> json) {
    // The backend may return either the story-wrapped format
    // (title, story, key_insights) or the raw format (period, body,
    // highlights).  Map both so the card always renders useful content.
    final title = json['title']?.toString().trim();
    final story = json['story']?.toString().trim();
    final keyInsights = _strings(json['key_insights']);
    final nextWeekSuggestion =
        json['next_week_suggestion']?.toString().trim() ?? '';

    final hasStory = (title?.isNotEmpty ?? false) ||
        (story?.isNotEmpty ?? false) ||
        keyInsights.isNotEmpty;

    if (hasStory) {
      return WeeklyDashboardNarrative(
        title: title ?? '',
        story: story ?? '',
        keyInsights: keyInsights,
        rejectedInsights: _strings(json['rejected_insights']),
        nextWeekSuggestion: nextWeekSuggestion,
      );
    }

    // Raw format from ProgressNarrativeService.to_dict().
    final period = json['period']?.toString().trim() ?? '';
    final body = json['body']?.toString().trim() ?? '';
    final highlights = _strings(json['highlights']);
    final sentences = _strings(json['sentences']);

    return WeeklyDashboardNarrative(
      title: period,
      story: body,
      keyInsights: highlights.isNotEmpty ? highlights : sentences,
      rejectedInsights: const [],
      nextWeekSuggestion: nextWeekSuggestion,
    );
  }

  final String title;
  final String story;
  final List<String> keyInsights;
  final List<String> rejectedInsights;
  final String nextWeekSuggestion;
}

class TimeDistributionItem {
  const TimeDistributionItem({
    required this.category,
    required this.hours,
    required this.trend,
  });

  factory TimeDistributionItem.fromJson(Map<String, dynamic> json) {
    return TimeDistributionItem(
      category: json['category']?.toString() ?? '',
      hours: _double(json['hours']),
      trend: json['trend']?.toString() ?? 'steady',
    );
  }

  final String category;
  final double hours;
  final String trend;
}

class EfficiencyMetrics {
  const EfficiencyMetrics({
    required this.tasksCompleted,
    required this.avgCompletionTime,
    required this.onTimeRate,
  });

  factory EfficiencyMetrics.fromJson(Map<String, dynamic> json) {
    return EfficiencyMetrics(
      tasksCompleted: _int(json['tasks_completed']),
      avgCompletionTime: _double(json['avg_completion_time']),
      onTimeRate: _double(json['on_time_rate']),
    );
  }

  final int tasksCompleted;
  final double avgCompletionTime;
  final double onTimeRate;
}

class WeaknessRadarItem {
  const WeaknessRadarItem({
    required this.area,
    required this.currentScore,
    required this.targetScore,
    required this.gap,
  });

  factory WeaknessRadarItem.fromJson(Map<String, dynamic> json) {
    return WeaknessRadarItem(
      area: json['area']?.toString() ?? '',
      currentScore: _double(json['current_score']),
      targetScore: _double(json['target_score']),
      gap: _double(json['gap']),
    );
  }

  final String area;
  final double currentScore;
  final double targetScore;
  final double gap;
}

class KnowledgeChangeItem {
  const KnowledgeChangeItem({
    required this.nodeLabel,
    required this.masteryBefore,
    required this.masteryAfter,
    required this.reason,
  });

  factory KnowledgeChangeItem.fromJson(Map<String, dynamic> json) {
    return KnowledgeChangeItem(
      nodeLabel: json['node_label']?.toString() ?? '',
      masteryBefore: _double(json['mastery_before']),
      masteryAfter: _double(json['mastery_after']),
      reason: json['reason']?.toString() ?? '',
    );
  }

  final String nodeLabel;
  final double masteryBefore;
  final double masteryAfter;
  final String reason;
}

class PlanStability {
  const PlanStability({
    required this.interruptions,
    required this.adjustments,
    required this.abandonmentRate,
  });

  factory PlanStability.fromJson(Map<String, dynamic> json) {
    return PlanStability(
      interruptions: _int(json['interruptions']),
      adjustments: _int(json['adjustments']),
      abandonmentRate: _double(json['abandonment_rate']),
    );
  }

  final int interruptions;
  final int adjustments;
  final double abandonmentRate;
}

class ModelUpdateItem {
  const ModelUpdateItem({
    required this.triggerEvent,
    required this.whatSparkleLearned,
    required this.whatChanged,
    required this.whatWasNotWritten,
  });

  factory ModelUpdateItem.fromJson(Map<String, dynamic> json) {
    return ModelUpdateItem(
      triggerEvent: json['trigger_event']?.toString() ?? '',
      whatSparkleLearned: json['what_sparkle_learned']?.toString() ?? '',
      whatChanged: json['what_changed']?.toString() ?? '',
      whatWasNotWritten: json['what_was_not_written']?.toString() ?? '',
    );
  }

  final String triggerEvent;
  final String whatSparkleLearned;
  final String whatChanged;
  final String whatWasNotWritten;
}

List<Map<String, dynamic>> _list(dynamic value) {
  if (value is! List) {
    return const [];
  }
  return value
      .whereType<Map<dynamic, dynamic>>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList(growable: false);
}

Map<String, dynamic> _map(dynamic value) {
  if (value is Map) {
    return Map<String, dynamic>.from(value);
  }
  return const {};
}

List<String> _strings(dynamic value) {
  if (value is! List) {
    return const [];
  }
  return value
      .map((item) => item?.toString().trim() ?? '')
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

int _int(dynamic value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.round();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _double(dynamic value, {double fallback = 0}) {
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? fallback;
}
