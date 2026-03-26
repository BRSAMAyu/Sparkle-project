class SimulationParticipantModel {
  const SimulationParticipantModel({
    required this.name,
    required this.roleHint,
    required this.persona,
    this.source,
    this.sourceNodeName,
    this.contextAnchor,
  });

  factory SimulationParticipantModel.fromJson(Map<String, dynamic> json) =>
      SimulationParticipantModel(
        name: json['name']?.toString() ?? '',
        roleHint: json['role_hint']?.toString() ?? '',
        persona: Map<String, dynamic>.from(
          json['persona'] as Map<String, dynamic>? ?? const {},
        ),
        source: json['source']?.toString(),
        sourceNodeName: json['source_node_name']?.toString(),
        contextAnchor: json['context_anchor']?.toString(),
      );

  final String name;
  final String roleHint;
  final Map<String, dynamic> persona;
  final String? source;
  final String? sourceNodeName;
  final String? contextAnchor;
}

class SimulationRoundModel {
  const SimulationRoundModel({
    required this.round,
    required this.speaker,
    required this.message,
  });

  factory SimulationRoundModel.fromJson(Map<String, dynamic> json) =>
      SimulationRoundModel(
        round: (json['round'] as num?)?.toInt() ?? 0,
        speaker: json['speaker']?.toString() ?? '',
        message: json['message']?.toString() ?? '',
      );

  final int round;
  final String speaker;
  final String message;
}

class SimulationSessionModel {
  const SimulationSessionModel({
    required this.id,
    required this.scenarioKey,
    required this.state,
    required this.topic,
    required this.participants,
    required this.rounds,
    required this.insightSummary,
  });

  factory SimulationSessionModel.fromJson(Map<String, dynamic> json) =>
      SimulationSessionModel(
        id: json['id']?.toString() ?? '',
        scenarioKey: json['scenario_key']?.toString() ?? '',
        state: json['state']?.toString() ?? '',
        topic: json['topic']?.toString() ?? '',
        participants: (json['participants'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(SimulationParticipantModel.fromJson)
            .toList(),
        rounds: (json['rounds'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(SimulationRoundModel.fromJson)
            .toList(),
        insightSummary: json['insight_summary']?.toString() ?? '',
      );

  final String id;
  final String scenarioKey;
  final String state;
  final String topic;
  final List<SimulationParticipantModel> participants;
  final List<SimulationRoundModel> rounds;
  final String insightSummary;

  SimulationSessionModel copyWith({
    String? id,
    String? scenarioKey,
    String? state,
    String? topic,
    List<SimulationParticipantModel>? participants,
    List<SimulationRoundModel>? rounds,
    String? insightSummary,
  }) =>
      SimulationSessionModel(
        id: id ?? this.id,
        scenarioKey: scenarioKey ?? this.scenarioKey,
        state: state ?? this.state,
        topic: topic ?? this.topic,
        participants: participants ?? this.participants,
        rounds: rounds ?? this.rounds,
        insightSummary: insightSummary ?? this.insightSummary,
      );
}

class SimulationStreamEventModel {
  const SimulationStreamEventModel({
    required this.event,
    this.sessionId,
    this.state,
    this.progress,
    this.participants = const [],
    this.round,
    this.rounds = const [],
    this.session,
    this.message,
  });

  factory SimulationStreamEventModel.fromJson(
    String event,
    Map<String, dynamic> json,
  ) =>
      SimulationStreamEventModel(
        event: event,
        sessionId: json['session_id']?.toString(),
        state: json['state']?.toString(),
        progress: (json['progress'] as num?)?.toDouble(),
        participants: (json['participants'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(SimulationParticipantModel.fromJson)
            .toList(),
        round: json['round'] is Map<String, dynamic>
            ? SimulationRoundModel.fromJson(
                json['round'] as Map<String, dynamic>,
              )
            : null,
        rounds: (json['rounds'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(SimulationRoundModel.fromJson)
            .toList(),
        session: json['session'] is Map<String, dynamic>
            ? SimulationSessionModel.fromJson(
                json['session'] as Map<String, dynamic>,
              )
            : null,
        message: json['message']?.toString(),
      );

  final String event;
  final String? sessionId;
  final String? state;
  final double? progress;
  final List<SimulationParticipantModel> participants;
  final SimulationRoundModel? round;
  final List<SimulationRoundModel> rounds;
  final SimulationSessionModel? session;
  final String? message;
}
