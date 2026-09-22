// GOAL-ROUTER regression: the home dashboard goal snapshot card and the goal
// detail screen both consume GET /experience/goal-detail/{goal_id}.
//
// After the engine verdict (v3-output/GOAL-ROUTER/REPORT.md) the route is owned
// by experience/goal_router.py whose `minimum_acceptance_criteria` is a dict
// `{description, status, thresholds: [...]}` (the goal-screen + criteria-status
// PUT contract). The legacy readouts snapshot shipped a flat list
// `[{label, status, source}]`. GoalDetailSnapshot must keep rendering criteria
// lines for BOTH shapes so the home card does not regress while the goal detail
// screen finally receives its typed payload.
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/experience/data/experience_models.dart';

void main() {
  test('parses router-shape criteria dict (thresholds) into readable lines', () {
    final snapshot = GoalDetailSnapshot.fromJson(const <String, dynamic>{
      'active': true,
      'goal': <String, dynamic>{
        'id': 'g1',
        'title': '数据结构期中冲刺',
        'goal_type': 'exam',
        'status': 'active',
        'mastery': 0.42,
        'progress': 0.6,
        'priority': 'high',
      },
      'plan': null,
      'progress': <String, dynamic>{
        'overall': 0.6,
        'tasks_total': 4,
        'tasks_completed': 1,
        'paused': 1,
        'stuck': 0,
      },
      'minimum_acceptance_criteria': <String, dynamic>{
        'description': '期中不低于 85 分',
        'status': 'pending_confirmation',
        'thresholds': <Object?>[
          <String, dynamic>{'id': 'c1', 'label': '模拟卷', 'threshold': 85, 'unit': '分'},
          <String, dynamic>{'id': 'c2', 'label': '错题本完成复盘'},
        ],
      },
      'next_task': <String, dynamic>{'id': 't1', 'title': '复习第 3 章'},
      'goal_graph': <String, dynamic>{'active': false, 'nodes': <Object?>[]},
      'why_this_matters': '图瓶颈提示',
    });

    expect(snapshot.active, isTrue);
    expect(snapshot.goalId, 'g1');
    expect(snapshot.title, '数据结构期中冲刺');
    expect(snapshot.nextTaskTitle, '复习第 3 章');
    expect(snapshot.whyThisMatters, '图瓶颈提示');
    expect(snapshot.criteria, <String>['模拟卷 >= 85分', '错题本完成复盘']);
  });

  test('still parses legacy readouts-shape criteria list', () {
    final snapshot = GoalDetailSnapshot.fromJson(const <String, dynamic>{
      'active': true,
      'goal': <String, dynamic>{'id': 'g2', 'title': 'Legacy goal'},
      'minimum_acceptance_criteria': <Object?>[
        <String, dynamic>{'label': '核心科目达到目标分数线', 'status': 'draft', 'source': 'sparkle_draft'},
        <String, dynamic>{'label': '关键风险已被复盘并处理', 'status': 'draft', 'source': 'sparkle_draft'},
      ],
    });

    expect(snapshot.criteria, <String>[
      '核心科目达到目标分数线',
      '关键风险已被复盘并处理',
    ]);
  });

  test('tolerates missing goal and empty criteria', () {
    final snapshot = GoalDetailSnapshot.fromJson(const <String, dynamic>{
      'active': false,
      'goal': null,
      'minimum_acceptance_criteria': <String, dynamic>{
        'description': '',
        'status': 'draft',
        'thresholds': <Object?>[],
      },
    });

    expect(snapshot.active, isFalse);
    expect(snapshot.title, 'Current goal');
    expect(snapshot.criteria, isEmpty);
  });
}
