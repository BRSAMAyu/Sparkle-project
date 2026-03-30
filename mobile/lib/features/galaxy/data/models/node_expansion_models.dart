class NodeExpansionCandidate {
  const NodeExpansionCandidate({
    required this.candidateId,
    required this.name,
    required this.description,
    required this.importanceLevel,
    required this.relationToTrigger,
    required this.relationStrength,
    this.nameEn,
    this.keywords = const <String>[],
    this.sectorWeights = const <String, double>{},
  });

  factory NodeExpansionCandidate.fromJson(Map<String, dynamic> json) =>
      NodeExpansionCandidate(
        candidateId: json['candidate_id']?.toString() ?? '',
        name: json['name']?.toString() ?? '',
        nameEn: json['name_en']?.toString(),
        description: json['description']?.toString() ?? '',
        importanceLevel: (json['importance_level'] as num?)?.toInt() ?? 3,
        relationToTrigger: json['relation_to_trigger']?.toString() ?? 'related',
        relationStrength:
            (json['relation_strength'] as num?)?.toDouble() ?? 0.7,
        keywords: ((json['keywords'] as List<dynamic>?) ?? const <dynamic>[])
            .map((item) => item.toString())
            .toList(growable: false),
        sectorWeights: ((json['sector_weights'] as Map<String, dynamic>?) ??
                const <String, dynamic>{})
            .map(
          (key, value) => MapEntry(
            key,
            (value as num?)?.toDouble() ?? 0,
          ),
        ),
      );

  final String candidateId;
  final String name;
  final String? nameEn;
  final String description;
  final int importanceLevel;
  final String relationToTrigger;
  final double relationStrength;
  final List<String> keywords;
  final Map<String, double> sectorWeights;

  Map<String, dynamic> toJson() => <String, dynamic>{
        'candidate_id': candidateId,
        'name': name,
        'name_en': nameEn,
        'description': description,
        'importance_level': importanceLevel,
        'relation_to_trigger': relationToTrigger,
        'relation_strength': relationStrength,
        'keywords': keywords,
        'sector_weights': sectorWeights,
      };
}

class NodeExpansionCandidatesResponse {
  const NodeExpansionCandidatesResponse({
    required this.triggerNodeId,
    required this.promptVersion,
    required this.candidates,
  });

  factory NodeExpansionCandidatesResponse.fromJson(Map<String, dynamic> json) =>
      NodeExpansionCandidatesResponse(
        triggerNodeId: json['trigger_node_id']?.toString() ?? '',
        promptVersion: json['prompt_version']?.toString() ?? 'v1',
        candidates:
            ((json['candidates'] as List<dynamic>?) ?? const <dynamic>[])
                .whereType<Map<String, dynamic>>()
                .map(NodeExpansionCandidate.fromJson)
                .toList(growable: false),
      );

  final String triggerNodeId;
  final String promptVersion;
  final List<NodeExpansionCandidate> candidates;
}
