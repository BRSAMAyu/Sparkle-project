class TheaterGraphNode {
  const TheaterGraphNode({
    required this.id,
    required this.name,
    required this.description,
    required this.currentMastery,
    required this.predictedMastery,
    required this.riskLevel,
  });

  factory TheaterGraphNode.fromJson(Map<String, dynamic> json) =>
      TheaterGraphNode(
        id: json['id']?.toString() ?? '',
        name: json['name']?.toString() ?? '',
        description: json['description']?.toString() ?? '',
        currentMastery: (json['current_mastery'] as num?)?.toDouble() ?? 0,
        predictedMastery: (json['predicted_mastery'] as num?)?.toDouble() ?? 0,
        riskLevel: json['risk_level']?.toString() ?? 'low',
      );

  final String id;
  final String name;
  final String description;
  final double currentMastery;
  final double predictedMastery;
  final String riskLevel;
}

class TheaterGraphEdge {
  const TheaterGraphEdge({
    required this.id,
    required this.sourceId,
    required this.targetId,
    required this.relationType,
    required this.strength,
  });

  factory TheaterGraphEdge.fromJson(Map<String, dynamic> json) =>
      TheaterGraphEdge(
        id: json['id']?.toString() ?? '',
        sourceId: json['source_id']?.toString() ?? '',
        targetId: json['target_id']?.toString() ?? '',
        relationType: json['relation_type']?.toString() ?? 'related',
        strength: (json['strength'] as num?)?.toDouble() ?? 0.5,
      );

  final String id;
  final String sourceId;
  final String targetId;
  final String relationType;
  final double strength;
}

class TheaterDiscussionTurn {
  const TheaterDiscussionTurn({
    required this.turnIndex,
    required this.agentId,
    required this.displayName,
    required this.turnType,
    required this.content,
    required this.relatedNodeIds,
  });

  factory TheaterDiscussionTurn.fromJson(Map<String, dynamic> json) =>
      TheaterDiscussionTurn(
        turnIndex: (json['turn_index'] as num?)?.toInt() ?? 0,
        agentId: json['agent_id']?.toString() ?? '',
        displayName: json['display_name']?.toString() ?? '',
        turnType: json['turn_type']?.toString() ?? 'analysis',
        content: json['content']?.toString() ?? '',
        relatedNodeIds: (json['related_node_ids'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
      );

  final int turnIndex;
  final String agentId;
  final String displayName;
  final String turnType;
  final String content;
  final List<String> relatedNodeIds;
}

class TheaterPathStep {
  const TheaterPathStep({
    required this.index,
    required this.nodeId,
    required this.nodeName,
    required this.rationale,
    required this.currentMastery,
    required this.predictedMastery,
    required this.riskLevel,
    required this.estimatedMinutes,
    required this.dayLabel,
    this.checkpointLabel,
  });

  factory TheaterPathStep.fromJson(Map<String, dynamic> json) =>
      TheaterPathStep(
        index: (json['index'] as num?)?.toInt() ?? 0,
        nodeId: json['node_id']?.toString() ?? '',
        nodeName: json['node_name']?.toString() ?? '',
        rationale: json['rationale']?.toString() ?? '',
        currentMastery: (json['current_mastery'] as num?)?.toDouble() ?? 0,
        predictedMastery: (json['predicted_mastery'] as num?)?.toDouble() ?? 0,
        riskLevel: json['risk_level']?.toString() ?? 'low',
        estimatedMinutes: (json['estimated_minutes'] as num?)?.toInt() ?? 25,
        dayLabel: json['day_label']?.toString() ?? '',
        checkpointLabel: json['checkpoint_label']?.toString(),
      );

  final int index;
  final String nodeId;
  final String nodeName;
  final String rationale;
  final double currentMastery;
  final double predictedMastery;
  final String riskLevel;
  final int estimatedMinutes;
  final String dayLabel;
  final String? checkpointLabel;
}

class TheaterTaskBrief {
  const TheaterTaskBrief({
    required this.title,
    required this.nodeId,
    required this.estimatedMinutes,
    required this.dayLabel,
    this.checkpointLabel,
    this.summary,
    this.taskId,
    this.dueDate,
    this.taskType,
  });

  factory TheaterTaskBrief.fromJson(Map<String, dynamic> json) =>
      TheaterTaskBrief(
        title: json['title']?.toString() ?? '',
        nodeId: json['node_id']?.toString() ?? '',
        estimatedMinutes: (json['estimated_minutes'] as num?)?.toInt() ??
            ((json['estimated_minutes'] as num?)?.toInt() ?? 25),
        dayLabel: json['day_label']?.toString() ?? '',
        checkpointLabel: json['checkpoint_label']?.toString(),
        summary: json['summary']?.toString(),
        taskId: json['task_id']?.toString(),
        dueDate: json['due_date']?.toString(),
        taskType: json['task_type']?.toString(),
      );

  final String title;
  final String nodeId;
  final int estimatedMinutes;
  final String dayLabel;
  final String? checkpointLabel;
  final String? summary;
  final String? taskId;
  final String? dueDate;
  final String? taskType;
}

class TheaterPathOption {
  const TheaterPathOption({
    required this.id,
    required this.title,
    required this.summary,
    required this.strategyType,
    required this.expertIds,
    required this.estimatedCompletionRate,
    required this.estimatedMastery,
    required this.dailyMinutes,
    required this.risks,
    required this.steps,
    this.routeScore = 0,
    this.checkpointDays = const [],
    this.weekOneTasks = const [],
  });

  factory TheaterPathOption.fromJson(Map<String, dynamic> json) =>
      TheaterPathOption(
        id: json['id']?.toString() ?? '',
        title: json['title']?.toString() ?? '',
        summary: json['summary']?.toString() ?? '',
        strategyType: json['strategy_type']?.toString() ?? '',
        expertIds: (json['expert_ids'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        estimatedCompletionRate:
            (json['estimated_completion_rate'] as num?)?.toDouble() ?? 0,
        estimatedMastery: (json['estimated_mastery'] as num?)?.toDouble() ?? 0,
        dailyMinutes: (json['daily_minutes'] as num?)?.toInt() ?? 40,
        risks: (json['risks'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        routeScore: (json['route_score'] as num?)?.toDouble() ?? 0,
        checkpointDays: (json['checkpoint_days'] as List<dynamic>? ?? const [])
            .map((item) => (item as num?)?.toInt() ?? 0)
            .where((item) => item > 0)
            .toList(),
        weekOneTasks: (json['week_one_tasks'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(TheaterTaskBrief.fromJson)
            .toList(),
        steps: (json['steps'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(TheaterPathStep.fromJson)
            .toList(),
      );

  final String id;
  final String title;
  final String summary;
  final String strategyType;
  final List<String> expertIds;
  final double estimatedCompletionRate;
  final double estimatedMastery;
  final int dailyMinutes;
  final List<String> risks;
  final List<TheaterPathStep> steps;
  final double routeScore;
  final List<int> checkpointDays;
  final List<TheaterTaskBrief> weekOneTasks;
}

class TheaterTimelineFrame {
  const TheaterTimelineFrame({
    required this.index,
    required this.label,
    required this.dayIndex,
    required this.routeId,
    required this.focusNodeIds,
    required this.discussionTurnIndex,
    this.projectedMastery = 0,
    this.projectedCompletionRate = 0,
    this.activeStepNodeId,
    this.activeStepTitle,
    this.compareLabel,
    this.branchType,
  });

  factory TheaterTimelineFrame.fromJson(Map<String, dynamic> json) =>
      TheaterTimelineFrame(
        index: (json['index'] as num?)?.toInt() ?? 0,
        label: json['label']?.toString() ?? '',
        dayIndex: (json['day_index'] as num?)?.toInt() ?? 0,
        routeId: json['route_id']?.toString() ?? '',
        focusNodeIds: (json['focus_node_ids'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        discussionTurnIndex:
            (json['discussion_turn_index'] as num?)?.toInt() ?? 0,
        projectedMastery: (json['projected_mastery'] as num?)?.toDouble() ?? 0,
        projectedCompletionRate:
            (json['projected_completion_rate'] as num?)?.toDouble() ?? 0,
        activeStepNodeId: json['active_step_node_id']?.toString(),
        activeStepTitle: json['active_step_title']?.toString(),
        compareLabel: json['compare_label']?.toString(),
        branchType: json['branch_type']?.toString(),
      );

  final int index;
  final String label;
  final int dayIndex;
  final String routeId;
  final List<String> focusNodeIds;
  final int discussionTurnIndex;
  final double projectedMastery;
  final double projectedCompletionRate;
  final String? activeStepNodeId;
  final String? activeStepTitle;
  final String? compareLabel;
  final String? branchType;
}

class TheaterAccuracyTracking {
  const TheaterAccuracyTracking({
    required this.predictionId,
    required this.status,
    required this.dueOn,
    required this.summaryHint,
    this.recordedAt,
  });

  factory TheaterAccuracyTracking.fromJson(Map<String, dynamic> json) =>
      TheaterAccuracyTracking(
        predictionId: json['prediction_id']?.toString() ?? '',
        status: json['status']?.toString() ?? 'pending_feedback',
        dueOn: json['due_on']?.toString() ?? '',
        summaryHint: json['summary_hint']?.toString() ?? '',
        recordedAt: json['recorded_at']?.toString(),
      );

  final String predictionId;
  final String status;
  final String dueOn;
  final String summaryHint;
  final String? recordedAt;
}

class TheaterPrediction {
  const TheaterPrediction({
    required this.predictionId,
    required this.topic,
    required this.targetNodeId,
    required this.targetName,
    required this.horizonDays,
    required this.paths,
    required this.discussionTurns,
    required this.graphNodes,
    required this.graphEdges,
    required this.timeline,
    this.recommendedRouteId = '',
    this.targetResolutionMode = '',
    this.accuracyTracking,
  });

  factory TheaterPrediction.fromJson(Map<String, dynamic> json) {
    final graph = json['graph'] as Map<String, dynamic>? ?? const {};
    return TheaterPrediction(
      predictionId: json['prediction_id']?.toString() ?? '',
      topic: json['topic']?.toString() ?? '',
      targetNodeId: json['target_node_id']?.toString() ?? '',
      targetName: json['target_name']?.toString() ?? '',
      horizonDays: (json['horizon_days'] as num?)?.toInt() ?? 14,
      paths: (json['paths'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(TheaterPathOption.fromJson)
          .toList(),
      discussionTurns: (json['discussion_turns'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(TheaterDiscussionTurn.fromJson)
          .toList(),
      graphNodes: (graph['nodes'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(TheaterGraphNode.fromJson)
          .toList(),
      graphEdges: (graph['edges'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(TheaterGraphEdge.fromJson)
          .toList(),
      timeline: (json['timeline'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(TheaterTimelineFrame.fromJson)
          .toList(),
      recommendedRouteId: json['recommended_route_id']?.toString() ?? '',
      targetResolutionMode: json['target_resolution_mode']?.toString() ??
          (json['routing_notes'] is Map<String, dynamic>
              ? (json['routing_notes']
                          as Map<String, dynamic>)['target_resolution_mode']
                      ?.toString() ??
                  ''
              : ''),
      accuracyTracking: json['accuracy_tracking'] is Map<String, dynamic>
          ? TheaterAccuracyTracking.fromJson(
              json['accuracy_tracking'] as Map<String, dynamic>,
            )
          : null,
    );
  }

  final String predictionId;
  final String topic;
  final String targetNodeId;
  final String targetName;
  final int horizonDays;
  final List<TheaterPathOption> paths;
  final List<TheaterDiscussionTurn> discussionTurns;
  final List<TheaterGraphNode> graphNodes;
  final List<TheaterGraphEdge> graphEdges;
  final List<TheaterTimelineFrame> timeline;
  final String recommendedRouteId;
  final String targetResolutionMode;
  final TheaterAccuracyTracking? accuracyTracking;
}

class TheaterWhatIfResult {
  const TheaterWhatIfResult({
    required this.skipNodeName,
    required this.predictedMastery,
    required this.predictedCompletionRate,
    required this.deltaMastery,
    required this.deltaCompletionRate,
    required this.consequences,
    required this.suggestion,
    this.skipNodeIds = const [],
    this.skipNodeNames = const [],
    this.originalMastery = 0,
    this.originalCompletionRate = 0,
    this.remainingPath = const [],
    this.branchTimeline = const [],
    this.branchLabel,
    this.branchFocusNodeIds = const [],
  });

  factory TheaterWhatIfResult.fromJson(Map<String, dynamic> json) =>
      TheaterWhatIfResult(
        skipNodeName: json['skip_node_name']?.toString() ?? '',
        skipNodeIds: (json['skip_node_ids'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        skipNodeNames: (json['skip_node_names'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        originalMastery: (json['original_mastery'] as num?)?.toDouble() ?? 0,
        originalCompletionRate:
            (json['original_completion_rate'] as num?)?.toDouble() ?? 0,
        predictedMastery: (json['predicted_mastery'] as num?)?.toDouble() ?? 0,
        predictedCompletionRate:
            (json['predicted_completion_rate'] as num?)?.toDouble() ?? 0,
        deltaMastery: (json['delta_mastery'] as num?)?.toDouble() ?? 0,
        deltaCompletionRate:
            (json['delta_completion_rate'] as num?)?.toDouble() ?? 0,
        consequences: (json['consequences'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .toList(),
        suggestion: json['suggestion']?.toString() ?? '',
        remainingPath: (json['remaining_path'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(TheaterPathStep.fromJson)
            .toList(),
        branchTimeline: (json['branch_timeline'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(TheaterTimelineFrame.fromJson)
            .toList(),
        branchLabel: json['branch_label']?.toString(),
        branchFocusNodeIds:
            (json['branch_focus_node_ids'] as List<dynamic>? ?? const [])
                .map((item) => item.toString())
                .toList(),
      );

  final String skipNodeName;
  final List<String> skipNodeIds;
  final List<String> skipNodeNames;
  final double originalMastery;
  final double originalCompletionRate;
  final double predictedMastery;
  final double predictedCompletionRate;
  final double deltaMastery;
  final double deltaCompletionRate;
  final List<String> consequences;
  final String suggestion;
  final List<TheaterPathStep> remainingPath;
  final List<TheaterTimelineFrame> branchTimeline;
  final String? branchLabel;
  final List<String> branchFocusNodeIds;
}

class TheaterSnapshot {
  const TheaterSnapshot({
    required this.snapshotId,
    required this.title,
    required this.topic,
    required this.shareResourceType,
  });

  factory TheaterSnapshot.fromJson(Map<String, dynamic> json) {
    final shareHint = json['share_hint'] as Map<String, dynamic>? ?? const {};
    return TheaterSnapshot(
      snapshotId: json['snapshot_id']?.toString() ?? '',
      title: json['title']?.toString() ?? '',
      topic: json['topic']?.toString() ?? '',
      shareResourceType: shareHint['resource_type']?.toString() ?? '',
    );
  }

  final String snapshotId;
  final String title;
  final String topic;
  final String shareResourceType;
}

class TheaterAdoptionResult {
  const TheaterAdoptionResult({
    required this.planId,
    required this.planName,
    this.createdTasks = const [],
    this.checkpointDates = const [],
    this.reviewDueOn,
  });

  factory TheaterAdoptionResult.fromJson(Map<String, dynamic> json) =>
      TheaterAdoptionResult(
        planId: json['plan_id']?.toString() ?? '',
        planName: json['plan_name']?.toString() ?? '',
        createdTasks: (json['created_tasks'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(TheaterTaskBrief.fromJson)
            .toList(),
        checkpointDates:
            (json['checkpoint_dates'] as List<dynamic>? ?? const [])
                .whereType<Map<String, dynamic>>()
                .map(Map<String, dynamic>.from)
                .toList(),
        reviewDueOn: json['review_due_on']?.toString(),
      );

  final String planId;
  final String planName;
  final List<TheaterTaskBrief> createdTasks;
  final List<Map<String, dynamic>> checkpointDates;
  final String? reviewDueOn;
}

class TheaterAccuracySummary {
  const TheaterAccuracySummary({
    required this.predictedCompletionRate,
    required this.predictedMastery,
    required this.actualCompletionRate,
    required this.actualMastery,
    required this.accuracyScore,
  });

  factory TheaterAccuracySummary.fromJson(Map<String, dynamic> json) =>
      TheaterAccuracySummary(
        predictedCompletionRate:
            (json['predicted_completion_rate'] as num?)?.toDouble() ?? 0,
        predictedMastery: (json['predicted_mastery'] as num?)?.toDouble() ?? 0,
        actualCompletionRate:
            (json['actual_completion_rate'] as num?)?.toDouble() ?? 0,
        actualMastery: (json['actual_mastery'] as num?)?.toDouble() ?? 0,
        accuracyScore: (json['accuracy_score'] as num?)?.toDouble() ?? 0,
      );

  final double predictedCompletionRate;
  final double predictedMastery;
  final double actualCompletionRate;
  final double actualMastery;
  final double accuracyScore;
}

class TheaterGalaxyOverlay {
  const TheaterGalaxyOverlay({
    required this.title,
    required this.topic,
    required this.focusNodeIds,
    required this.highlightEdgeIds,
    required this.nodeRiskLevels,
    required this.predictedMasteryByNodeId,
  });

  final String title;
  final String topic;
  final List<String> focusNodeIds;
  final List<String> highlightEdgeIds;
  final Map<String, String> nodeRiskLevels;
  final Map<String, double> predictedMasteryByNodeId;
}
