class ScenarioPackSummary {
  const ScenarioPackSummary({
    required this.id,
    required this.name,
    required this.version,
    required this.description,
    required this.horizonDays,
    required this.nodeCount,
    this.goalType = '',
    this.author = '',
  });

  final String id;
  final String name;
  final String version;
  final String description;
  final int horizonDays;
  final int nodeCount;
  final String goalType;
  final String author;

  factory ScenarioPackSummary.fromJson(Map<String, dynamic> json) {
    return ScenarioPackSummary(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      version: json['version'] as String? ?? '',
      description: json['description'] as String? ?? '',
      horizonDays: json['horizon_days'] as int? ?? 0,
      nodeCount: json['node_count'] as int? ?? 0,
      goalType: json['goal_type'] as String? ?? '',
      author: json['author'] as String? ?? '',
    );
  }
}

class ScenarioPackDetail extends ScenarioPackSummary {
  const ScenarioPackDetail({
    required super.id,
    required super.name,
    required super.version,
    required super.description,
    required super.horizonDays,
    required super.nodeCount,
    super.goalType,
    super.author,
    this.applicabilityConditions = const [],
    this.backboneNodes = const [],
    this.defaultStrategies = const {},
  });

  final List<String> applicabilityConditions;
  final List<Map<String, dynamic>> backboneNodes;
  final Map<String, String> defaultStrategies;

  factory ScenarioPackDetail.fromJson(Map<String, dynamic> json) {
    final summary = ScenarioPackSummary.fromJson(json);
    return ScenarioPackDetail(
      id: summary.id,
      name: summary.name,
      version: summary.version,
      description: summary.description,
      horizonDays: summary.horizonDays,
      nodeCount: summary.nodeCount,
      goalType: summary.goalType,
      author: summary.author,
      applicabilityConditions: (json['applicability_conditions'] as List?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      backboneNodes: (json['backbone_nodes'] as List?)
              ?.map((e) => Map<String, dynamic>.from(e as Map))
              .toList() ??
          const [],
      defaultStrategies: (json['default_strategies'] as Map?)
              ?.map((k, v) => MapEntry(k.toString(), v.toString())) ??
          const {},
    );
  }
}

class JourneyProgress {
  const JourneyProgress({
    this.packId,
    this.packName,
    this.currentNode,
    this.currentNodeIndex = 0,
    this.totalNodes = 0,
    this.dayNumber = 0,
    this.horizonDays = 0,
    this.isOnBackbone = true,
  });

  final String? packId;
  final String? packName;
  final String? currentNode;
  final int currentNodeIndex;
  final int totalNodes;
  final int dayNumber;
  final int horizonDays;
  final bool isOnBackbone;

  bool get hasPack => packId != null && packId!.isNotEmpty;
  double get progress => totalNodes > 0 ? (currentNodeIndex + 1) / totalNodes : 0.0;

  factory JourneyProgress.fromJson(Map<String, dynamic> json) {
    return JourneyProgress(
      packId: json['pack_id'] as String?,
      packName: json['pack_name'] as String?,
      currentNode: json['current_node'] as String?,
      currentNodeIndex: json['current_node_index'] as int? ?? 0,
      totalNodes: json['total_nodes'] as int? ?? 0,
      dayNumber: json['day_number'] as int? ?? 0,
      horizonDays: json['horizon_days'] as int? ?? 0,
      isOnBackbone: json['is_on_backbone'] as bool? ?? true,
    );
  }
}
