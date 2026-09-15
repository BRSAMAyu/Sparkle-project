/// Task feedback submission model
class TaskFeedbackSubmission {
  TaskFeedbackSubmission({
    this.completionQuality,
    this.feedbackText,
    this.category,
    this.stuckPoint,
    this.effectiveMethod,
    this.adjustmentIntention,
  });

  factory TaskFeedbackSubmission.fromJson(Map<String, dynamic> json) =>
      TaskFeedbackSubmission(
        completionQuality: json['completion_quality'] as int?,
        feedbackText: json['feedback_text'] as String?,
        category: json['category'] as String?,
        stuckPoint: json['stuck_point'] as String?,
        effectiveMethod: json['effective_method'] as String?,
        adjustmentIntention: json['adjustment_intention'] as String?,
      );

  final int? completionQuality; // 1-5 star rating
  final String? feedbackText;
  final String? category;
  final String? stuckPoint;
  final String? effectiveMethod;
  final String? adjustmentIntention;

  Map<String, dynamic> toJson() => {
        if (completionQuality != null) 'completion_quality': completionQuality,
        if (feedbackText != null) 'feedback_text': feedbackText,
        if (category != null) 'category': category,
        if (stuckPoint != null) 'stuck_point': stuckPoint,
        if (effectiveMethod != null) 'effective_method': effectiveMethod,
        if (adjustmentIntention != null)
          'adjustment_intention': adjustmentIntention,
      };

  TaskFeedbackSubmission copyWith({
    int? completionQuality,
    String? feedbackText,
    String? category,
    String? stuckPoint,
    String? effectiveMethod,
    String? adjustmentIntention,
  }) =>
      TaskFeedbackSubmission(
        completionQuality: completionQuality ?? this.completionQuality,
        feedbackText: feedbackText ?? this.feedbackText,
        category: category ?? this.category,
        stuckPoint: stuckPoint ?? this.stuckPoint,
        effectiveMethod: effectiveMethod ?? this.effectiveMethod,
        adjustmentIntention: adjustmentIntention ?? this.adjustmentIntention,
      );
}
