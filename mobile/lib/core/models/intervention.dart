class InterventionAction {

  const InterventionAction({
    required this.id,
    required this.label,
    required this.type,
  });

  factory InterventionAction.fromJson(Map<String, dynamic> json) => InterventionAction(
      id: json['id'] as String? ?? '',
      label: json['label'] as String? ?? '',
      type: json['type'] as String? ?? 'primary',
    );
  final String id;
  final String label;
  final String type;
}

class InterventionContent {

  const InterventionContent({
    required this.renderedMessage,
    required this.intentType,
    required this.templateId,
    required this.scaffoldingLevel,
    required this.contextVariables,
  });

  factory InterventionContent.fromJson(Map<String, dynamic> json) {
    final rawContext = json['context_variables'];
    final context = <String, String>{};
    if (rawContext is Map) {
      rawContext.forEach((key, value) {
        if (key != null) {
          context[key.toString()] = value?.toString() ?? '';
        }
      });
    }
    return InterventionContent(
      renderedMessage: json['rendered_message'] as String? ?? '',
      intentType: json['intent_type'] as String? ?? '',
      templateId: json['template_id'] as String? ?? '',
      scaffoldingLevel: (json['scaffolding_level'] as num?)?.toInt() ?? 0,
      contextVariables: context,
    );
  }
  final String renderedMessage;
  final String intentType;
  final String templateId;
  final int scaffoldingLevel;
  final Map<String, String> contextVariables;
}

enum InterventionLevel {
  silent,
  toast,
  card,
  modal,
}

InterventionLevel parseInterventionLevel(String? raw) {
  switch (raw?.toLowerCase()) {
    case 'toast':
      return InterventionLevel.toast;
    case 'card':
      return InterventionLevel.card;
    case 'modal':
    case 'full_screen_modal':
      return InterventionLevel.modal;
    default:
      return InterventionLevel.silent;
  }
}

class InterventionPushMessage {

  const InterventionPushMessage({
    required this.interventionId,
    required this.level,
    required this.content,
    required this.actions,
    required this.expiresAt,
  });

  factory InterventionPushMessage.fromJson(Map<String, dynamic> json) {
    final contentJson = json['content'] as Map<String, dynamic>? ?? {};
    final actionsJson = json['actions'] as List<dynamic>? ?? [];
    final expiresAtMs = (json['expires_at'] as num?)?.toInt();

    return InterventionPushMessage(
      interventionId: json['intervention_id'] as String? ?? '',
      level: parseInterventionLevel(json['level'] as String?),
      content: InterventionContent.fromJson(contentJson),
      actions: actionsJson
          .whereType<Map<String, dynamic>>()
          .map(InterventionAction.fromJson)
          .toList(),
      expiresAt: expiresAtMs == null || expiresAtMs == 0
          ? null
          : DateTime.fromMillisecondsSinceEpoch(expiresAtMs),
    );
  }
  final String interventionId;
  final InterventionLevel level;
  final InterventionContent content;
  final List<InterventionAction> actions;
  final DateTime? expiresAt;

  bool get isExpired {
    if (expiresAt == null) return false;
    return DateTime.now().isAfter(expiresAt!);
  }

  InterventionAction? get primaryAction {
    if (actions.isEmpty) return null;
    return actions.first;
  }
}

InterventionPushMessage buildLocalFallback({
  required String title,
  required String body,
}) => InterventionPushMessage(
    interventionId: 'local-${DateTime.now().millisecondsSinceEpoch}',
    level: InterventionLevel.toast,
    content: InterventionContent(
      renderedMessage: '$title\n$body',
      intentType: 'local',
      templateId: 'local',
      scaffoldingLevel: 0,
      contextVariables: const {},
    ),
    actions: const [
      InterventionAction(id: 'start_now', label: '开始', type: 'primary'),
      InterventionAction(id: 'dismiss', label: '稍后', type: 'secondary'),
    ],
    expiresAt: DateTime.now().add(const Duration(minutes: 10)),
  );
