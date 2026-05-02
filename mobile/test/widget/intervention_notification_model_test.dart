import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import '../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  test('infers intervention source type from intervention_push notifications',
      () {
    final notification = UnifiedNotification.fromJson({
      'id': 'notif-1',
      'title': '先从很小的一步开始',
      'content': '把今天的入口缩到 5 分钟',
      'type': 'intervention_push',
      'priority': 'high',
      'is_read': false,
      'created_at': DateTime.utc(2026, 4, 3).toIso8601String(),
      'data': {
        'intent_type': 'micro_restart',
        'suggested_step': '先打开任务并计时 5 分钟',
      },
    });

    expect(notification.sourceType, 'intervention');
    expect(notification.intentType, 'micro_restart');
    expect(notification.suggestedStep, '先打开任务并计时 5 分钟');
  });

  test('preview text surfaces intervention suggested step', () {
    final notification = UnifiedNotification.fromJson({
      'id': 'notif-2',
      'source_type': 'intervention',
      'title': '补一个关键概念',
      'content': '你可能卡在热力学过程分类上',
      'type': 'intervention',
      'priority': 'medium',
      'is_read': false,
      'created_at': DateTime.utc(2026, 4, 3).toIso8601String(),
      'metadata': {
        'intent_type': 'concept_gap_focus',
        'suggested_step': '先花 10 分钟补一下等温与绝热的区别',
      },
    });

    expect(notification.previewText, contains('建议动作'));
    expect(notification.previewText, contains('等温与绝热'));
  });

  test('deserializes recall value fields from metadata and top-level payload',
      () {
    final notification = UnifiedNotification.fromJson({
      'id': 'recall-1',
      'source_type': 'push',
      'title': '任务等你开始',
      'content': '今天的第一个任务还没开始，要不要先看一眼？',
      'type': 'recall_notification',
      'created_at': DateTime.utc(2026, 5, 2).toIso8601String(),
      'value_reason': '轻量启动能帮助系统校准任务粒度。',
      'metadata': {
        'reasoning': '今天的计划中有待办任务。',
        'effort_estimate': '预计 5 分钟',
        'deadline_pressure_label': '今日节奏待启动',
        'recall_score': '0.72',
      },
    });

    expect(notification.hasRecallValueDetails, isTrue);
    expect(notification.valueReason, '轻量启动能帮助系统校准任务粒度。');
    expect(notification.recallReason, '今天的计划中有待办任务。');
    expect(notification.effortEstimate, '预计 5 分钟');
    expect(notification.deadlinePressureLabel, '今日节奏待启动');
    expect(notification.recallScore, 0.72);
    expect(notification.canMarkRecallInaccurate, isTrue);
  });

  test('intervention interaction state gates accept and act affordances', () {
    final accepted = UnifiedNotification.fromJson({
      'id': 'notif-3',
      'source_type': 'intervention',
      'title': '先把这一步收下',
      'content': '我已经帮你缩成一个小步子',
      'type': 'intervention',
      'created_at': DateTime.utc(2026, 4, 3).toIso8601String(),
      'metadata': {
        'client_intervention_state': 'accepted',
      },
    });

    final acted = UnifiedNotification.fromJson({
      'id': 'notif-4',
      'source_type': 'intervention',
      'title': '开始这一步',
      'content': '现在就进入计划',
      'type': 'intervention_push',
      'created_at': DateTime.utc(2026, 4, 3).toIso8601String(),
      'metadata': {
        'client_intervention_state': 'acted',
      },
    });

    expect(accepted.canAcceptIntervention, isFalse);
    expect(accepted.canActOnIntervention, isTrue);
    expect(acted.canAcceptIntervention, isFalse);
    expect(acted.canActOnIntervention, isFalse);
  });
}
