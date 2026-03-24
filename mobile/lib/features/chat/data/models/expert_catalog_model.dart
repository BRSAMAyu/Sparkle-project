class ExpertCatalogMode {
  ExpertCatalogMode({
    required this.id,
    required this.label,
    required this.description,
    required this.entryChatMode,
    required this.enabled,
  });

  factory ExpertCatalogMode.fromJson(Map<String, dynamic> json) => ExpertCatalogMode(
      id: json['id'] as String? ?? '',
      label: json['label'] as String? ?? '',
      description: json['description'] as String? ?? '',
      entryChatMode: json['entry_chat_mode'] as String? ?? '',
      enabled: json['enabled'] as bool? ?? false,
    );

  final String id;
  final String label;
  final String description;
  final String entryChatMode;
  final bool enabled;
}

class ExpertCatalogExpert {
  ExpertCatalogExpert({
    required this.id,
    required this.displayName,
    required this.description,
    required this.tags,
    required this.entryChatMode,
    required this.enabled,
    required this.source,
    required this.official,
    this.modelTier,
    this.specificModel,
    this.modelPolicy,
  });

  factory ExpertCatalogExpert.fromJson(Map<String, dynamic> json) {
    final tagsRaw = json['tags'];
    return ExpertCatalogExpert(
      id: json['id'] as String? ?? '',
      displayName: json['display_name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      tags: tagsRaw is List ? tagsRaw.map((e) => '$e').toList() : const [],
      entryChatMode: json['entry_chat_mode'] as String? ?? '',
      enabled: json['enabled'] as bool? ?? false,
      source: json['source'] as String? ?? 'official',
      official: json['official'] as bool? ?? false,
      modelTier: json['model_tier'] as String?,
      specificModel: json['specific_model'] as String?,
      modelPolicy: json['model_policy'] is Map<String, dynamic>
          ? Map<String, dynamic>.from(json['model_policy'] as Map<String, dynamic>)
          : null,
    );
  }

  final String id;
  final String displayName;
  final String description;
  final List<String> tags;
  final String entryChatMode;
  final bool enabled;
  final String source;
  final bool official;
  final String? modelTier;
  final String? specificModel;
  final Map<String, dynamic>? modelPolicy;
}

class ExpertCatalogTeam {
  ExpertCatalogTeam({
    required this.id,
    required this.name,
    required this.description,
    required this.collaborationMode,
    required this.expertIds,
    required this.answerExpertIds,
    required this.enabled,
    required this.source,
  });

  factory ExpertCatalogTeam.fromJson(Map<String, dynamic> json) {
    final expertIdsRaw = json['expert_ids'];
    final answerExpertIdsRaw = json['answer_expert_ids'];
    return ExpertCatalogTeam(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      collaborationMode: json['collaboration_mode'] as String? ?? 'auto',
      expertIds: expertIdsRaw is List
          ? expertIdsRaw.map((e) => '$e').toList()
          : const [],
      answerExpertIds: answerExpertIdsRaw is List
          ? answerExpertIdsRaw.map((e) => '$e').toList()
          : const [],
      enabled: json['enabled'] as bool? ?? false,
      source: json['source'] as String? ?? 'custom',
    );
  }

  final String id;
  final String name;
  final String description;
  final String collaborationMode;
  final List<String> expertIds;
  final List<String> answerExpertIds;
  final bool enabled;
  final String source;
}

class ModelOption {
  ModelOption({
    required this.key,
    required this.provider,
    required this.modelName,
    required this.tier,
  });

  factory ModelOption.fromJson(Map<String, dynamic> json) => ModelOption(
        key: json['key'] as String? ?? '',
        provider: json['provider'] as String? ?? '',
        modelName: json['model_name'] as String? ?? '',
        tier: json['tier'] as String? ?? '',
      );

  final String key;
  final String provider;
  final String modelName;
  final String tier;
}

class MultiAgentCatalog {
  MultiAgentCatalog({
    required this.modes,
    required this.experts,
    required this.customExperts,
    required this.customTeams,
    required this.modelOptions,
  });

  factory MultiAgentCatalog.fromJson(Map<String, dynamic> json) {
    final modesRaw = json['modes'];
    final expertsRaw = json['experts'];
    final customExpertsRaw = json['custom_experts'];
    final customTeamsRaw = json['custom_teams'];
    final modelOptionsRaw = json['model_options'];
    return MultiAgentCatalog(
      modes: modesRaw is List
          ? modesRaw
              .whereType<Map<String, dynamic>>()
              .map(ExpertCatalogMode.fromJson)
              .toList()
          : const [],
      experts: expertsRaw is List
          ? expertsRaw
              .whereType<Map<String, dynamic>>()
              .map(ExpertCatalogExpert.fromJson)
              .toList()
          : const [],
      customExperts: customExpertsRaw is List
          ? customExpertsRaw
              .whereType<Map<String, dynamic>>()
              .map(ExpertCatalogExpert.fromJson)
              .toList()
          : const [],
      customTeams: customTeamsRaw is List
          ? customTeamsRaw
              .whereType<Map<String, dynamic>>()
              .map(ExpertCatalogTeam.fromJson)
              .toList()
          : const [],
      modelOptions: modelOptionsRaw is List
          ? modelOptionsRaw
              .whereType<Map<String, dynamic>>()
              .map(ModelOption.fromJson)
              .toList()
          : const [],
    );
  }

  final List<ExpertCatalogMode> modes;
  final List<ExpertCatalogExpert> experts;
  final List<ExpertCatalogExpert> customExperts;
  final List<ExpertCatalogTeam> customTeams;
  final List<ModelOption> modelOptions;
}
