import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';

void main() {
  group('AuroraComebackContext A-07 goal state parsing', () {
    test('parses goal_state block and staleness flags from engine payload', () {
      final context = AuroraComebackContext.fromJson({
        'comeback_kind': 'checkpoint_debrief',
        'title': '我们先把这几天接回来',
        'message': '你已经 14 天没来了……',
        'should_show_message': true,
        'last_active_at': '2026-09-11T10:00:00',
        'inactive_minutes': 20160,
        'days_away': 14,
        'days_remaining': 0,
        'subject': '计算机网络',
        'next_task_title': 'Day 4 · TCP 流量控制',
        'recent_task_summary': 'TCP 流量控制',
        'light_restart_suggestion': '先开一个「30分钟保底版」。',
        'plan_id': 'plan-1',
        'conversation_id': '',
        'last_message_id': '',
        'topic_summary': '',
        'pending_question': '',
        'active_core_session': <String, dynamic>{},
        'resume_token': '',
        'unfinished_items': <Object>[],
        'calendar_note': '',
        'goal_state': {
          'goal_id': 'goal-1',
          'title': '期末计算机网络冲 85 分',
          'status': 'active',
          'progress': 0.0,
          'ledger': {'completed': 3, 'total': 7, 'ratio': 0.4286},
        },
        'plan_expired': true,
        'stale_focus': true,
        'next_task_overdue_days': 14,
      });

      expect(context.goalState.goalId, 'goal-1');
      expect(context.goalState.title, '期末计算机网络冲 85 分');
      expect(context.goalState.status, 'active');
      // 真源读数如实呈报（含 0），不做修饰。
      expect(context.goalState.progress, 0.0);
      expect(context.goalState.hasLedger, isTrue);
      expect(context.goalState.ledgerCompleted, 3);
      expect(context.goalState.ledgerTotal, 7);
      expect(context.planExpired, isTrue);
      expect(context.staleFocus, isTrue);
      expect(context.nextTaskOverdueDays, 14);
    });

    test('missing goal_state degrades to empty without breaking hasContent',
        () {
      final context = AuroraComebackContext.fromJson({
        'comeback_kind': 'light_resume',
        'message': '继续上次的「函数极限」。',
        'should_show_message': true,
        'last_active_at': '2026-09-25T10:00:00',
        'inactive_minutes': 120,
        'days_away': 0,
        'days_remaining': 0,
        'subject': '',
        'next_task_title': '',
        'recent_task_summary': '',
        'light_restart_suggestion': '',
        'plan_id': '',
        'conversation_id': 'conv-1',
        'last_message_id': '',
        'topic_summary': '函数极限',
        'pending_question': '',
        'active_core_session': <String, dynamic>{},
        'resume_token': '',
        'unfinished_items': <Object>[],
        'calendar_note': '',
      });

      expect(context.goalState.hasContent, isFalse);
      expect(context.goalState.hasLedger, isFalse);
      expect(context.planExpired, isFalse);
      expect(context.staleFocus, isFalse);
      expect(context.hasContent, isTrue);
    });

    test('null progress stays null (honest read of frozen source)', () {
      final context = AuroraComebackContext.fromJson({
        'goal_state': {
          'goal_id': 'goal-2',
          'title': '目标',
          'status': 'active',
          'progress': null,
          'ledger': <String, dynamic>{},
        },
      });

      expect(context.goalState.progress, isNull);
      expect(context.goalState.hasLedger, isFalse);
    });
  });

  group('AuroraComebackContext J-07 rationale / rescope / primary action', () {
    test('parses rationale, rescope, and primary_action blocks', () {
      final context = AuroraComebackContext.fromJson({
        'comeback_kind': 'checkpoint_debrief',
        'title': '我们先把这几天接回来',
        'message': '你已经 7 天没来了……',
        'should_show_message': true,
        'last_active_at': '2026-09-18T10:00:00',
        'inactive_minutes': 10080,
        'days_away': 7,
        'days_remaining': 0,
        'subject': '计算机网络',
        'next_task_title': '',
        'recent_task_summary': '',
        'light_restart_suggestion': '',
        'plan_id': 'plan-7',
        'conversation_id': '',
        'last_message_id': '',
        'topic_summary': '',
        'pending_question': '',
        'active_core_session': <String, dynamic>{},
        'resume_token': '',
        'unfinished_items': <Object>[],
        'calendar_note': '',
        'plan_expired': true,
        'stale_focus': true,
        'rationale': {
          'sources': <Object>['time_passed', 'progress_drifted'],
          'primary': 'progress_drifted',
          'summary': '窗口时间走了 60%、任务账本完成 1/4。',
        },
        'rescope': {
          'available': true,
          'recommended': true,
          'endpoint': '/api/v1/plans/plan-7/replan',
          'reason': 'plan_window_expired',
        },
        'primary_action': {
          'kind': 'rescope_plan',
          'route': '/plans/plan-7/edit',
          'within_actions': 2,
        },
      });

      expect(context.rationale.sources, ['time_passed', 'progress_drifted']);
      expect(context.rationale.primary, 'progress_drifted');
      expect(context.rationale.summary, contains('1/4'));
      expect(context.rescope.available, isTrue);
      expect(context.rescope.recommended, isTrue);
      expect(
        context.rescope.endpoint,
        '/api/v1/plans/plan-7/replan',
      );
      expect(context.rescope.reason, 'plan_window_expired');
      expect(context.rescope.recommended, isTrue);
      expect(context.rescope.hasRecommendation, isTrue);
      expect(context.primaryAction.kind, 'rescope_plan');
      expect(context.primaryAction.route, '/plans/plan-7/edit');
      // ≤2 actions 量化：回来主路径的交互步数不超过 2。
      expect(context.primaryAction.withinActions, lessThanOrEqualTo(2));
    });

    test('missing rationale/rescope blocks degrade to neutral defaults', () {
      final context = AuroraComebackContext.fromJson({
        'comeback_kind': 'light_resume',
        'message': '继续上次的「函数极限」。',
        'should_show_message': true,
        'last_active_at': '2026-09-25T10:00:00',
        'inactive_minutes': 120,
        'days_away': 0,
        'days_remaining': 0,
        'subject': '',
        'next_task_title': '',
        'recent_task_summary': '',
        'light_restart_suggestion': '',
        'plan_id': '',
        'conversation_id': 'conv-1',
        'last_message_id': '',
        'topic_summary': '函数极限',
        'pending_question': '',
        'active_core_session': <String, dynamic>{},
        'resume_token': '',
        'unfinished_items': <Object>[],
        'calendar_note': '',
      });

      expect(context.rationale.sources, isEmpty);
      expect(context.rationale.primary, isEmpty);
      expect(context.rescope.available, isFalse);
      expect(context.rescope.recommended, isFalse);
      expect(context.rescope.hasRecommendation, isFalse);
      expect(context.primaryAction.kind, isEmpty);
      expect(context.primaryAction.route, isEmpty);
      expect(context.primaryAction.withinActions, 0);
    });
  });
}
