import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// IR-G3/N22 · 通知分级门控落点唯一 机检。
///
/// N22 条款：分级门控落点唯一（通知事件入口单点分流）——通知中心是
/// 全量落点（先入中心），toast 仅即时档（后按档分流）。
void main() {
  final source = File(
    '${Directory.current.path}/lib/features/chat/presentation/providers/'
    'chat_notifier_actions.dart',
  ).readAsStringSync();

  String notificationSection() => source
      .split('处理 Notification Event')
      .skip(1)
      .first
      .split('/// 处理 ActionCard 状态更新')
      .first;

  test('_handleNotificationEvent 经常量映射表单点判档', () {
    expect(
      notificationSection(),
      contains('NotificationInterruptPolicy.resolve'),
      reason: 'priority 字段接真判定（不再只被 demo 消费）',
    );
  });

  test('通知中心全量落点在判档之前（任何档都进中心）', () {
    final section = notificationSection();
    final centerIdx = section.indexOf('handleNewNotification');
    // 锚定调用点（带括号），排除文档注释中的 [NotificationInterruptPolicy.resolve] 提法。
    final tierIdx = section.indexOf('NotificationInterruptPolicy.resolve(');
    expect(centerIdx, greaterThanOrEqualTo(0));
    expect(
      tierIdx,
      greaterThan(centerIdx),
      reason: '先入中心，再决定是否 toast',
    );
  });

  test('非即时档 early return（digest/silent 不写 toast 通道）', () {
    final section = notificationSection();
    expect(
      section,
      contains('if (tier != NotificationInterruptTier.immediate)'),
    );
    // early return 之后才允许出现 lastAction 写入（toast）。
    final afterGate = section
        .split('if (tier != NotificationInterruptTier.immediate)')
        .skip(1)
        .first;
    expect(
      afterGate,
      contains("lastActionStatus: 'notification_received'"),
      reason: '即时档保留 toast 通道',
    );
  });
}
