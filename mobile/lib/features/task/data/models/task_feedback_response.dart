/// Task feedback response model
///
/// Enhanced response from the backend when submitting task feedback.
/// Includes preference update information.
class TaskFeedbackResponse {
  const TaskFeedbackResponse({
    required this.success,
    this.message,
    this.preferenceUpdates,
    this.reflectionPayload,
    this.aiResponse,
  });

  factory TaskFeedbackResponse.fromJson(Map<String, dynamic> json) =>
      TaskFeedbackResponse(
        success: json['success'] as bool? ?? false,
        message: json['message'] as String?,
        preferenceUpdates: json['preference_updates'] != null
            ? PreferenceUpdates.fromJson(
                json['preference_updates'] as Map<String, dynamic>,
              )
            : null,
        reflectionPayload: json['reflection_payload'] is Map
            ? Map<String, dynamic>.from(
                json['reflection_payload'] as Map<dynamic, dynamic>,
              )
            : null,
        aiResponse: json['ai_response'] as String?,
      );

  final bool success;
  final String? message;
  final PreferenceUpdates? preferenceUpdates;
  final Map<String, dynamic>? reflectionPayload;
  final String? aiResponse;

  Map<String, dynamic> toJson() => {
        'success': success,
        if (message != null) 'message': message,
        if (preferenceUpdates != null)
          'preference_updates': preferenceUpdates?.toJson(),
        if (reflectionPayload != null) 'reflection_payload': reflectionPayload,
        if (aiResponse != null) 'ai_response': aiResponse,
      };

  TaskFeedbackResponse copyWith({
    bool? success,
    String? message,
    PreferenceUpdates? preferenceUpdates,
    Map<String, dynamic>? reflectionPayload,
    String? aiResponse,
  }) =>
      TaskFeedbackResponse(
        success: success ?? this.success,
        message: message ?? this.message,
        preferenceUpdates: preferenceUpdates ?? this.preferenceUpdates,
        reflectionPayload: reflectionPayload ?? this.reflectionPayload,
        aiResponse: aiResponse ?? this.aiResponse,
      );
}

/// Preference updates detail
class PreferenceUpdates {
  const PreferenceUpdates({
    this.depthPreference,
    this.difficultyPreference,
  });

  factory PreferenceUpdates.fromJson(Map<String, dynamic> json) =>
      PreferenceUpdates(
        depthPreference: (json['depth_preference'] as num?)?.toDouble(),
        difficultyPreference:
            (json['difficulty_preference'] as num?)?.toDouble(),
      );

  final double? depthPreference;
  final double? difficultyPreference;

  Map<String, dynamic> toJson() => {
        if (depthPreference != null) 'depth_preference': depthPreference,
        if (difficultyPreference != null)
          'difficulty_preference': difficultyPreference,
      };

  @override
  String toString() =>
      'PreferenceUpdates(depthPreference: $depthPreference, difficultyPreference: $difficultyPreference)';
}
