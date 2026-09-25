import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/notification_center/data/models/proactive_suggestion_navigation.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';

UnifiedNotification _suggestion(Map<String, dynamic> metadata) =>
    UnifiedNotification.fromJson({
      'id': 'sugg-1',
      'source_type': 'system',
      'title': '你的学习计划状态',
      'content': '距离「计算机网络」目标截止还有 3 天。',
      'type': 'comeback_nudge',
      'priority': 'medium',
      'is_read': false,
      'created_at': DateTime(2026, 9, 25, 9).toIso8601String(),
      'metadata': metadata,
    });

void main() {
  group('P-03 suggestion model elements', () {
    test('parses why_now / suggested_action from engine payload', () {
      final n = _suggestion({
        'suggestion_type': 'comeback_nudge',
        'why_now': '距离「计算机网络」目标截止还有 3 天；任务账本 1/4。',
        'suggested_action': '先开一个「30分钟保底版」。',
      });
      expect(n.whyNow, '距离「计算机网络」目标截止还有 3 天；任务账本 1/4。');
      expect(n.suggestedAction, '先开一个「30分钟保底版」。');
      expect(n.suggestionType, 'comeback_nudge');
      expect(n.isProactiveSuggestion, isTrue);
      // 未反馈过：两个可忽略入口都可用。
      expect(n.canIgnoreTodaySuggestion, isTrue);
      expect(n.canMuteSuggestionType, isTrue);
    });

    test('plain system notification is not a suggestion', () {
      final n = UnifiedNotification.fromJson({
        'id': 'sys-1',
        'source_type': 'system',
        'title': '系统通知',
        'content': '设置已更新。',
        'type': 'settings_updated',
        'is_read': false,
        'created_at': DateTime(2026, 9, 25, 9).toIso8601String(),
      });
      expect(n.isProactiveSuggestion, isFalse);
      expect(n.canIgnoreTodaySuggestion, isFalse);
      expect(n.canMuteSuggestionType, isFalse);
    });

    test('suggestion feedback state gates the ignore/mute entries', () {
      final ignored = _suggestion({
        'suggestion_type': 'comeback_nudge',
        'why_now': '距离目标截止还有 3 天。',
        'suggestion_feedback': 'ignored_today',
      });
      expect(ignored.canIgnoreTodaySuggestion, isFalse);
      expect(ignored.canMuteSuggestionType, isTrue);

      final muted = _suggestion({
        'suggestion_type': 'comeback_nudge',
        'why_now': '距离目标截止还有 3 天。',
        'suggestion_feedback': 'muted',
      });
      expect(muted.canIgnoreTodaySuggestion, isFalse);
      expect(muted.canMuteSuggestionType, isFalse);
    });
  });

  group('P-03 suggestion deep link navigation (offline/expired fallback)', () {
    test('prefers engine destination_route and derives resilience fallback', () {
      final nav = resolveSuggestionNavigation(
        _suggestion({
          'suggestion_type': 'comeback_nudge',
          'destination_route': '/goals/abc-123?source=comeback_nudge',
          'deep_link': '/goals/abc-123?source=comeback_nudge',
        }),
      );
      expect(nav, isNotNull);
      expect(nav!.route, '/goals/abc-123?source=comeback_nudge');
      // 兜底路由非空且不等于死链本身——目标失效时仍有可退回的落点。
      expect(nav.fallbackRoute, isNotEmpty);
    });

    test('builds goal page from goal_state when route missing (F-7 不误用 plan_id)', () {
      final nav = resolveSuggestionNavigation(
        _suggestion({
          'suggestion_type': 'comeback_nudge',
          'goal_state': {
            'goal_id': 'goal-9',
            'title': '期末目标',
            'ledger': {'completed': 1, 'total': 4},
          },
          'plan_id': 'plan-1',
        }),
      );
      expect(nav, isNotNull);
      expect(nav!.route, '/goals/goal-9');
      expect(nav.fallbackRoute, isNotEmpty);
    });

    test('falls back to plan page when only plan_id exists', () {
      final nav = resolveSuggestionNavigation(
        _suggestion({
          'suggestion_type': 'comeback_nudge',
          'plan_id': 'plan-1',
        }),
      );
      expect(nav!.route, '/plans/plan-1');
    });

    test('returns null for suggestion without any resolvable target (dialog)', () {
      final nav = resolveSuggestionNavigation(
        _suggestion({
          'suggestion_type': 'comeback_nudge',
          'why_now': '距离目标截止还有 3 天。',
        }),
      );
      expect(nav, isNull);
    });
  });
}
