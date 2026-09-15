import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

enum GoalGraphNodeState {
  bottleneck,
  mastered,
  learning,
}

class GoalGraphOverlayEdge {
  const GoalGraphOverlayEdge({
    required this.fromNodeId,
    required this.toNodeId,
    required this.type,
  });

  factory GoalGraphOverlayEdge.fromJson(Map<String, dynamic> json) =>
      GoalGraphOverlayEdge(
        fromNodeId: _stringValue(json['from_node'] ?? json['fromNode']),
        toNodeId: _stringValue(json['to_node'] ?? json['toNode']),
        type: _stringValue(json['edge_type'] ?? json['type']),
      );

  final String fromNodeId;
  final String toNodeId;
  final String type;
}

class GoalGraphOverlayNode {
  const GoalGraphOverlayNode({
    required this.id,
    required this.label,
    required this.nodeType,
    required this.mastery,
    required this.isBottleneck,
    this.examWeight,
    this.difficulty,
    this.trainability,
    this.mistakes,
    this.relationship,
  });

  factory GoalGraphOverlayNode.fromJson(
    Map<String, dynamic> json, {
    String? relationship,
  }) =>
      GoalGraphOverlayNode(
        id: _stringValue(json['node_id'] ?? json['nodeId'] ?? json['id']),
        label: _stringValue(json['label'] ?? json['name']),
        nodeType: _stringValue(json['node_type'] ?? json['nodeType']),
        mastery: _doubleValue(json['mastery']).clamp(0, 1).toDouble(),
        isBottleneck: json['is_bottleneck'] == true ||
            json['isBottleneck'] == true ||
            json['bottleneck'] == true,
        examWeight: _nullableDouble(json['exam_weight'] ?? json['examWeight']),
        difficulty: _nullableDouble(json['difficulty']),
        trainability: _nullableDouble(json['trainability']),
        mistakes: _nullableInt(json['mistakes']),
        relationship: relationship,
      );

  final String id;
  final String label;
  final String nodeType;
  final double mastery;
  final bool isBottleneck;
  final double? examWeight;
  final double? difficulty;
  final double? trainability;
  final int? mistakes;
  final String? relationship;

  GoalGraphNodeState get state {
    if (isBottleneck) return GoalGraphNodeState.bottleneck;
    if (mastery >= 0.72) return GoalGraphNodeState.mastered;
    return GoalGraphNodeState.learning;
  }
}

class GoalGraphOverlayData {
  const GoalGraphOverlayData({
    required this.active,
    required this.goalId,
    required this.nodes,
    required this.edges,
    required this.bottleneckNodeId,
  });

  factory GoalGraphOverlayData.fromJson(Map<String, dynamic> json) {
    final suggestions = _relationshipByNodeId(json['focus_suggestions']);
    final rawNodes = json['nodes'];
    final nodes = rawNodes is List
        ? rawNodes
            .whereType<Map<Object?, Object?>>()
            .map(Map<String, dynamic>.from)
            .map(
              (item) => GoalGraphOverlayNode.fromJson(
                item,
                relationship: suggestions[_stringValue(
                  item['node_id'] ?? item['nodeId'] ?? item['id'],
                )],
              ),
            )
            .where((node) => node.id.isNotEmpty && node.label.isNotEmpty)
            .toList(growable: false)
        : const <GoalGraphOverlayNode>[];

    final rawEdges = json['edges'];
    final edges = rawEdges is List
        ? rawEdges
            .whereType<Map<Object?, Object?>>()
            .map(Map<String, dynamic>.from)
            .map(GoalGraphOverlayEdge.fromJson)
            .where(
              (edge) => edge.fromNodeId.isNotEmpty && edge.toNodeId.isNotEmpty,
            )
            .toList(growable: false)
        : const <GoalGraphOverlayEdge>[];

    return GoalGraphOverlayData(
      active: json['active'] == true,
      goalId: _stringValue(json['goal_id'] ?? json['goalId']),
      nodes: nodes,
      edges: edges,
      bottleneckNodeId: _optionalString(
        json['bottleneck_node_id'] ?? json['bottleneckNodeId'],
      ),
    );
  }

  final bool active;
  final String goalId;
  final List<GoalGraphOverlayNode> nodes;
  final List<GoalGraphOverlayEdge> edges;
  final String? bottleneckNodeId;

  List<GoalGraphOverlayNode> get bottleneckNodes => nodes
      .where((node) => node.state == GoalGraphNodeState.bottleneck)
      .toList(growable: false);

  List<GoalGraphOverlayNode> get masteredNodes => nodes
      .where((node) => node.state == GoalGraphNodeState.mastered)
      .toList(growable: false);

  List<GoalGraphOverlayNode> get learningNodes => nodes
      .where((node) => node.state == GoalGraphNodeState.learning)
      .toList(growable: false);
}

final goalGraphOverlayProvider =
    FutureProvider.family<GoalGraphOverlayData, String>((ref, goalId) async {
  final response = await ref
      .read(apiClientProvider)
      .get<dynamic>(ApiEndpoints.auroraSpineGoalGraph(goalId));
  final data = response.data;
  if (data is Map<String, dynamic>) {
    return GoalGraphOverlayData.fromJson(data);
  }
  if (data is Map<Object?, Object?>) {
    return GoalGraphOverlayData.fromJson(Map<String, dynamic>.from(data));
  }
  return GoalGraphOverlayData(
    active: false,
    goalId: goalId,
    nodes: const [],
    edges: const [],
    bottleneckNodeId: null,
  );
});

Map<String, String> _relationshipByNodeId(Object? raw) {
  if (raw is! List) return const {};
  final result = <String, String>{};
  for (final item in raw.whereType<Map<Object?, Object?>>()) {
    final map = Map<String, dynamic>.from(item);
    final nodeId = _stringValue(map['node_id'] ?? map['nodeId'] ?? map['id']);
    final relationship = _optionalString(
      map['reason'] ??
          map['relationship'] ??
          map['blocks'] ??
          map['task_title'] ??
          map['phase'],
    );
    if (nodeId.isNotEmpty && relationship != null) {
      result[nodeId] = relationship;
    }
  }
  return result;
}

String _stringValue(Object? value) => value?.toString().trim() ?? '';

String? _optionalString(Object? value) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? null : text;
}

double _doubleValue(Object? value) => _nullableDouble(value) ?? 0;

double? _nullableDouble(Object? value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

int? _nullableInt(Object? value) {
  if (value is int) return value;
  if (value is num) return value.round();
  if (value is String) return int.tryParse(value);
  return null;
}
