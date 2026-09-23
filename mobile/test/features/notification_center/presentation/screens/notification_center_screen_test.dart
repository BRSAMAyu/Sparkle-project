import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/notification_center/presentation/screens/notification_center_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

class _StubNotificationCenter extends NotificationCenter {
  @override
  NotificationCenterState build() =>
      // N15（ERR-SECONDARY 批）：error 字段已类型化——状态只存类别，
      // 原始异常文本从不入户。
      NotificationCenterState(error: UiErrorCategory.unknown);

  @override
  Future<void> loadNotifications({
    bool unreadOnly = false,
    String? sourceType,
  }) async {}
}

/// A-SPEC3 改造 #2（N15/EE-G2）：notification_center_screen.dart:266 直出靶——
/// 裸 `Text(error)` 行删除、标题不再经 loadingFailed({error}) 内插原始异常，
/// 详情行经唯一映射 owner 人话化。
/// ERR-SECONDARY 批续：state.error 由 String 升级为 UiErrorCategory，
/// 渲染侧改经 uiErrorMessage 类别映射（不再对 raw 串做文本嗅探）。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
      'error view drops the double raw dump — humanized single line only',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          notificationCenterProvider
              .overrideWith(_StubNotificationCenter.new),
        ],
        child: testMaterialApp(home: const NotificationCenterScreen()),
      ),
    );
    await tester.pump();
    await tester.pump();

    // 标题为人话固定文案（不再内插原始异常）。
    expect(find.text('通知加载失败'), findsOneWidget);
    // 旧契约两处直出（loadingFailed('Exception: …') + Text(error)）均不复存在；
    // 类型化后 raw 异常形态在 UI 无任何出现面。
    expect(find.textContaining('notification feed blew up'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    expect(find.textContaining('加载失败:'), findsNothing);
    // 详情行经 owner 映射：unknown 类别落 arb 兜底人话，且只出现一次（无双份）。
    expect(find.textContaining('哎呀，出错了'), findsOneWidget);
  });
}
