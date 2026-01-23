/// Task feedback submission model
class TaskFeedbackSubmission {
  TaskFeedbackSubmission({
    this.completionQuality,
    this.feedbackText,
  });

  factory TaskFeedbackSubmission.fromJson(Map<String, dynamic> json) =>
      TaskFeedbackSubmission(
        completionQuality: json['completion_quality'] as int?,
        feedbackText: json['feedback_text'] as String?,
      );

  final int? completionQuality; // 1-5 star rating
  final String? feedbackText;

  Map<String, dynamic> toJson() => {
        if (completionQuality != null) 'completion_quality': completionQuality,
        if (feedbackText != null) 'feedback_text': feedbackText,
      };

  TaskFeedbackSubmission copyWith({
    int? completionQuality,
    String? feedbackText,
  }) =>
      TaskFeedbackSubmission(
        completionQuality: completionQuality ?? this.completionQuality,
        feedbackText: feedbackText ?? this.feedbackText,
      );
}
