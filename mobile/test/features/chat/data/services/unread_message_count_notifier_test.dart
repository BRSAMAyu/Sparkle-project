import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/services/message_notification_service.dart';

/// IR-G2/N24 · badge 生命周期（unreadMessageCountProvider）清除语义单测。
///
/// 三声明（钉在 provider 定义处）：
/// - 触发：community WS 他人消息 increment（community_provider 三处）；
/// - 清除：进入社群 tab reset（shell_navigation 三入口）+ 会话内逐条
///   已读 decrementBy（GroupChatNotifier._markVisibleMessagesAsRead）；
/// - 到达：community tab 角标 / home 横幅 / dashboard 摘要。
void main() {
  group('UnreadMessageCountNotifier 清除语义', () {
    test('reset：进入社群 tab 进入即清，角标归零', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(unreadMessageCountProvider.notifier)
        ..increment()
        ..increment()
        ..increment();
      expect(container.read(unreadMessageCountProvider), 3);

      notifier.reset();
      expect(container.read(unreadMessageCountProvider), 0);
    });

    test('decrementBy：会话内逐条已读精确抵消（2 条已读 → -2）', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(unreadMessageCountProvider.notifier)
        ..increment()
        ..increment()
        ..increment()
        ..decrementBy(2);
      expect(container.read(unreadMessageCountProvider), 1);
    });

    test('decrementBy 钳制 ≥0：历史载入场景不会负抵消', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(unreadMessageCountProvider.notifier)
        ..increment()
        ..decrementBy(5);
      expect(
        container.read(unreadMessageCountProvider),
        0,
        reason: 'badge 是未读事实，禁止出现负数',
      );
    });

    test('decrementBy(0)/负数 为 no-op', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(unreadMessageCountProvider.notifier)
        ..increment()
        ..decrementBy(0)
        ..decrementBy(-3);
      expect(container.read(unreadMessageCountProvider), 1);
    });
  });

  group('N24 机检登记：badge 计数类 provider 必须含清除方法且有调用点', () {
    test('provider 定义文件含清除方法（decrementBy/reset）', () {
      final source = File(
        '${Directory.current.path}/lib/features/chat/data/services/'
        'message_notification_service.dart',
      ).readAsStringSync();
      expect(source, contains('void reset()'));
      expect(source, contains('void decrementBy('));
    });

    test('shell_navigation 存在「进入社群即清」调用点', () {
      final source = File(
        '${Directory.current.path}/lib/core/navigation/shell_navigation.dart',
      ).readAsStringSync();
      expect(
        source,
        contains('unreadMessageCountProvider.notifier).reset()'),
        reason: '进入社群 tab 必须清除 badge（IR-G2：只增不清禁新增）',
      );
    });

    test('community_provider 存在逐条已读 decrementBy 调用点', () {
      final source = File(
        '${Directory.current.path}/lib/features/community/presentation/'
        'providers/community_provider.dart',
      ).readAsStringSync();
      expect(
        source,
        contains('unreadMessageCountProvider.notifier)'),
        reason: '清除触发点在位',
      );
      expect(
        source,
        contains('.decrementBy(unreadVisibleCount)'),
        reason: '群聊会话内标记已读必须抵消 badge（正在看会话不计数）',
      );
      // increment 触发点仍在（三声明之「触发」不被误删）。
      expect(
        source,
        contains('unreadMessageCountProvider.notifier).increment()'),
      );
    });
  });
}
