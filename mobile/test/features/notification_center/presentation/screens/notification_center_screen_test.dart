import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/notification_center/presentation/screens/notification_center_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

class _StubNotificationCenter extends NotificationCenter {
  @override
  NotificationCenterState build() =>
      NotificationCenterState(error: 'Exception: notification feed blew up');

  @override
  Future<void> loadNotifications({
    bool unreadOnly = false,
    String? sourceType,
  }) async {}
}

/// A-SPEC3 改造 #2（N15/EE-G2）：notification_center_screen.dart:266 直出靶——
/// 裸 `Text(error)` 行删除、标题不再经 loadingFailed({error}) 内插原始异常，
/// 详情行经唯一映射 owner（UserFacingError.from）人话化。
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
    // 旧契约两处直出（loadingFailed('Exception: …') + Text(error)）均不复存在。
    expect(find.textContaining('notification feed blew up'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    expect(find.textContaining('加载失败:'), findsNothing);
    // 详情行经 owner 映射：人话 + 稳定码，且只出现一次（无双份）。
    expect(find.textContaining('哎呀，出错了'), findsOneWidget);
    expect(find.textContaining('[ERR-UNKNOWN]'), findsOneWidget);
  });
}
