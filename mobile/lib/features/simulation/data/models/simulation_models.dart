class SimulationParticipantModel {
  const SimulationParticipantModel({
    required this.name,
    required this.roleHint,
    required this.persona,
    this.stance,
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
        stance: json['stance']?.toString(),
        source: json['source']?.toString(),
        sourceNodeName: json['source_node_name']?.toString(),
        contextAnchor: json['context_anchor']?.toString(),
      );

  final String name;
  final String roleHint;
  final Map<String, dynamic> persona;
  final String? stance;
  final String? source;
  final String? sourceNodeName;
  final String? contextAnchor;
}

class SimulationSeedModel {
  const SimulationSeedModel({
    required this.topic,
    required this.context,
    required this.tensionPoint,
    required this.sourceType,
    required this.sourceIds,
    required this.relevanceScore,
    required this.suggestedScenario,
    required this.suggestedExperts,
  });

  factory SimulationSeedModel.fromJson(Map<String, dynamic> json) =>
      SimulationSeedModel(
        topic: json['topic']?.toString() ?? '',
        context: json['context']?.toString() ?? '',
        tensionPoint: json['tension_point']?.toString() ?? '',
        sourceType: json['source_type']?.toString() ?? '',
        sourceIds: (json['source_ids'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        relevanceScore: (json['relevance_score'] as num?)?.toDouble() ?? 0,
        suggestedScenario: json['suggested_scenario']?.toString() ?? '',
        suggestedExperts:
            (json['suggested_experts'] as List<dynamic>? ?? const [])
                .map((item) => item.toString())
                .toList(),
      );

  final String topic;
  final String context;
  final String tensionPoint;
  final String sourceType;
  final List<String> sourceIds;
  final double relevanceScore;
  final String suggestedScenario;
  final List<String> suggestedExperts;
}

class SimulationRoundModel {
  const SimulationRoundModel({
    required this.round,
    required this.speaker,
    required this.message,
    this.replyToSpeaker,
    this.turnGoal,
    this.speakerType,
  });

  factory SimulationRoundModel.fromJson(Map<String, dynamic> json) =>
      SimulationRoundModel(
        round: (json['round'] as num?)?.toInt() ?? 0,
        speaker: json['speaker']?.toString() ?? '',
        message: json['message']?.toString() ?? '',
        replyToSpeaker: json['reply_to_speaker']?.toString(),
        turnGoal: json['turn_goal']?.toString(),
        speakerType: json['speaker_type']?.toString(),
      );

  final int round;
  final String speaker;
  final String message;
  final String? replyToSpeaker;
  final String? turnGoal;
  final String? speakerType;
}

class SimulationInteractionModel {
  const SimulationInteractionModel({
    required this.id,
    required this.interactionType,
    required this.prompt,
    this.suggestedReplies = const [],
    this.options = const [],
    this.targetRound = 0,
    this.status,
  });

  factory SimulationInteractionModel.fromJson(Map<String, dynamic> json) =>
      SimulationInteractionModel(
        id: json['id']?.toString() ?? '',
        interactionType: json['interaction_type']?.toString() ?? 'choice',
        prompt: json['prompt']?.toString() ?? '',
        suggestedReplies:
            (json['suggested_replies'] as List<dynamic>? ?? const [])
                .map((item) => item.toString())
                .toList(),
        options: (json['options'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        targetRound: (json['target_round'] as num?)?.toInt() ?? 0,
        status: json['status']?.toString(),
      );

  final String id;
  final String interactionType;
  final String prompt;
  final List<String> suggestedReplies;
  final List<String> options;
  final int targetRound;
  final String? status;
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
    this.interactionPrompt,
    this.suggestedReplies = const [],
    this.interactionType,
    this.interactionOptions = const [],
    this.plannedRoundCount = 0,
    this.pendingInteraction,
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
        interactionPrompt: json['interaction_prompt']?.toString(),
        suggestedReplies:
            (json['suggested_replies'] as List<dynamic>? ?? const [])
                .map((item) => item.toString())
                .toList(),
        interactionType: json['interaction_type']?.toString(),
        interactionOptions:
            (json['interaction_options'] as List<dynamic>? ?? const [])
                .map((item) => item.toString())
                .toList(),
        plannedRoundCount: (json['planned_round_count'] as num?)?.toInt() ?? 0,
        pendingInteraction: json['pending_interaction'] is Map<String, dynamic>
            ? SimulationInteractionModel.fromJson(
                json['pending_interaction'] as Map<String, dynamic>,
              )
            : null,
      );

  final String id;
  final String scenarioKey;
  final String state;
  final String topic;
  final List<SimulationParticipantModel> participants;
  final List<SimulationRoundModel> rounds;
  final String insightSummary;
  final String? interactionPrompt;
  final List<String> suggestedReplies;
  final String? interactionType;
  final List<String> interactionOptions;
  final int plannedRoundCount;
  final SimulationInteractionModel? pendingInteraction;

  SimulationSessionModel copyWith({
    String? id,
    String? scenarioKey,
    String? state,
    String? topic,
    List<SimulationParticipantModel>? participants,
    List<SimulationRoundModel>? rounds,
    String? insightSummary,
    String? interactionPrompt,
    List<String>? suggestedReplies,
    String? interactionType,
    List<String>? interactionOptions,
    int? plannedRoundCount,
    SimulationInteractionModel? pendingInteraction,
  }) =>
      SimulationSessionModel(
        id: id ?? this.id,
        scenarioKey: scenarioKey ?? this.scenarioKey,
        state: state ?? this.state,
        topic: topic ?? this.topic,
        participants: participants ?? this.participants,
        rounds: rounds ?? this.rounds,
        insightSummary: insightSummary ?? this.insightSummary,
        interactionPrompt: interactionPrompt ?? this.interactionPrompt,
        suggestedReplies: suggestedReplies ?? this.suggestedReplies,
        interactionType: interactionType ?? this.interactionType,
        interactionOptions: interactionOptions ?? this.interactionOptions,
        plannedRoundCount: plannedRoundCount ?? this.plannedRoundCount,
        pendingInteraction: pendingInteraction ?? this.pendingInteraction,
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
    this.interactionPrompt,
    this.suggestedReplies = const [],
    this.interaction,
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
        interactionPrompt: json['interaction_prompt']?.toString(),
        suggestedReplies:
            (json['suggested_replies'] as List<dynamic>? ?? const [])
                .map((item) => item.toString())
                .toList(),
        interaction: json['interaction'] is Map<String, dynamic>
            ? SimulationInteractionModel.fromJson(
                json['interaction'] as Map<String, dynamic>,
              )
            : null,
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
  final String? interactionPrompt;
  final List<String> suggestedReplies;
  final SimulationInteractionModel? interaction;
}
