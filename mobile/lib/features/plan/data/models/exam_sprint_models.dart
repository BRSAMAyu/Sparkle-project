class ExamSprintScopeContext {
  ExamSprintScopeContext({
    this.text,
    this.fileIds = const <String>[],
    this.fileNames = const <String>[],
  });

  final String? text;
  final List<String> fileIds;
  final List<String> fileNames;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'text': text?.trim(),
        'file_ids': fileIds,
        'file_names': fileNames,
      };
}

class ExamSprintBaselineInput {
  ExamSprintBaselineInput({
    required this.currentLevel,
    this.weakChapters = const <String>[],
  });

  final int currentLevel;
  final List<String> weakChapters;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'current_level': currentLevel,
        'weak_chapters': weakChapters,
      };
}

class ExamSprintIntakeRequest {
  ExamSprintIntakeRequest({
    required this.subject,
    required this.examDate,
    required this.targetMode,
    required this.scopeContext,
    required this.baseline,
    required this.dailyStudyMinutes,
    this.conversationId,
  });

  final String subject;
  final DateTime examDate;
  final String targetMode;
  final ExamSprintScopeContext scopeContext;
  final ExamSprintBaselineInput baseline;
  final int dailyStudyMinutes;
  final String? conversationId;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'subject': subject.trim(),
        'exam_date': examDate.toIso8601String().split('T').first,
        'target_mode': targetMode,
        'scope_context': scopeContext.toJson(),
        'baseline': baseline.toJson(),
        'daily_study_minutes': dailyStudyMinutes,
        if (conversationId != null && conversationId!.trim().isNotEmpty)
          'conversation_id': conversationId!.trim(),
      };
}

class PostExamReviewRequest {
  PostExamReviewRequest({
    required this.planId,
    required this.resultRating,
    required this.resultDescription,
    required this.biggestChallenge,
    required this.strategyFeedback,
    required this.selfAdvice,
  });

  final String planId;
  final int resultRating;
  final String resultDescription;
  final String biggestChallenge;
  final String strategyFeedback;
  final String selfAdvice;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'plan_id': planId.trim(),
        'result_rating': resultRating,
        'result_description': resultDescription.trim(),
        'biggest_challenge': biggestChallenge.trim(),
        'strategy_feedback': strategyFeedback.trim(),
        'self_advice': selfAdvice.trim(),
      };
}

class SprintCompletionSummary {
  const SprintCompletionSummary({
    required this.masteredNodesCount,
    required this.repairedErrorsCount,
    required this.completedTasksCount,
    required this.strongestArea,
    required this.growthArea,
  });

  factory SprintCompletionSummary.fromJson(Map<String, dynamic> json) =>
      SprintCompletionSummary(
        masteredNodesCount:
            (json['mastered_nodes_count'] as num?)?.toInt() ?? 0,
        repairedErrorsCount:
            (json['repaired_errors_count'] as num?)?.toInt() ?? 0,
        completedTasksCount:
            (json['completed_tasks_count'] as num?)?.toInt() ?? 0,
        strongestArea: json['strongest_area']?.toString() ?? '',
        growthArea: json['growth_area']?.toString() ?? '',
      );

  final int masteredNodesCount;
  final int repairedErrorsCount;
  final int completedTasksCount;
  final String strongestArea;
  final String growthArea;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'mastered_nodes_count': masteredNodesCount,
        'repaired_errors_count': repairedErrorsCount,
        'completed_tasks_count': completedTasksCount,
        'strongest_area': strongestArea,
        'growth_area': growthArea,
      };
}

class SprintCompletionCheckResult {
  const SprintCompletionCheckResult({
    required this.completed,
    this.summary,
  });

  factory SprintCompletionCheckResult.fromJson(Map<String, dynamic> json) {
    final rawSummary = json['summary'];
    return SprintCompletionCheckResult(
      completed: json['completed'] == true,
      summary: rawSummary is Map
          ? SprintCompletionSummary.fromJson(
              Map<String, dynamic>.from(rawSummary),
            )
          : null,
    );
  }

  final bool completed;
  final SprintCompletionSummary? summary;
}

class ExamSprintGoalModel {
  ExamSprintGoalModel({
    required this.examDate,
    required this.daysLeft,
    required this.targetMode,
    required this.estimatedScoreNow,
    required this.targetScoreHint,
    required this.recommendedMode,
  });

  factory ExamSprintGoalModel.fromJson(Map<String, dynamic> json) =>
      ExamSprintGoalModel(
        examDate: DateTime.parse(json['exam_date'].toString()),
        daysLeft: (json['days_left'] as num?)?.toInt() ?? 0,
        targetMode: json['target_mode']?.toString() ?? 'pass',
        estimatedScoreNow: (json['estimated_score_now'] as num?)?.toInt() ?? 0,
        targetScoreHint: (json['target_score_hint'] as num?)?.toInt() ?? 60,
        recommendedMode: json['recommended_mode']?.toString() ?? 'pass',
      );

  final DateTime examDate;
  final int daysLeft;
  final String targetMode;
  final int estimatedScoreNow;
  final int targetScoreHint;
  final String recommendedMode;
}

class ExamSprintAssessment {
  ExamSprintAssessment({
    required this.passProbability,
    required this.recommendedMode,
    required this.recommendedModeLabel,
    required this.summary,
  });

  factory ExamSprintAssessment.fromJson(Map<String, dynamic> json) =>
      ExamSprintAssessment(
        passProbability: (json['pass_probability'] as num?)?.toDouble() ?? 0.0,
        recommendedMode: json['recommended_mode']?.toString() ?? 'pass',
        recommendedModeLabel:
            json['recommended_mode_label']?.toString() ?? '先过',
        summary: json['summary']?.toString() ?? '',
      );

  final double passProbability;
  final String recommendedMode;
  final String recommendedModeLabel;
  final String summary;
}

class ExamSprintPackSelection {
  ExamSprintPackSelection({
    required this.packId,
    required this.packName,
    required this.selectionType,
    required this.reason,
  });

  factory ExamSprintPackSelection.fromJson(Map<String, dynamic> json) =>
      ExamSprintPackSelection(
        packId: json['pack_id']?.toString() ?? '',
        packName: json['pack_name']?.toString() ?? '',
        selectionType: json['selection_type']?.toString() ?? 'generic_policy',
        reason: json['reason']?.toString() ?? '',
      );

  final String packId;
  final String packName;
  final String selectionType;
  final String reason;
}

class ExamSprintStrategyPreview {
  ExamSprintStrategyPreview({
    required this.sprintMode,
    required this.dailyCommitmentRange,
    required this.firstDayFocus,
    required this.firstDayOutput,
  });

  factory ExamSprintStrategyPreview.fromJson(Map<String, dynamic> json) =>
      ExamSprintStrategyPreview(
        sprintMode: json['sprint_mode']?.toString() ?? 'standard_exam_sprint',
        dailyCommitmentRange: json['daily_commitment_range']?.toString() ?? '',
        firstDayFocus: json['first_day_focus']?.toString() ?? '',
        firstDayOutput: json['first_day_output']?.toString() ?? '',
      );

  final String sprintMode;
  final String dailyCommitmentRange;
  final String firstDayFocus;
  final String firstDayOutput;
}

class ExamSprintLaunchPayload {
  ExamSprintLaunchPayload({
    required this.planId,
    required this.planName,
    required this.firstDayTaskIds,
    required this.planRoute,
    this.recommendedTaskId,
    this.recommendedTaskRoute,
  });

  factory ExamSprintLaunchPayload.fromJson(Map<String, dynamic> json) =>
      ExamSprintLaunchPayload(
        planId: json['plan_id']?.toString() ?? '',
        planName: json['plan_name']?.toString() ?? '',
        firstDayTaskIds:
            (json['first_day_task_ids'] as List<dynamic>? ?? const <dynamic>[])
                .map((dynamic item) => item.toString())
                .toList(),
        recommendedTaskId: json['recommended_task_id']?.toString(),
        planRoute: json['plan_route']?.toString() ?? '',
        recommendedTaskRoute: json['recommended_task_route']?.toString(),
      );

  final String planId;
  final String planName;
  final List<String> firstDayTaskIds;
  final String? recommendedTaskId;
  final String planRoute;
  final String? recommendedTaskRoute;
}

class ExamSprintUserModel {
  ExamSprintUserModel({
    required this.subject,
    required this.examScope,
    required this.knowledgeBaseline,
    required this.currentLevel,
    required this.weakChapters,
    required this.dailyStudyMinutes,
    required this.availableMaterials,
    required this.scopeFileIds,
    required this.scopeFileNames,
    required this.planningSessionId,
    required this.conversationId,
  });

  factory ExamSprintUserModel.fromJson(Map<String, dynamic> json) =>
      ExamSprintUserModel(
        subject: json['subject']?.toString() ?? '',
        examScope: json['exam_scope']?.toString() ?? '',
        knowledgeBaseline: json['knowledge_baseline']?.toString() ?? '',
        currentLevel: (json['current_level'] as num?)?.toInt() ?? 0,
        weakChapters:
            (json['weak_chapters'] as List<dynamic>? ?? const <dynamic>[])
                .map((dynamic item) => item.toString())
                .toList(),
        dailyStudyMinutes: (json['daily_study_minutes'] as num?)?.toInt() ?? 0,
        availableMaterials:
            (json['available_materials'] as List<dynamic>? ?? const <dynamic>[])
                .map((dynamic item) => item.toString())
                .toList(),
        scopeFileIds:
            (json['scope_file_ids'] as List<dynamic>? ?? const <dynamic>[])
                .map((dynamic item) => item.toString())
                .toList(),
        scopeFileNames:
            (json['scope_file_names'] as List<dynamic>? ?? const <dynamic>[])
                .map((dynamic item) => item.toString())
                .toList(),
        planningSessionId: json['planning_session_id']?.toString() ?? '',
        conversationId: json['conversation_id']?.toString() ?? '',
      );

  final String subject;
  final String examScope;
  final String knowledgeBaseline;
  final int currentLevel;
  final List<String> weakChapters;
  final int dailyStudyMinutes;
  final List<String> availableMaterials;
  final List<String> scopeFileIds;
  final List<String> scopeFileNames;
  final String planningSessionId;
  final String conversationId;
}

class ExamSprintIntakeResult {
  ExamSprintIntakeResult({
    required this.planningSessionId,
    required this.conversationId,
    required this.userModel,
    required this.goalModel,
    required this.selectedPack,
    required this.initialAssessment,
    required this.strategyPreview,
    required this.launch,
  });

  factory ExamSprintIntakeResult.fromJson(Map<String, dynamic> json) =>
      ExamSprintIntakeResult(
        planningSessionId: json['planning_session_id']?.toString() ?? '',
        conversationId: json['conversation_id']?.toString() ?? '',
        userModel: ExamSprintUserModel.fromJson(
          json['user_model'] as Map<String, dynamic>? ?? <String, dynamic>{},
        ),
        goalModel: ExamSprintGoalModel.fromJson(
          json['goal_model'] as Map<String, dynamic>? ?? <String, dynamic>{},
        ),
        selectedPack: ExamSprintPackSelection.fromJson(
          json['selected_pack'] as Map<String, dynamic>? ?? <String, dynamic>{},
        ),
        initialAssessment: ExamSprintAssessment.fromJson(
          json['initial_assessment'] as Map<String, dynamic>? ??
              <String, dynamic>{},
        ),
        strategyPreview: ExamSprintStrategyPreview.fromJson(
          json['strategy_preview'] as Map<String, dynamic>? ??
              <String, dynamic>{},
        ),
        launch: ExamSprintLaunchPayload.fromJson(
          json['launch'] as Map<String, dynamic>? ?? <String, dynamic>{},
        ),
      );

  final String planningSessionId;
  final String conversationId;
  final ExamSprintUserModel userModel;
  final ExamSprintGoalModel goalModel;
  final ExamSprintPackSelection selectedPack;
  final ExamSprintAssessment initialAssessment;
  final ExamSprintStrategyPreview strategyPreview;
  final ExamSprintLaunchPayload launch;
}

class LearningPortfolioEntry {
  const LearningPortfolioEntry({
    required this.planId,
    required this.planName,
    required this.subject,
    required this.status,
    required this.masteredNodesCount,
    required this.progress,
    this.sprintMode,
    this.startedAt,
    this.completedAt,
    this.targetDate,
    this.strongestArea,
    this.growthArea,
    this.selfRating,
    this.resultRating,
    this.resultDescription,
    this.headline,
    this.currentScore,
    this.weakestPoints = const <String>[],
    this.proudNodes = const <String>[],
  });

  factory LearningPortfolioEntry.fromJson(Map<String, dynamic> json) =>
      LearningPortfolioEntry(
        planId: json['plan_id']?.toString() ?? '',
        planName: json['plan_name']?.toString() ?? '',
        subject: json['subject']?.toString() ?? '',
        sprintMode: json['sprint_mode']?.toString(),
        status: json['status']?.toString() ?? 'planned',
        masteredNodesCount:
            (json['mastered_nodes_count'] as num?)?.toInt() ?? 0,
        startedAt: _tryParseDateTime(json['started_at']?.toString()),
        completedAt: _tryParseDateTime(json['completed_at']?.toString()),
        targetDate: _tryParseDateTime(json['target_date']?.toString()),
        progress: (json['progress'] as num?)?.toDouble() ?? 0,
        strongestArea: json['strongest_area']?.toString(),
        growthArea: json['growth_area']?.toString(),
        selfRating: (json['self_rating'] as num?)?.toInt(),
        resultRating: (json['result_rating'] as num?)?.toInt(),
        resultDescription: json['result_description']?.toString(),
        headline: json['headline']?.toString(),
        currentScore: (json['current_score'] as num?)?.toDouble(),
        weakestPoints:
            (json['weakest_points'] as List<dynamic>? ?? const <dynamic>[])
                .map((dynamic item) => item.toString())
                .where((String item) => item.trim().isNotEmpty)
                .toList(),
        proudNodes: (json['proud_nodes'] as List<dynamic>? ?? const <dynamic>[])
            .map((dynamic item) => item.toString())
            .where((String item) => item.trim().isNotEmpty)
            .toList(),
      );

  final String planId;
  final String planName;
  final String subject;
  final String? sprintMode;
  final String status;
  final int masteredNodesCount;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final DateTime? targetDate;
  final double progress;
  final String? strongestArea;
  final String? growthArea;
  final int? selfRating;
  final int? resultRating;
  final String? resultDescription;
  final String? headline;
  final double? currentScore;
  final List<String> weakestPoints;
  final List<String> proudNodes;

  bool get isActive => status == 'active';
  bool get isCompleted => status == 'completed';
  bool get isPlanned => status == 'planned';
}

class LearningPortfolioResult {
  const LearningPortfolioResult({
    required this.entries,
    required this.totalMasteredNodes,
    required this.activeCount,
    required this.completedCount,
    required this.plannedCount,
  });

  factory LearningPortfolioResult.fromJson(Map<String, dynamic> json) =>
      LearningPortfolioResult(
        entries: (json['entries'] as List<dynamic>? ?? const <dynamic>[])
            .whereType<Map<dynamic, dynamic>>()
            .map(
              (Map<dynamic, dynamic> item) => LearningPortfolioEntry.fromJson(
                Map<String, dynamic>.from(item),
              ),
            )
            .toList(),
        totalMasteredNodes:
            (json['total_mastered_nodes'] as num?)?.toInt() ?? 0,
        activeCount: (json['active_count'] as num?)?.toInt() ?? 0,
        completedCount: (json['completed_count'] as num?)?.toInt() ?? 0,
        plannedCount: (json['planned_count'] as num?)?.toInt() ?? 0,
      );

  final List<LearningPortfolioEntry> entries;
  final int totalMasteredNodes;
  final int activeCount;
  final int completedCount;
  final int plannedCount;

  List<LearningPortfolioEntry> get activeEntries => entries
      .where((LearningPortfolioEntry entry) => entry.isActive)
      .toList(growable: false);

  List<LearningPortfolioEntry> get completedEntries => entries
      .where((LearningPortfolioEntry entry) => entry.isCompleted)
      .toList(growable: false);

  List<LearningPortfolioEntry> get plannedEntries => entries
      .where((LearningPortfolioEntry entry) => entry.isPlanned)
      .toList(growable: false);

  bool get isEmpty => entries.isEmpty;
}

DateTime? _tryParseDateTime(String? raw) {
  if (raw == null || raw.trim().isEmpty) {
    return null;
  }
  return DateTime.tryParse(raw);
}
