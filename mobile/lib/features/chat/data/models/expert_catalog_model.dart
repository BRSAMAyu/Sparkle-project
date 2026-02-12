class ExpertCatalogMode {
  ExpertCatalogMode({
    required this.id,
    required this.label,
    required this.description,
    required this.entryChatMode,
    required this.enabled,
    required this.rank,
    required this.tags,
  });

  factory ExpertCatalogMode.fromJson(Map<String, dynamic> json) {
    final tagsRaw = json['tags'];
    return ExpertCatalogMode(
      id: json['id'] as String? ?? '',
      label: json['label'] as String? ?? '',
      description: json['description'] as String? ?? '',
      entryChatMode: json['entry_chat_mode'] as String? ?? '',
      enabled: json['enabled'] as bool? ?? false,
      rank: (json['rank'] as num?)?.toInt() ?? 999,
      tags: tagsRaw is List ? tagsRaw.map((e) => '$e').toList() : const [],
    );
  }

  final String id;
  final String label;
  final String description;
  final String entryChatMode;
  final bool enabled;
  final int rank;
  final List<String> tags;
}

class ExpertCatalogExpert {
  ExpertCatalogExpert({
    required this.id,
    required this.displayName,
    required this.description,
    required this.tags,
    required this.entryChatMode,
    required this.recommendedScenarios,
    required this.enabled,
    required this.rank,
  });

  factory ExpertCatalogExpert.fromJson(Map<String, dynamic> json) {
    final tagsRaw = json['tags'];
    final scenariosRaw = json['recommended_scenarios'];
    return ExpertCatalogExpert(
      id: json['id'] as String? ?? '',
      displayName: json['display_name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      tags: tagsRaw is List ? tagsRaw.map((e) => '$e').toList() : const [],
      entryChatMode: json['entry_chat_mode'] as String? ?? '',
      recommendedScenarios: scenariosRaw is List
          ? scenariosRaw.map((e) => '$e').toList()
          : const [],
      enabled: json['enabled'] as bool? ?? false,
      rank: (json['rank'] as num?)?.toInt() ?? 999,
    );
  }

  final String id;
  final String displayName;
  final String description;
  final List<String> tags;
  final String entryChatMode;
  final List<String> recommendedScenarios;
  final bool enabled;
  final int rank;
}

class MultiAgentCatalog {
  MultiAgentCatalog({
    required this.modes,
    required this.experts,
  });

  factory MultiAgentCatalog.fromJson(Map<String, dynamic> json) {
    final modesRaw = json['modes'];
    final expertsRaw = json['experts'];
    final modes = modesRaw is List
        ? modesRaw
            .whereType<Map<String, dynamic>>()
            .map(ExpertCatalogMode.fromJson)
            .toList()
        : <ExpertCatalogMode>[];
    final experts = expertsRaw is List
        ? expertsRaw
            .whereType<Map<String, dynamic>>()
            .map(ExpertCatalogExpert.fromJson)
            .toList()
        : <ExpertCatalogExpert>[];

    modes.sort((a, b) => a.rank.compareTo(b.rank));
    experts.sort((a, b) => a.rank.compareTo(b.rank));

    return MultiAgentCatalog(
      modes: modes,
      experts: experts,
    );
  }

  final List<ExpertCatalogMode> modes;
  final List<ExpertCatalogExpert> experts;
}
