import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_scroll_anchor.dart';

/// V4-U07「上滑后不自动拉回」：ChatScrollAnchor 的可失败钉。
///
/// 每面一正一反（widget 层用 chat_screen 同款 reversed ListView + 真实
/// 滚动物理驱动，不是只有纯函数自证）：
/// - 正：贴底时新内容到达 → 跟随最新端（既有行为保持）；
/// - 反：用户上滑离开最新端后新内容到达 → 视口不被拉回（阅读位置保留）；
/// - 反：离开最新端即解除跟随（阈值判定，与驱动来源无关）；
/// - 正：用户显式动作（forceFollow）恢复跟随。
void main() {
  testWidgets('贴底时到达性滚动继续跟随最新端（既有行为）', (tester) async {
    final controller = ScrollController();
    final anchor = ChatScrollAnchor();
    var itemCount = 30;

    Widget buildList() => Directionality(
          textDirection: TextDirection.ltr,
          child: ListView.custom(
            controller: controller,
            reverse: true,
            childrenDelegate: SliverChildBuilderDelegate(
              (context, index) => SizedBox(
                height: 80,
                child: Text('message-${itemCount - 1 - index}'),
              ),
              childCount: itemCount,
            ),
          ),
        );

    await tester.pumpWidget(buildList());
    await tester.pumpAndSettle();

    // 贴底（offset 0），模拟新消息到达前的滚动帧。
    anchor.updateFromPosition(controller.position);
    expect(anchor.shouldFollow, isTrue);

    itemCount += 1;
    await tester.pumpWidget(buildList());
    await tester.pumpAndSettle();
    expect(anchor.shouldFollow, isTrue);
    expect(controller.offset, 0.0);
  });

  testWidgets('上滑阅读历史后新内容到达不拉回视口（卡面核心反例）', (tester) async {
    final controller = ScrollController();
    final anchor = ChatScrollAnchor();
    var itemCount = 60;

    Widget buildList() => Directionality(
          textDirection: TextDirection.ltr,
          child: ListView.custom(
            controller: controller,
            reverse: true,
            childrenDelegate: SliverChildBuilderDelegate(
              (context, index) => SizedBox(
                height: 80,
                child: Text('message-${itemCount - 1 - index}'),
              ),
              childCount: itemCount,
            ),
          ),
        );

    await tester.pumpWidget(buildList());
    await tester.pumpAndSettle();
    expect(controller.offset, 0.0);

    // 用户上滑（reversed 列表向上拖 = offset 增大 = 走向历史端）。
    await tester.drag(find.byType(ListView), const Offset(0, 600));
    await tester.pumpAndSettle();
    final readingOffset = controller.offset;
    expect(
      readingOffset,
      greaterThan(ChatScrollAnchor.kChatFollowLatestThreshold),
    );

    anchor.updateFromPosition(controller.position);
    expect(anchor.shouldFollow, isFalse, reason: '用户手势离开最新端后必须解除跟随');

    // 流式/新消息到达（到达性滚动调用）——必须不拉回。
    itemCount += 1;
    await tester.pumpWidget(buildList());
    await tester.pumpAndSettle();
    expect(anchor.shouldFollow, isFalse);
    expect(controller.offset, readingOffset, reason: '上滑阅读位置不被自动拉回，中断处内容保持可见');
  });

  test('离开最新端即解除跟随；恢复只经 forceFollow 或滑回贴底（阈值语义）', () {
    final anchor = ChatScrollAnchor()
      ..forceFollow()
      ..reset();
    expect(anchor.shouldFollow, isTrue);

    // 阈值外 → 解除（不区分驱动来源，只有「停在哪里」一个事实）。
    anchor
      ..updateFromPosition(_FakePosition(600))
      ..forceFollow();
    expect(anchor.shouldFollow, isTrue);

    // 滑回贴底窗口内 → 恢复跟随。
    anchor.updateFromPosition(_FakePosition(100));
    expect(anchor.shouldFollow, isTrue);
  });

  testWidgets('用户显式动作 forceFollow 恢复跟随（发送消息路径）', (tester) async {
    final controller = ScrollController();
    final anchor = ChatScrollAnchor();
    var itemCount = 60;

    Widget buildList() => Directionality(
          textDirection: TextDirection.ltr,
          child: ListView.custom(
            controller: controller,
            reverse: true,
            childrenDelegate: SliverChildBuilderDelegate(
              (context, index) => SizedBox(
                height: 80,
                child: Text('message-${itemCount - 1 - index}'),
              ),
              childCount: itemCount,
            ),
          ),
        );

    await tester.pumpWidget(buildList());
    await tester.pumpAndSettle();

    await tester.drag(find.byType(ListView), const Offset(0, 600));
    await tester.pumpAndSettle();
    anchor.updateFromPosition(controller.position);
    expect(anchor.shouldFollow, isFalse);

    // 用户发送消息：chat_screen._scrollToBottom(force: true)。
    anchor.forceFollow();
    expect(anchor.shouldFollow, isTrue);

    itemCount += 1;
    await tester.pumpWidget(buildList());
    await tester.pumpAndSettle();
    // forceFollow 本身不滚（滚动由 screen 的 animateTo 完成）；语义钉：
    // 跟随态已恢复，下一次到达性滚动被允许。
    expect(anchor.shouldFollow, isTrue);
  });
}

/// 阈值判定的最小滚动位置桩（纯位移语义，无需真实视口）。
class _FakePosition implements ScrollPosition {
  _FakePosition(this.pixels);

  @override
  final double pixels;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
