import 'package:sparkle/core/services/i18n_service.dart';

/// Next action suggested after task completion
class NextAction {
  const NextAction({
    required this.type,
    required this.title,
    required this.description,
    required this.estimatedMinutes,
    required this.energyCost,
    required this.difficulty,
    required this.reason,
    this.quickCreateParams,
    this.existingTaskId,
    this.canQuickCreate = true,
  });

  factory NextAction.fromJson(Map<String, dynamic> json) => NextAction(
        type: _parseType(json['type'] as String?),
        title: json['title'] as String,
        description: json['description'] as String? ?? '',
        estimatedMinutes: json['estimated_minutes'] as int? ?? 5,
        energyCost: json['energy_cost'] as int? ?? 1,
        difficulty: json['difficulty'] as int? ?? 1,
        reason: json['reason'] as String? ?? '',
        quickCreateParams: json['quick_create_params'] as Map<String, dynamic>?,
        existingTaskId: json['existing_task_id'] as String?,
        canQuickCreate: json['can_quick_create'] as bool? ?? true,
      );

  static NextActionType _parseType(String? typeStr) {
    switch (typeStr) {
      case 'quick_review':
        return NextActionType.quickReview;
      case 'light_expand':
        return NextActionType.lightExpand;
      case 'practice_apply':
        return NextActionType.practiceApply;
      case 'rest_break':
        return NextActionType.restBreak;
      case 'continue_plan':
        return NextActionType.continuePlan;
      default:
        return NextActionType.quickReview;
    }
  }

  final NextActionType type;
  final String title;
  final String description;
  final int estimatedMinutes;
  final int energyCost;
  final int difficulty;
  final String reason;
  final Map<String, dynamic>? quickCreateParams;
  final String? existingTaskId;
  final bool canQuickCreate;

  Map<String, dynamic> toJson() => {
        'type': _typeToString(type),
        'title': title,
        'description': description,
        'estimated_minutes': estimatedMinutes,
        'energy_cost': energyCost,
        'difficulty': difficulty,
        'reason': reason,
        if (quickCreateParams != null) 'quick_create_params': quickCreateParams,
        if (existingTaskId != null) 'existing_task_id': existingTaskId,
        'can_quick_create': canQuickCreate,
      };

  static String _typeToString(NextActionType type) {
    switch (type) {
      case NextActionType.quickReview:
        return 'quick_review';
      case NextActionType.lightExpand:
        return 'light_expand';
      case NextActionType.practiceApply:
        return 'practice_apply';
      case NextActionType.restBreak:
        return 'rest_break';
      case NextActionType.continuePlan:
        return 'continue_plan';
    }
  }

  NextAction copyWith({
    NextActionType? type,
    String? title,
    String? description,
    int? estimatedMinutes,
    int? energyCost,
    int? difficulty,
    String? reason,
    Map<String, dynamic>? quickCreateParams,
    String? existingTaskId,
    bool? canQuickCreate,
  }) =>
      NextAction(
        type: type ?? this.type,
        title: title ?? this.title,
        description: description ?? this.description,
        estimatedMinutes: estimatedMinutes ?? this.estimatedMinutes,
        energyCost: energyCost ?? this.energyCost,
        difficulty: difficulty ?? this.difficulty,
        reason: reason ?? this.reason,
        quickCreateParams: quickCreateParams ?? this.quickCreateParams,
        existingTaskId: existingTaskId ?? this.existingTaskId,
        canQuickCreate: canQuickCreate ?? this.canQuickCreate,
      );
}

enum NextActionType {
  quickReview,
  lightExpand,
  practiceApply,
  restBreak,
  continuePlan;
}

extension NextActionTypeExt on NextActionType {
  String get displayName {
    final l10n = I18nService.instance.l10n;
    switch (this) {
      case NextActionType.quickReview:
        return l10n.nextActionQuickReviewTitle;
      case NextActionType.lightExpand:
        return l10n.nextActionLightExpandTitle;
      case NextActionType.practiceApply:
        return l10n.nextActionPracticeApplyTitle;
      case NextActionType.restBreak:
        return l10n.nextActionRestBreakTitle;
      case NextActionType.continuePlan:
        return l10n.nextActionContinuePlanTitle;
    }
  }

  String get description {
    final l10n = I18nService.instance.l10n;
    switch (this) {
      case NextActionType.quickReview:
        return l10n.nextActionQuickReviewDescription;
      case NextActionType.lightExpand:
        return l10n.nextActionLightExpandDescription;
      case NextActionType.practiceApply:
        return l10n.nextActionPracticeApplyDescription;
      case NextActionType.restBreak:
        return l10n.nextActionRestBreakDescription;
      case NextActionType.continuePlan:
        return l10n.nextActionContinuePlanDescription;
    }
  }
}
