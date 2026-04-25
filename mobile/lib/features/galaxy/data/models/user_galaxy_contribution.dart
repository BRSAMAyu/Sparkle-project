class GalaxyContributionNodeItem {
  const GalaxyContributionNodeItem({
    required this.nodeId,
    required this.nodeName,
    this.reason,
    this.masteryDelta = 0,
    this.updatedAt,
  });

  factory GalaxyContributionNodeItem.fromJson(Map<String, dynamic> json) =>
      GalaxyContributionNodeItem(
        nodeId: (json['node_id'] ?? '').toString(),
        nodeName: (json['node_name'] ?? '未命名节点').toString(),
        reason: json['reason']?.toString(),
        masteryDelta: (json['mastery_delta'] as num?)?.toInt() ?? 0,
        updatedAt: json['updated_at'] == null
            ? null
            : DateTime.tryParse(json['updated_at'].toString()),
      );

  final String nodeId;
  final String nodeName;
  final String? reason;
  final int masteryDelta;
  final DateTime? updatedAt;

  Map<String, dynamic> toJson() => {
        'node_id': nodeId,
        'node_name': nodeName,
        'reason': reason,
        'mastery_delta': masteryDelta,
        'updated_at': updatedAt?.toIso8601String(),
      };
}

class UserGalaxyContribution {
  const UserGalaxyContribution({
    this.firstActivationCount = 0,
    this.errorRepairedCount = 0,
    this.conversationUpdatedCount = 0,
    this.firstActivatedNodes = const <GalaxyContributionNodeItem>[],
    this.errorRepairedNodes = const <GalaxyContributionNodeItem>[],
    this.conversationUpdatedNodes = const <GalaxyContributionNodeItem>[],
  });

  factory UserGalaxyContribution.fromJson(Map<String, dynamic> json) =>
      UserGalaxyContribution(
        firstActivationCount:
            (json['first_activation_count'] as num?)?.toInt() ?? 0,
        errorRepairedCount:
            (json['error_repaired_count'] as num?)?.toInt() ?? 0,
        conversationUpdatedCount:
            (json['conversation_updated_count'] as num?)?.toInt() ?? 0,
        firstActivatedNodes:
            (json['first_activated_nodes'] as List<dynamic>? ?? const [])
                .whereType<Map<Object?, Object?>>()
                .map(
                  (item) => GalaxyContributionNodeItem.fromJson(
                    Map<String, dynamic>.from(item),
                  ),
                )
                .toList(growable: false),
        errorRepairedNodes:
            (json['error_repaired_nodes'] as List<dynamic>? ?? const [])
                .whereType<Map<Object?, Object?>>()
                .map(
                  (item) => GalaxyContributionNodeItem.fromJson(
                    Map<String, dynamic>.from(item),
                  ),
                )
                .toList(growable: false),
        conversationUpdatedNodes:
            (json['conversation_updated_nodes'] as List<dynamic>? ?? const [])
                .whereType<Map<Object?, Object?>>()
                .map(
                  (item) => GalaxyContributionNodeItem.fromJson(
                    Map<String, dynamic>.from(item),
                  ),
                )
                .toList(growable: false),
      );

  static const empty = UserGalaxyContribution();

  final int firstActivationCount;
  final int errorRepairedCount;
  final int conversationUpdatedCount;
  final List<GalaxyContributionNodeItem> firstActivatedNodes;
  final List<GalaxyContributionNodeItem> errorRepairedNodes;
  final List<GalaxyContributionNodeItem> conversationUpdatedNodes;

  bool get isEmpty =>
      firstActivationCount == 0 &&
      errorRepairedCount == 0 &&
      conversationUpdatedCount == 0;

  Map<String, dynamic> toJson() => {
        'first_activation_count': firstActivationCount,
        'error_repaired_count': errorRepairedCount,
        'conversation_updated_count': conversationUpdatedCount,
        'first_activated_nodes':
            firstActivatedNodes.map((item) => item.toJson()).toList(),
        'error_repaired_nodes':
            errorRepairedNodes.map((item) => item.toJson()).toList(),
        'conversation_updated_nodes':
            conversationUpdatedNodes.map((item) => item.toJson()).toList(),
      };
}
