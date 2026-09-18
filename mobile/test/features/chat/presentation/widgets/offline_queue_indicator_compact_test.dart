import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/offline_queue_indicator.dart';

import '../../../../shared/i18n_test_helper.dart';

/// A-5 残余 / N-6 红绿测试：聊天页「离线横幅 + 键盘」组合态的
/// `BOTTOM OVERFLOWED BY 5.0 PIXELS` 条纹（Android round-2 A2-13/A2-14）。
///
/// 修复：键盘拉起时 OfflineQueueIndicator 切 compact 态
/// （外边距 bottom 8→2、内边距 vertical 8→5，合计回收 9px ≥ 5px 实测溢出），
/// 主 Column 的不可压缩子项重新放得下，条纹消失、发送键不再被盖。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<Size> pumpIndicator(WidgetTester tester, bool compact) async {
    await tester.binding.setSurfaceSize(const Size(400, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final key = GlobalKey();
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: RepaintBoundary(
            child: Align(
              alignment: Alignment.topCenter,
              child: OfflineQueueIndicator(
                key: key,
                status: OfflineQueueIndicatorStatus.sending,
                pendingCount: 3,
                compact: compact,
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    // sending 态有无穷旋转指示器，不能 pumpAndSettle；等 AnimatedSwitcher 完成。
    await tester.pump(const Duration(milliseconds: 250));
    final box = key.currentContext!.findRenderObject()! as RenderBox;
    return box.size;
  }

  testWidgets('compact 态比常规态至少矮 5px（覆盖实测溢出量）', (tester) async {
    final regular = await pumpIndicator(tester, false);
    final compact = await pumpIndicator(tester, true);

    expect(compact.height, lessThan(regular.height));
    final reclaimed = regular.height - compact.height;
    expect(
      reclaimed,
      greaterThanOrEqualTo(5.0),
      reason: '实测组合态溢出 5px，键盘态横幅必须至少回收 5px，实际回收 $reclaimed px',
    );
  });

  testWidgets('常规态保持原尺寸语义（回归保护）', (tester) async {
    final regular = await pumpIndicator(tester, false);
    // margin bottom 8 + padding v 8*2 + 文本行高
    expect(regular.height, greaterThanOrEqualTo(30.0));
  });
}
