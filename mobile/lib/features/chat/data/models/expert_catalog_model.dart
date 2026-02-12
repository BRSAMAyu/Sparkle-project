class ExpertCatalogMode {
  ExpertCatalogMode({
    required this.id,
    required this.label,
    required this.description,
    required this.entryChatMode,
    required this.enabled,
  });

  factory ExpertCatalogMode.fromJson(Map<String, dynamic> json) {
    return ExpertCatalogMode(
      id: json['id'] as String? ?? '',
      label: json['label'] as String? ?? '',
      description: json['description'] as String? ?? '',
      entryChatMode: json['entry_chat_mode'] as String? ?? '',
      enabled: json['enabled'] as bool? ?? false,
    );
  }

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
    );
  }

  final String id;
  final String displayName;
  final String description;
  final List<String> tags;
  final String entryChatMode;
  final bool enabled;
}

class MultiAgentCatalog {
  MultiAgentCatalog({
    required this.modes,
    required this.experts,
  });

  factory MultiAgentCatalog.fromJson(Map<String, dynamic> json) {
    final modesRaw = json['modes'];
    final expertsRaw = json['experts'];
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
    );
  }

  final List<ExpertCatalogMode> modes;
  final List<ExpertCatalogExpert> experts;
}
