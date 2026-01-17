/// Candidate Action Model
///
/// Represents a predicted action suggestion from the signals pipeline.
class CandidateActionModel {
  final String id;
  final String actionType; // "break", "review", "clarify", "plan_split"
  final String title;
  final String reason;
  final double confidence;
  final String timingHint; // "now", "in_5min", "after_current_task"
  final String payloadSeed;
  final Map<String, dynamic> metadata;

  const CandidateActionModel({
    required this.id,
    required this.actionType,
    required this.title,
    required this.reason,
    required this.confidence,
    required this.timingHint,
    required this.payloadSeed,
    this.metadata = const {},
  });

  factory CandidateActionModel.fromJson(Map<String, dynamic> json) {
    return CandidateActionModel(
      id: json['id'] as String,
      actionType: json['action_type'] as String,
      title: json['title'] as String,
      reason: json['reason'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      timingHint: json['timing_hint'] as String,
      payloadSeed: json['payload_seed'] as String,
      metadata: json['metadata'] as Map<String, dynamic>? ?? {},
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'action_type': actionType,
      'title': title,
      'reason': reason,
      'confidence': confidence,
      'timing_hint': timingHint,
      'payload_seed': payloadSeed,
      'metadata': metadata,
    };
  }

  /// Get icon for action type
  String getIcon() {
    switch (actionType) {
      case 'break':
        return '☕';
      case 'review':
        return '📚';
      case 'clarify':
        return '💡';
      case 'plan_split':
        return '🎯';
      default:
        return '✨';
    }
  }

  /// Get color for action type
  int getColorValue() {
    switch (actionType) {
      case 'break':
        return 0xFF4CAF50; // Green
      case 'review':
        return 0xFF2196F3; // Blue
      case 'clarify':
        return 0xFFFF9800; // Orange
      case 'plan_split':
        return 0xFF9C27B0; // Purple
      default:
        return 0xFF757575; // Grey
    }
  }
}
