import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';

void main() {
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
