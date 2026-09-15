class PlanPhaseModel {
  PlanPhaseModel({
    required this.cardId,
    required this.title,
    required this.phaseIndex,
    required this.lifecycleStatus,
    required this.progress,
    required this.taskCount,
    required this.occurrenceCount,
    required this.completedOccurrenceCount,
    this.objective,
    this.estimatedStart,
    this.estimatedEnd,
    this.entryCriteria = const [],
    this.exitCriteria = const [],
    this.feedbackGateRequired = true,
    this.phaseWeight,
    this.syntheticPhase = false,
    this.needsFeedback = false,
    this.alignmentScore,
  });

  factory PlanPhaseModel.fromJson(Map<String, dynamic> json) {
    DateTime? parseDate(dynamic value) {
      if (value is String && value.isNotEmpty) {
        return DateTime.tryParse(value);
      }
      return null;
    }

    List<String> parseStringList(dynamic value) {
      if (value is List) {
        return value.map((item) => item.toString()).toList();
      }
      return const [];
    }

    return PlanPhaseModel(
      cardId: json['card_id']?.toString() ?? '',
      title: json['title']?.toString() ?? 'Untitled phase',
      phaseIndex: (json['phase_index'] as num?)?.toInt() ?? 0,
      lifecycleStatus: json['lifecycle_status']?.toString() ?? 'DRAFT',
      progress: (json['progress'] as num?)?.toDouble() ?? 0,
      taskCount: (json['task_count'] as num?)?.toInt() ?? 0,
      occurrenceCount: (json['occurrence_count'] as num?)?.toInt() ?? 0,
      completedOccurrenceCount:
          (json['completed_occurrence_count'] as num?)?.toInt() ?? 0,
      objective: json['objective']?.toString(),
      estimatedStart: parseDate(json['estimated_start']),
      estimatedEnd: parseDate(json['estimated_end']),
      entryCriteria: parseStringList(json['entry_criteria']),
      exitCriteria: parseStringList(json['exit_criteria']),
      feedbackGateRequired: json['feedback_gate_required'] as bool? ?? true,
      phaseWeight: (json['phase_weight'] as num?)?.toDouble(),
      syntheticPhase: json['synthetic_phase'] as bool? ?? false,
      needsFeedback: json['needs_feedback'] as bool? ?? false,
      alignmentScore: (json['alignment_score'] as num?)?.toDouble(),
    );
  }

  final String cardId;
  final String title;
  final int phaseIndex;
  final String lifecycleStatus;
  final double progress;
  final int taskCount;
  final int occurrenceCount;
  final int completedOccurrenceCount;
  final String? objective;
  final DateTime? estimatedStart;
  final DateTime? estimatedEnd;
  final List<String> entryCriteria;
  final List<String> exitCriteria;
  final bool feedbackGateRequired;
  final double? phaseWeight;
  final bool syntheticPhase;
  final bool needsFeedback;
  final double? alignmentScore;
}

class PlanPhaseBundle {
  PlanPhaseBundle({
    required this.planCardId,
    required this.currentPhaseCardId,
    required this.progressMode,
    required this.weightedProgress,
    required this.phases,
  });

  factory PlanPhaseBundle.fromJson(Map<String, dynamic> json) {
    final phasesPayload = json['phases'];
    return PlanPhaseBundle(
      planCardId: json['plan_card_id']?.toString(),
      currentPhaseCardId: json['current_phase_card_id']?.toString(),
      progressMode: json['progress_mode']?.toString() ?? 'legacy',
      weightedProgress: (json['weighted_progress'] as num?)?.toDouble(),
      phases: phasesPayload is List
          ? phasesPayload
              .map(
                (item) => PlanPhaseModel.fromJson(item as Map<String, dynamic>),
              )
              .toList()
          : const [],
    );
  }

  final String? planCardId;
  final String? currentPhaseCardId;
  final String progressMode;
  final double? weightedProgress;
  final List<PlanPhaseModel> phases;
}
