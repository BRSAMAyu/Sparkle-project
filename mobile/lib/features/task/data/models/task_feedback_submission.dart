/// Task feedback submission model
class TaskFeedbackSubmission {
  TaskFeedbackSubmission({
    this.completionQuality,
    this.feedbackText,
    this.category,
  });

  factory TaskFeedbackSubmission.fromJson(Map<String, dynamic> json) =>
      TaskFeedbackSubmission(
        completionQuality: json['completion_quality'] as int?,
        feedbackText: json['feedback_text'] as String?,
        category: json['category'] as String?,
      );

  final int? completionQuality; // 1-5 star rating
  final String? feedbackText;
  final String? category;

  Map<String, dynamic> toJson() => {
        if (completionQuality != null) 'completion_quality': completionQuality,
        if (feedbackText != null) 'feedback_text': feedbackText,
        if (category != null) 'category': category,
      };

  TaskFeedbackSubmission copyWith({
    int? completionQuality,
    String? feedbackText,
    String? category,
  }) =>
      TaskFeedbackSubmission(
        completionQuality: completionQuality ?? this.completionQuality,
        feedbackText: feedbackText ?? this.feedbackText,
        category: category ?? this.category,
      );
}
