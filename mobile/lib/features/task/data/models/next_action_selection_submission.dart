import 'package:sparkle/features/task/data/models/next_action.dart';

/// Next action selection submission model
///
/// Used to track user interactions with next action suggestions.
class NextActionSelectionSubmission {
  const NextActionSelectionSubmission({
    required this.taskId,
    required this.actionType,
    required this.actionTitle,
    required this.selected,
    this.skipped = false,
    this.displayPosition,
    this.displayedActionsCount,
    this.context,
  });

  factory NextActionSelectionSubmission.fromJson(Map<String, dynamic> json) =>
      NextActionSelectionSubmission(
        taskId: json['task_id'] as String,
        actionType: json['action_type'] as String,
        actionTitle: json['action_title'] as String,
        selected: json['selected'] as bool? ?? false,
        skipped: json['skipped'] as bool? ?? false,
        displayPosition: json['display_position'] as int?,
        displayedActionsCount: json['displayed_actions_count'] as int?,
        context: json['context'] as Map<String, dynamic>?,
      );

  /// Create from a NextAction with selection state
  factory NextActionSelectionSubmission.fromAction({
    required String taskId,
    required NextAction action,
    required bool selected,
    int? displayPosition,
    int? displayedActionsCount,
    Map<String, dynamic>? context,
  }) =>
      NextActionSelectionSubmission(
        taskId: taskId,
        actionType: action.type.name,
        actionTitle: action.title,
        selected: selected,
        displayPosition: displayPosition,
        displayedActionsCount: displayedActionsCount,
        context: context,
      );

  final String taskId;
  final String actionType;
  final String actionTitle;
  final bool selected;
  final bool skipped;
  final int? displayPosition;
  final int? displayedActionsCount;
  final Map<String, dynamic>? context;

  Map<String, dynamic> toJson() => {
        'task_id': taskId,
        'action_type': actionType,
        'action_title': actionTitle,
        'selected': selected,
        if (skipped) 'skipped': skipped,
        if (displayPosition != null) 'display_position': displayPosition,
        if (displayedActionsCount != null)
          'displayed_actions_count': displayedActionsCount,
        if (context != null) 'context': context,
      };

  NextActionSelectionSubmission copyWith({
    String? taskId,
    String? actionType,
    String? actionTitle,
    bool? selected,
    bool? skipped,
    int? displayPosition,
    int? displayedActionsCount,
    Map<String, dynamic>? context,
  }) =>
      NextActionSelectionSubmission(
        taskId: taskId ?? this.taskId,
        actionType: actionType ?? this.actionType,
        actionTitle: actionTitle ?? this.actionTitle,
        selected: selected ?? this.selected,
        skipped: skipped ?? this.skipped,
        displayPosition: displayPosition ?? this.displayPosition,
        displayedActionsCount: displayedActionsCount ?? this.displayedActionsCount,
        context: context ?? this.context,
      );

  /// Create a skip record (user skipped all suggestions)
  static List<NextActionSelectionSubmission> createSkipRecords({
    required String taskId,
    required List<NextAction> actions,
  }) =>
      actions
          .asMap()
          .entries
          .map(
            (entry) => NextActionSelectionSubmission(
              taskId: taskId,
              actionType: entry.value.type.name,
              actionTitle: entry.value.title,
              selected: false,
              skipped: true,
              displayPosition: entry.key,
              displayedActionsCount: actions.length,
            ),
          )
          .toList();
}
