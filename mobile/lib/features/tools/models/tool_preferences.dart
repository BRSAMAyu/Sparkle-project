class ToolPreferences {
  factory ToolPreferences.fromJson(Map<String, dynamic> json) =>
      ToolPreferences(
        pinnedToolIds: (json['pinned_tool_ids'] as List<dynamic>? ?? const [])
            .whereType<String>()
            .toList(),
        recentToolIds: (json['recent_tool_ids'] as List<dynamic>? ?? const [])
            .whereType<String>()
            .toList(),
        isLoaded: true,
      );

  const ToolPreferences({
    required this.pinnedToolIds,
    required this.recentToolIds,
    this.isLoaded = false,
  });

  final List<String> pinnedToolIds;
  final List<String> recentToolIds;
  final bool isLoaded;

  Map<String, dynamic> toJson() => {
        'pinned_tool_ids': pinnedToolIds,
        'recent_tool_ids': recentToolIds,
      };

  ToolPreferences copyWith({
    List<String>? pinnedToolIds,
    List<String>? recentToolIds,
    bool? isLoaded,
  }) =>
      ToolPreferences(
        pinnedToolIds: pinnedToolIds ?? this.pinnedToolIds,
        recentToolIds: recentToolIds ?? this.recentToolIds,
        isLoaded: isLoaded ?? this.isLoaded,
      );
}
