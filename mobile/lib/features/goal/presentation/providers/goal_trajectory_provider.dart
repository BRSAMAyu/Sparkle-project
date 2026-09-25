import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';

/// J-08 · Goal Trajectory —— 「想法 → 成果」轨迹读面。
///
/// 数据源 = 后端 `GET /journey/trajectory?goal_id=`（goal_trajectory_service
/// 只读投影）：action → artifact/outcome → goal milestone → reflection →
/// experience candidate → Galaxy 全环真实数据。本 provider 只做形状解析，
/// 不重建任何真源；星图侧（GalaxyNodeModel.outcomeEvidenceIds）与本面读
/// 同一批 outcome id（同一成果两面同源）。
final goalTrajectoryProvider =
    FutureProvider.family<GoalTrajectoryData, String>((ref, goalId) async {
  final response = await ref
      .read(apiClientProvider)
      .get<dynamic>('/journey/trajectory', queryParameters: {'goal_id': goalId});
  final payload = _asMap(response.data);
  if (payload == null) {
    throw const FormatException('Goal trajectory response was not a map');
  }
  return GoalTrajectoryData.fromJson(payload);
});

@immutable
class GoalTrajectoryData {
  const GoalTrajectoryData({
    required this.version,
    required this.idea,
    required this.milestones,
    required this.outcomes,
    required this.artifacts,
    required this.reflections,
    required this.experienceCandidates,
    required this.galaxy,
    required this.valueSummary,
  });

  factory GoalTrajectoryData.fromJson(Map<String, dynamic> json) =>
      GoalTrajectoryData(
        version: _asString(json['version'], fallback: 'goal_trajectory.v1'),
        idea: GoalTrajectoryIdea.fromJson(_asMap(json['idea']) ?? const {}),
        milestones: _asList(json['milestones'])
            .map(_asMap)
            .whereType<Map<String, dynamic>>()
            .map(GoalTrajectoryMilestone.fromJson)
            .toList(growable: false),
        outcomes: _asList(json['outcomes'])
            .map(_asMap)
            .whereType<Map<String, dynamic>>()
            .map(GoalTrajectoryOutcome.fromJson)
            .toList(growable: false),
        artifacts: _asList(json['artifacts'])
            .map(_asMap)
            .whereType<Map<String, dynamic>>()
            .map(GoalTrajectoryArtifact.fromJson)
            .toList(growable: false),
        reflections: _asList(json['reflections'])
            .map(_asMap)
            .whereType<Map<String, dynamic>>()
            .map(GoalTrajectoryReflection.fromJson)
            .toList(growable: false),
        experienceCandidates: _asList(json['experience_candidates'])
            .map(_asMap)
            .whereType<Map<String, dynamic>>()
            .map(GoalTrajectoryExperienceCandidate.fromJson)
            .toList(growable: false),
        galaxy: _asList(json['galaxy'])
            .map(_asMap)
            .whereType<Map<String, dynamic>>()
            .map(GoalTrajectoryGalaxyNode.fromJson)
            .toList(growable: false),
        valueSummary: _asMap(json['value_summary']) ?? const {},
      );

  final String version;
  final GoalTrajectoryIdea idea;
  final List<GoalTrajectoryMilestone> milestones;
  final List<GoalTrajectoryOutcome> outcomes;
  final List<GoalTrajectoryArtifact> artifacts;
  final List<GoalTrajectoryReflection> reflections;
  final List<GoalTrajectoryExperienceCandidate> experienceCandidates;
  final List<GoalTrajectoryGalaxyNode> galaxy;

  /// 价值叙事计数（后端 value_summary）：证据与成果，非时长统计。
  final Map<String, dynamic> valueSummary;

  int get outcomesFormed => _asInt(valueSummary['outcomes_formed']) ?? 0;
  int get milestonesReached =>
      _asInt(valueSummary['milestones_reached']) ?? 0;
  int get milestonesTotal => _asInt(valueSummary['milestones_total']) ?? 0;
  int get reflectionsCount => _asInt(valueSummary['reflections']) ?? 0;
  int get experienceCandidatesCount =>
      _asInt(valueSummary['experience_candidates']) ?? 0;
  int get galaxyNodesLit => _asInt(valueSummary['galaxy_nodes_lit']) ?? 0;
  int get artifactsCount => _asInt(valueSummary['artifacts']) ?? 0;

  bool get hasAnyProgress =>
      outcomes.isNotEmpty ||
      milestones.any((m) => m.reached) ||
      reflections.isNotEmpty ||
      galaxy.isNotEmpty;
}

/// 想法环：目标本身（含用户建目标时的真实动机）。
@immutable
class GoalTrajectoryIdea {
  const GoalTrajectoryIdea({
    required this.goalId,
    required this.title,
    this.motivation,
    this.createdAt,
  });

  factory GoalTrajectoryIdea.fromJson(Map<String, dynamic> json) =>
      GoalTrajectoryIdea(
        goalId: _asString(json['goal_id']),
        title: _asString(json['title']),
        motivation: _asNullableString(json['motivation']),
        createdAt: _asNullableString(json['created_at']),
      );

  final String goalId;
  final String title;
  final String? motivation;
  final String? createdAt;
}

/// milestone 环：达成判定来自真实任务行终态（服务端推导，客户端不重算）。
@immutable
class GoalTrajectoryMilestone {
  const GoalTrajectoryMilestone({
    required this.title,
    required this.reached,
    this.milestoneId,
    this.taskId,
    this.outcomeId,
  });

  factory GoalTrajectoryMilestone.fromJson(Map<String, dynamic> json) =>
      GoalTrajectoryMilestone(
        milestoneId: _asNullableString(json['milestone_id']),
        title: _asString(json['title']),
        reached: json['reached'] == true,
        taskId: _asNullableString(json['task_id']),
        outcomeId: _asNullableString(json['outcome_id']),
      );

  final String? milestoneId;
  final String title;
  final bool reached;
  final String? taskId;
  final String? outcomeId;
}

/// outcome 环：账本核验后的成果面（ledger_verified = D-02 真实查询命中）。
@immutable
class GoalTrajectoryOutcome {
  const GoalTrajectoryOutcome({
    required this.outcomeId,
    required this.taskTitle,
    required this.polarity,
    required this.ledgerVerified,
    this.evidenceCount = 0,
    this.occurredAt,
  });

  factory GoalTrajectoryOutcome.fromJson(Map<String, dynamic> json) =>
      GoalTrajectoryOutcome(
        outcomeId: _asString(json['outcome_id']),
        taskTitle: _asString(json['task_title']),
        polarity: _asString(json['polarity'], fallback: 'positive'),
        ledgerVerified: json['ledger_verified'] == true,
        evidenceCount: _asInt(json['evidence_count']) ?? 0,
        occurredAt: _asNullableString(json['occurred_at']),
      );

  final String outcomeId;
  final String taskTitle;
  final String polarity;
  final bool ledgerVerified;
  final int evidenceCount;
  final String? occurredAt;

  bool get isNegative => polarity == 'negative';
}

/// artifact 环：J-06 Hybrid 旅程产物行。
@immutable
class GoalTrajectoryArtifact {
  const GoalTrajectoryArtifact({
    required this.id,
    required this.stage,
    required this.artifactKind,
    this.taskId,
    this.citationCount = 0,
  });

  factory GoalTrajectoryArtifact.fromJson(Map<String, dynamic> json) =>
      GoalTrajectoryArtifact(
        id: _asString(json['id']),
        stage: _asString(json['stage']),
        artifactKind: _asString(json['artifact_kind']),
        taskId: _asNullableString(json['task_id']),
        citationCount: _asInt(json['citation_count']) ?? 0,
      );

  final String id;
  final String stage;
  final String artifactKind;
  final String? taskId;
  final int citationCount;
}

/// reflection 环：用户真实提交的结构化反思（原样回声，零性格推断）。
@immutable
class GoalTrajectoryReflection {
  const GoalTrajectoryReflection({
    required this.feedbackId,
    required this.taskId,
    this.stuckPoint,
    this.effectiveMethod,
    this.adjustmentIntention,
    this.memoryId,
  });

  factory GoalTrajectoryReflection.fromJson(Map<String, dynamic> json) =>
      GoalTrajectoryReflection(
        feedbackId: _asString(json['feedback_id']),
        taskId: _asString(json['task_id']),
        stuckPoint: _asNullableString(json['stuck_point']),
        effectiveMethod: _asNullableString(json['effective_method']),
        adjustmentIntention: _asNullableString(json['adjustment_intention']),
        memoryId: _asNullableString(json['memory_id']),
      );

  final String feedbackId;
  final String taskId;
  final String? stuckPoint;
  final String? effectiveMethod;
  final String? adjustmentIntention;
  final String? memoryId;

  bool get hasContent =>
      (stuckPoint != null && stuckPoint!.isNotEmpty) ||
      (effectiveMethod != null && effectiveMethod!.isNotEmpty) ||
      (adjustmentIntention != null && adjustmentIntention!.isNotEmpty);
}

/// experience candidate 环：反思沉淀的真实 episodic memory 行（M-03 契约）。
@immutable
class GoalTrajectoryExperienceCandidate {
  const GoalTrajectoryExperienceCandidate({
    required this.id,
    required this.summary,
    this.occurredAt,
    this.sourceType,
    this.sourceLane,
    this.epistemicClass,
  });

  factory GoalTrajectoryExperienceCandidate.fromJson(
    Map<String, dynamic> json,
  ) =>
      GoalTrajectoryExperienceCandidate(
        id: _asString(json['id']),
        summary: _asString(json['summary']),
        occurredAt: _asNullableString(json['occurred_at']),
        sourceType: _asNullableString(json['source_type']),
        sourceLane: _asNullableString(json['source_lane']),
        epistemicClass: _asNullableString(json['epistemic_class']),
      );

  final String id;
  final String summary;
  final String? occurredAt;
  final String? sourceType;
  final String? sourceLane;
  final String? epistemicClass;
}

/// Galaxy 环：与星图面同一 provenance 行（graph_event_sources 同形状）。
@immutable
class GoalTrajectoryGalaxyNode {
  const GoalTrajectoryGalaxyNode({
    required this.nodeId,
    required this.nodeName,
    required this.mastery,
    required this.outcomeIds,
  });

  factory GoalTrajectoryGalaxyNode.fromJson(Map<String, dynamic> json) =>
      GoalTrajectoryGalaxyNode(
        nodeId: _asString(json['node_id']),
        nodeName: _asString(json['node_name']),
        mastery: (_asInt(json['mastery']) ?? 0).toDouble(),
        outcomeIds: _asList(json['outcome_ids'])
            .map((item) => item.toString())
            .toList(growable: false),
      );

  final String nodeId;
  final String nodeName;
  final double mastery;
  final List<String> outcomeIds;
}

Map<String, dynamic>? _asMap(dynamic value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  return null;
}

List<dynamic> _asList(dynamic value) => value is List ? value : const [];

String _asString(dynamic value, {String fallback = ''}) {
  final text = value?.toString().trim();
  return text == null || text.isEmpty ? fallback : text;
}

String? _asNullableString(dynamic value) {
  final text = _asString(value);
  return text.isEmpty ? null : text;
}

int? _asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}
