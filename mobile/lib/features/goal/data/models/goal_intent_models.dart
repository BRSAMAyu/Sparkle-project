/// Phase-1 Entry Wire — server-side intent analysis result.
///
/// Kept in a dedicated file (not [goal_creation_models.dart]) so the existing
/// goal model contract stays untouched and this feature can be removed
/// cleanly if rolled back.
///
/// `mode` shape mirrors `backend/app/api/v1/goal_intent.py::GoalIntentAnalyzeResponse`:
///   • "disabled" — kill switch off/shadow; UI should fall back to legacy wizard.
///   • "exam_rescue" / "exam_build" — exam detector hit; surface an Aha card.
///   • "job_search_*", "project_*", "habit_*" — non-exam detector matched.
///   • "standard" — server understood the message but had no specific judgement;
///     UI should ask for one clarifying detail.
class GoalIntentAnalysis {
  const GoalIntentAnalysis({
    required this.mode,
    required this.confidence,
    required this.headline,
    required this.nextBestAction,
    required this.correctionOptions,
    required this.suggestedActions,
    this.detectedSubject,
    this.deadlineDays,
    this.baseline,
  });

  factory GoalIntentAnalysis.disabled() => const GoalIntentAnalysis(
        mode: 'disabled',
        confidence: 0,
        headline: '',
        nextBestAction: '',
        correctionOptions: [],
        suggestedActions: [],
      );

  factory GoalIntentAnalysis.fromJson(Map<String, dynamic> json) =>
      GoalIntentAnalysis(
        mode: _stringOr(json['mode'], 'disabled'),
        detectedSubject: _stringOrNull(json['detected_subject']),
        deadlineDays: _intOrNull(json['deadline_days']),
        baseline: _stringOrNull(json['baseline']),
        confidence: _doubleOr(json['confidence'], 0),
        headline: _stringOr(json['headline'], ''),
        nextBestAction: _stringOr(json['next_best_action'], ''),
        correctionOptions: _listOfMaps(json['correction_options'])
            .map(GoalIntentCorrectionOption.fromJson)
            .toList(growable: false),
        suggestedActions: _listOfMaps(json['suggested_actions'])
            .map(GoalIntentSuggestedAction.fromJson)
            .toList(growable: false),
      );

  final String mode;
  final String? detectedSubject;
  final int? deadlineDays;
  final String? baseline;
  final double confidence;
  final String headline;
  final String nextBestAction;
  final List<GoalIntentCorrectionOption> correctionOptions;
  final List<GoalIntentSuggestedAction> suggestedActions;

  bool get isDisabled => mode == 'disabled';

  bool get isActionable =>
      !isDisabled && (headline.isNotEmpty || suggestedActions.isNotEmpty);

  bool get isExamRescue => mode == 'exam_rescue';

  /// Translate detected mode into the legacy wizard's `goal_type` field so
  /// the existing /goals POST flow keeps working unchanged.
  String get inferredGoalType {
    if (mode.startsWith('exam')) return 'academic';
    if (mode.startsWith('job_search')) return 'skill';
    if (mode.startsWith('project')) return 'project';
    if (mode.startsWith('habit')) return 'habit';
    return 'other';
  }

  /// Translate deadline_days into the legacy wizard's `time_horizon` field.
  String get inferredTimeHorizon {
    final d = deadlineDays;
    if (d == null) return 'medium';
    if (d <= 30) return 'short';
    if (d <= 90) return 'medium';
    return 'long';
  }
}

class GoalIntentCorrectionOption {
  const GoalIntentCorrectionOption({required this.key, required this.label});

  factory GoalIntentCorrectionOption.fromJson(Map<String, dynamic> json) =>
      GoalIntentCorrectionOption(
        key: _stringOr(json['key'], ''),
        label: _stringOr(json['label'], ''),
      );

  final String key;
  final String label;
}

class GoalIntentSuggestedAction {
  const GoalIntentSuggestedAction({
    required this.key,
    required this.label,
    required this.estimatedMinutes,
  });

  factory GoalIntentSuggestedAction.fromJson(Map<String, dynamic> json) =>
      GoalIntentSuggestedAction(
        key: _stringOr(json['key'], ''),
        label: _stringOr(json['label'], ''),
        estimatedMinutes: _intOrNull(json['estimated_minutes']) ?? 0,
      );

  final String key;
  final String label;
  final int estimatedMinutes;
}

String _stringOr(dynamic value, String fallback) {
  if (value == null) return fallback;
  final text = value.toString().trim();
  return text.isEmpty ? fallback : text;
}

String? _stringOrNull(dynamic value) {
  if (value == null) return null;
  final text = value.toString().trim();
  return text.isEmpty ? null : text;
}

int? _intOrNull(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}

double _doubleOr(dynamic value, double fallback) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value) ?? fallback;
  return fallback;
}

List<Map<String, dynamic>> _listOfMaps(dynamic value) {
  if (value is! List) return const [];
  return value
      .whereType<Map<dynamic, dynamic>>()
      .map((m) => Map<String, dynamic>.from(m))
      .toList(growable: false);
}

GoalIntentCorrectionOption goalIntentCorrectionOptionFromJson(
        Map<String, dynamic> json) =>
    GoalIntentCorrectionOption.fromJson(json);

GoalIntentSuggestedAction goalIntentSuggestedActionFromJson(
        Map<String, dynamic> json) =>
    GoalIntentSuggestedAction.fromJson(json);
