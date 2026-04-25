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
