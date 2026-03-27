import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';

void main() {
  test('theater phase2 preserves timeline branch and action loop payload', () {
    const route = TheaterPathOption(
      id: 'path_foundation',
      title: '稳扎稳打',
      summary: '先补前置，再推目标。',
      strategyType: 'foundation',
      expertIds: <String>['galaxy_guide'],
      estimatedCompletionRate: 0.84,
      estimatedMastery: 79,
      dailyMinutes: 40,
      risks: <String>['后半程需要稳定性'],
      routeScore: 83,
      checkpointDays: <int>[1, 3, 7],
      weekOneTasks: <TheaterTaskBrief>[
        TheaterTaskBrief(
          title: 'Day 1 · 推进行列式',
          nodeId: 'node-1',
          estimatedMinutes: 35,
          dayLabel: 'Day 1',
        ),
      ],
      steps: <TheaterPathStep>[
        TheaterPathStep(
          index: 1,
          nodeId: 'node-1',
          nodeName: '行列式',
          rationale: '补前置',
          currentMastery: 40,
          predictedMastery: 62,
          riskLevel: 'high',
          estimatedMinutes: 35,
          dayLabel: 'Day 1',
          checkpointLabel: 'Checkpoint · Day 1',
        ),
        TheaterPathStep(
          index: 2,
          nodeId: 'node-2',
          nodeName: '特征值',
          rationale: '推进目标',
          currentMastery: 56,
          predictedMastery: 79,
          riskLevel: 'medium',
          estimatedMinutes: 40,
          dayLabel: 'Day 7',
          checkpointLabel: 'Checkpoint · Day 7',
        ),
      ],
    );

    final prediction = TheaterPrediction(
      predictionId: 'prediction-1',
      topic: '特征值与特征向量',
      targetNodeId: 'node-2',
      targetName: '线性代数',
      horizonDays: 7,
      paths: const <TheaterPathOption>[route],
      discussionTurns: const <TheaterDiscussionTurn>[
        TheaterDiscussionTurn(
          turnIndex: 0,
          agentId: 'galaxy_guide',
          displayName: '星图导航',
          turnType: 'analysis',
          content: '先补前置再推进目标会更稳。',
          relatedNodeIds: <String>['node-1'],
        ),
      ],
      graphNodes: const <TheaterGraphNode>[
        TheaterGraphNode(
          id: 'node-1',
          name: '行列式',
          description: '前置节点',
          currentMastery: 40,
          predictedMastery: 62,
          riskLevel: 'high',
        ),
      ],
      graphEdges: const <TheaterGraphEdge>[
        TheaterGraphEdge(
          id: 'edge-1',
          sourceId: 'node-1',
          targetId: 'node-2',
          relationType: 'prerequisite',
          strength: 0.9,
        ),
      ],
      timeline: const <TheaterTimelineFrame>[
        TheaterTimelineFrame(
          index: 0,
          label: 'Day 1',
          dayIndex: 1,
          routeId: 'path_foundation',
          focusNodeIds: <String>['node-1'],
          discussionTurnIndex: 0,
          projectedMastery: 45,
          projectedCompletionRate: 0.12,
          activeStepNodeId: 'node-1',
          activeStepTitle: '行列式',
          compareLabel: '推荐基线',
          branchType: 'baseline',
        ),
        TheaterTimelineFrame(
          index: 1,
          label: 'Day 7',
          dayIndex: 7,
          routeId: 'path_foundation',
          focusNodeIds: <String>['node-2'],
          discussionTurnIndex: 0,
          projectedMastery: 79,
          projectedCompletionRate: 0.84,
          activeStepNodeId: 'node-2',
          activeStepTitle: '特征值',
          compareLabel: '推荐基线',
          branchType: 'baseline',
        ),
      ],
      recommendedRouteId: 'path_foundation',
      targetResolutionMode: 'knowledge_graph',
      accuracyTracking: const TheaterAccuracyTracking(
        predictionId: 'prediction-1',
        status: 'pending_feedback',
        dueOn: '2026-04-03',
        summaryHint: '建议在 7 天后回填真实完成率和掌握度。',
      ),
    );

    const whatIfResult = TheaterWhatIfResult(
      skipNodeName: '行列式',
      skipNodeIds: <String>['node-1'],
      skipNodeNames: <String>['行列式'],
      originalMastery: 79,
      originalCompletionRate: 0.84,
      predictedMastery: 68,
      predictedCompletionRate: 0.66,
      deltaMastery: -11,
      deltaCompletionRate: -0.18,
      consequences: <String>['后续推导会失去一个校验点。'],
      suggestion: '先做 15 分钟速览再推进。',
      remainingPath: <TheaterPathStep>[
        TheaterPathStep(
          index: 2,
          nodeId: 'node-2',
          nodeName: '特征值',
          rationale: '推进目标',
          currentMastery: 56,
          predictedMastery: 79,
          riskLevel: 'medium',
          estimatedMinutes: 40,
          dayLabel: 'Day 7',
        ),
      ],
      branchTimeline: <TheaterTimelineFrame>[
        TheaterTimelineFrame(
          index: 0,
          label: 'Day 1',
          dayIndex: 1,
          routeId: 'path_foundation',
          focusNodeIds: <String>['node-2'],
          discussionTurnIndex: 0,
          projectedMastery: 68,
          projectedCompletionRate: 0.66,
          activeStepNodeId: 'node-2',
          activeStepTitle: '特征值',
          compareLabel: 'What-If 分支',
          branchType: 'what_if',
        ),
      ],
      branchLabel: '跳过 行列式',
      branchFocusNodeIds: <String>['node-1'],
    );

    const adoptionResult = TheaterAdoptionResult(
      planId: 'plan-1',
      planName: '线性代数 · 稳扎稳打',
      createdTasks: <TheaterTaskBrief>[
        TheaterTaskBrief(
          title: 'Day 1 · 推进行列式',
          nodeId: 'node-1',
          estimatedMinutes: 35,
          dayLabel: 'Day 1',
          taskId: 'task-1',
        ),
      ],
      checkpointDates: <Map<String, dynamic>>[
        <String, dynamic>{'date': '2026-04-03'},
      ],
      reviewDueOn: '2026-04-03',
    );

    expect(prediction.recommendedRouteId, 'path_foundation');
    expect(prediction.targetResolutionMode, 'knowledge_graph');
    expect(prediction.accuracyTracking?.status, 'pending_feedback');
    expect(route.routeScore, 83);
    expect(route.checkpointDays, <int>[1, 3, 7]);
    expect(route.weekOneTasks.first.title, 'Day 1 · 推进行列式');
    expect(prediction.timeline.first.dayIndex, 1);
    expect(prediction.timeline.last.activeStepTitle, '特征值');
    expect(whatIfResult.skipNodeIds, <String>['node-1']);
    expect(whatIfResult.branchTimeline.first.branchType, 'what_if');
    expect(whatIfResult.branchLabel, '跳过 行列式');
    expect(adoptionResult.createdTasks.first.taskId, 'task-1');
    expect(adoptionResult.checkpointDates.single['date'], '2026-04-03');
    expect(adoptionResult.reviewDueOn, '2026-04-03');
  });
}
