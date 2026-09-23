import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/notification_interrupt_policy.dart';

/// N22（A-SPEC4 §7.3）打断三档分级 · 常量映射表单测。
///
/// 验收口径（卡面）：高优（被@/小队事件）→ immediate；普通（点赞等
/// priority=normal/medium）→ digest 只进中心；low → silent；
/// intervention/aurora_confirm 保守条款强制 immediate（宁多一次 toast
/// 不可漏干预）；类型白名单优先于 priority 字段。
void main() {
  group('NotificationInterruptPolicy.tierForPriority', () {
    test('high → immediate（即时档 toast+进中心）', () {
      expect(
        NotificationInterruptPolicy.tierForPriority('high'),
        NotificationInterruptTier.immediate,
      );
    });

    test('normal（引擎缺省值）→ digest（普通通知只进中心）', () {
      expect(
        NotificationInterruptPolicy.tierForPriority('normal'),
        NotificationInterruptTier.digest,
      );
    });

    test('medium → digest（摘要档，仅进中心+红点）', () {
      expect(
        NotificationInterruptPolicy.tierForPriority('medium'),
        NotificationInterruptTier.digest,
      );
    });

    test('low → silent（静默入中心）', () {
      expect(
        NotificationInterruptPolicy.tierForPriority('low'),
        NotificationInterruptTier.silent,
      );
    });

    test('缺失/未知/带空白与大小写差异的值保守归 digest', () {
      expect(
        NotificationInterruptPolicy.tierForPriority(null),
        NotificationInterruptTier.digest,
      );
      expect(
        NotificationInterruptPolicy.tierForPriority(''),
        NotificationInterruptTier.digest,
      );
      expect(
        NotificationInterruptPolicy.tierForPriority('urgent'),
        NotificationInterruptTier.digest,
      );
      expect(
        NotificationInterruptPolicy.tierForPriority(' HIGH '),
        NotificationInterruptTier.immediate,
      );
      expect(
        NotificationInterruptPolicy.tierForPriority('Low'),
        NotificationInterruptTier.silent,
      );
    });
  });

  group('NotificationInterruptPolicy.resolve（类型白名单优先）', () {
    test('被@（mention）强制即时档——即使 priority 声明为 low', () {
      expect(
        NotificationInterruptPolicy.resolve(
          sourceType: 'system',
          contentType: 'mention',
          priority: 'low',
        ),
        NotificationInterruptTier.immediate,
      );
    });

    test('小队事件族强制即时档', () {
      for (final type in const [
        'squad_event',
        'squad_invite',
        'squad_mention',
        'squad_join',
      ]) {
        expect(
          NotificationInterruptPolicy.resolve(
            sourceType: 'system',
            contentType: type,
            priority: 'low',
          ),
          NotificationInterruptTier.immediate,
          reason: '$type 应为即时档',
        );
      }
    });

    test('intervention / aurora_confirm 保守条款：一律 immediate', () {
      for (final source in const [
        'intervention',
        'intervention_push',
        'aurora_confirm',
      ]) {
        expect(
          NotificationInterruptPolicy.resolve(
            sourceType: source,
            contentType: 'whatever',
            priority: 'low',
          ),
          NotificationInterruptTier.immediate,
          reason: '$source 宁多一次 toast 不可漏干预',
        );
      }
    });

    test('task_reminder 属时间敏感例外，强制即时档', () {
      expect(
        NotificationInterruptPolicy.resolve(
          sourceType: 'system',
          contentType: 'task_reminder',
          priority: 'normal',
        ),
        NotificationInterruptTier.immediate,
      );
    });

    test('普通系统通知（点赞/设置/归档类，priority=normal/medium）只进中心', () {
      expect(
        NotificationInterruptPolicy.resolve(
          sourceType: 'system',
          contentType: 'community_like',
          priority: 'normal',
        ),
        NotificationInterruptTier.digest,
      );
      expect(
        NotificationInterruptPolicy.resolve(
          sourceType: 'system',
          contentType: 'plan_archived',
          priority: 'medium',
        ),
        NotificationInterruptTier.digest,
      );
    });

    test('priority=low 的普通通知静默入中心', () {
      expect(
        NotificationInterruptPolicy.resolve(
          sourceType: 'system',
          contentType: 'memory_cleanup',
          priority: 'low',
        ),
        NotificationInterruptTier.silent,
      );
    });

    test('priority 缺失（null）时按内容类型判定：普通类型归 digest', () {
      expect(
        NotificationInterruptPolicy.resolve(
          sourceType: 'system',
          contentType: 'settings_updated',
        ),
        NotificationInterruptTier.digest,
      );
    });

    test('判定不依赖大小写与首尾空白', () {
      expect(
        NotificationInterruptPolicy.resolve(
          sourceType: ' Intervention ',
          contentType: 'other',
          priority: 'low',
        ),
        NotificationInterruptTier.immediate,
      );
      expect(
        NotificationInterruptPolicy.resolve(
          sourceType: 'system',
          contentType: 'MENTION',
        ),
        NotificationInterruptTier.immediate,
      );
    });
  });
}
