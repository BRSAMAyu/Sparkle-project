import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/theater/data/models/theater_models.dart';

void main() {
  test('theater phase2 preserves timeline branch, disclaimer, and low-quality payload', () {
    final prediction = TheaterPrediction.fromJson(<String, dynamic>{
      'prediction_id': 'prediction-1',
      'topic': '特征值与特征向量',
      'target_node_id': 'node-2',
      'target_name': '线性代数',
      'horizon_days': 7,
      'disclaimer': '此推演基于 AI 对主题的通用理解，未经你的实际学习数据验证。',
      'paths': <Map<String, dynamic>>[
        <String, dynamic>{
          'id': 'path_foundation',
          'title': '稳扎稳打',
          'summary': '先补前置，再推目标。',
          'strategy_type': 'foundation',
          'expert_ids': <String>['galaxy_guide'],
          'estimated_completion_rate': null,
          'estimated_mastery': null,
          'daily_minutes': 40,
          'risks': <String>['后半程需要稳定性'],
          'route_score': 83,
          'checkpoint_days': <int>[1, 3, 7],
          'data_sufficiency_score': 0.42,
          'data_quality': 'low',
          'completion_range_low': 0.64,
          'completion_range_high': 0.82,
          'mastery_range_low': 58,
          'mastery_range_high': 76,
          'week_one_tasks': <Map<String, dynamic>>[
            <String, dynamic>{
              'title': '第 1 天 · 推进行列式',
              'node_id': 'node-1',
              'estimated_minutes': 35,
              'day_label': '第 1 天',
            },
          ],
          'steps': <Map<String, dynamic>>[
            <String, dynamic>{
              'index': 1,
              'node_id': 'node-1',
              'node_name': '行列式',
              'rationale': '补前置',
              'current_mastery': 40,
              'predicted_mastery': null,
              'risk_level': 'high',
              'estimated_minutes': 35,
              'day_label': '第 1 天',
              'checkpoint_label': '检查点 · 第 1 天',
              'source_type': 'ai_suggested',
            },
            <String, dynamic>{
              'index': 2,
              'node_id': 'node-2',
              'node_name': '特征值',
              'rationale': '推进目标',
              'current_mastery': 56,
              'predicted_mastery': null,
              'risk_level': 'medium',
              'estimated_minutes': 40,
              'day_label': '第 2 天',
              'checkpoint_label': '检查点 · 第 2 天',
              'source_type': 'ai_suggested',
            },
          ],
        },
      ],
      'discussion_turns': <Map<String, dynamic>>[
        <String, dynamic>{
          'turn_index': 0,
          'agent_id': 'galaxy_guide',
          'display_name': '星图导航',
          'turn_type': 'analysis',
          'content': '先补前置再推进目标会更稳。',
          'related_node_ids': <String>['node-1'],
        },
      ],
      'graph': <String, dynamic>{
        'nodes': <Map<String, dynamic>>[
          <String, dynamic>{
            'id': 'node-1',
            'name': '行列式',
            'description': '前置节点',
            'current_mastery': 40,
            'predicted_mastery': 62,
            'risk_level': 'high',
          },
        ],
        'edges': <Map<String, dynamic>>[
          <String, dynamic>{
            'id': 'edge-1',
            'source_id': 'node-1',
            'target_id': 'node-2',
            'relation_type': 'prerequisite',
            'strength': 0.9,
          },
        ],
      },
      'timeline': <Map<String, dynamic>>[
        <String, dynamic>{
          'index': 0,
          'label': '第 1 天 · 步骤 1',
          'day_index': 1,
          'route_id': 'path_foundation',
          'focus_node_ids': <String>['node-1'],
          'discussion_turn_index': 0,
          'projected_mastery': 45,
          'projected_completion_rate': 0.12,
          'active_step_node_id': 'node-1',
          'active_step_title': '行列式',
          'compare_label': '推荐基线',
          'branch_type': 'baseline',
        },
        <String, dynamic>{
          'index': 1,
          'label': '第 2 天 · 步骤 2',
          'day_index': 2,
          'route_id': 'path_foundation',
          'focus_node_ids': <String>['node-2'],
          'discussion_turn_index': 0,
          'projected_mastery': 79,
          'projected_completion_rate': 0.84,
          'active_step_node_id': 'node-2',
          'active_step_title': '特征值',
          'compare_label': '推荐基线',
          'branch_type': 'baseline',
        },
      ],
      'recommended_route_id': 'path_foundation',
      'target_resolution_mode': 'freeform_only',
      'accuracy_tracking': <String, dynamic>{
        'prediction_id': 'prediction-1',
        'status': 'pending_feedback',
        'due_on': '2026-04-03',
        'summary_hint': '建议在 7 天后回填真实完成率和掌握度。',
      },
    });

    final route = prediction.paths.single;

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
          dayLabel: '第 2 天',
        ),
      ],
      branchTimeline: <TheaterTimelineFrame>[
        TheaterTimelineFrame(
          index: 0,
          label: '第 1 天 · 步骤 1',
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
          title: '第 1 天 · 推进行列式',
          nodeId: 'node-1',
          estimatedMinutes: 35,
          dayLabel: '第 1 天',
          taskId: 'task-1',
        ),
      ],
      checkpointDates: <Map<String, dynamic>>[
        <String, dynamic>{'date': '2026-04-03'},
      ],
      reviewDueOn: '2026-04-03',
    );

    expect(prediction.recommendedRouteId, 'path_foundation');
    expect(prediction.targetResolutionMode, 'freeform_only');
    expect(prediction.disclaimer, isNotNull);
    expect(prediction.accuracyTracking?.status, 'pending_feedback');
    expect(route.routeScore, 83);
    expect(route.dataQuality, 'low');
    expect(route.dataSufficiencyScore, 0.42);
    expect(route.estimatedCompletionRate, 0);
    expect(route.completionRangeLow, 0.64);
    expect(route.completionRangeHigh, 0.82);
    expect(route.steps.first.predictedMastery, 0);
    expect(route.checkpointDays, <int>[1, 3, 7]);
    expect(route.weekOneTasks.first.title, '第 1 天 · 推进行列式');
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
