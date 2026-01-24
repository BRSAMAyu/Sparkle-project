/// Intent Entity
///
/// Internal entity class for intent data
class IntentEntity {
  const IntentEntity({
    required this.type,
    required this.confidence,
    required this.content,
    this.agentRole,
    this.entities = const {},
  });

  final String type;
  final double confidence;
  final String content;
  final String? agentRole;
  final Map<String, dynamic> entities;
}
