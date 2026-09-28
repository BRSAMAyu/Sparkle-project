// V4-F05 验收 3 · 五面（首页/卡住 sheet/记忆/长回答/星图）+ 同一状态流。
//
// 每面一正一反：
// - 五面真实表面组件就位（非替身/非重绘）；
// - 同一状态流四步推进在所有面同源生效（F03 冻结文案 + F02 徽章族）；
// - 反例：success 徽章只在 committed 步出现（其余步出现即红）、流步重放
//   幂等、classic 下像素扩展不渗入面内。
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/design/style_preview/style_preview_faces.dart';
import 'package:sparkle/core/design/style_preview/style_preview_page.dart';
import 'package:sparkle/core/design/style_preview/style_preview_seed.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/chat/presentation/widgets/task_stuck_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_background_painter.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';

import 'style_preview_test_harness.dart';

void main() {
  group('faces｜五面真实组件 + 确定性 seed（验收 3 机制面）', () {
    testWidgets('正例：五面真实表面组件逐面就位，seed 渲染真实文案',
        (tester) async {
      tester.view.devicePixelRatio = 2.0;
      // 高视口：committed 内容步下五面全量入懒构建视口（结构性断言一次
      // 可见，不依赖滚动手感）。
      tester.view.physicalSize = const Size(720, 7200);
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      await freshThemeManager();
      await tester.pumpWidget(
        buildPreviewHost(body: const StylePreviewPage()),
      );
      await settlePreview(tester);

      // 推进到 committed（内容步）：runActive 步首页面呈现真实加载骨架
      // （isLoading 语义），seed 内容断言在内容步执行。
      await tester.tap(
        find.byKey(const ValueKey('style-preview-flow-advance')),
      );
      await settlePreview(tester);
      expect(find.text('状态流：任务已更新'), findsOneWidget);

      // 五面卡（页面骨架）。
      for (final face in StylePreviewFace.values) {
        expect(
          find.byKey(ValueKey('style-preview-face-${face.name}')),
          findsOneWidget,
          reason: '面 ${face.title} 缺席',
        );
      }
      // 面内真实表面组件（每面至少一枚）：
      expect(find.byType(TodayCockpitCard), findsOneWidget); // 首页
      expect(find.byType(TaskStuckCard), findsOneWidget); // 卡住 sheet
      expect(find.byType(MemoryEvidenceBadge), findsOneWidget); // 记忆
      expect(find.byType(EvidenceQuickPeek), findsOneWidget);
      expect(find.byType(SparkleMarkdown), findsOneWidget); // 长回答
      expect(find.byType(TiledSectorBackground), findsOneWidget); // 星图
      expect(find.byType(GalaxyNodePreviewCard), findsOneWidget);
      // seed 真实性：面内容来自冻结 seed，非占位符。
      expect(find.textContaining(kSeedGoalTitle), findsWidgets);
      expect(find.textContaining(kSeedStuckCardData['message'] as String),
          findsOneWidget,);
      expect(tester.takeException(), isNull);
    });

    testWidgets('正例：卡住 sheet 面以真实 bottomSheet 打开（sheet 形态本体）',
        (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(720, 1600);
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      await freshThemeManager();
      await tester.pumpWidget(
        buildPreviewHost(
          body: const Scaffold(
            body: SafeArea(child: StylePreviewStuckSheetFace()),
          ),
        ),
      );
      await settlePreview(tester);

      await tester.tap(find.text('以真实 bottomSheet 打开'));
      await settlePreview(tester);

      // sheet 顶层：真实干预卡在 modal sheet 内再现（同 seed 同 build）。
      expect(find.text('卡住 sheet · 真实干预卡'), findsOneWidget);
      expect(
        find.byType(TaskStuckCard),
        findsNWidgets(2), // 面内嵌 1 + sheet 内 1
      );
      // 关闭 sheet（反例：点障碍层收起）。
      await tester.tapAt(const Offset(20, 40));
      await settlePreview(tester);
      expect(find.text('卡住 sheet · 真实干预卡'), findsNothing);
    });

    testWidgets('正例+反例：同一状态流四步推进——所有面同源换态；'
        'success 徽章仅在 committed 步出现（反例：其余步出现即红）',
        (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(720, 3200);
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      await freshThemeManager();
      await tester.pumpWidget(
        buildPreviewHost(body: const StylePreviewPage()),
      );
      await settlePreview(tester);

      Future<void> scrollToTop() async {
        for (var i = 0;
            i < 12 &&
                find
                    .byKey(const ValueKey('style-preview-flow-advance'))
                    .evaluate()
                    .isEmpty;
            i++) {
          await tester.fling(
            find.byType(ListView),
            const Offset(0, 800),
            2000,
          );
          await settlePreview(tester);
        }
      }

      final advance = find.byKey(const ValueKey('style-preview-flow-advance'));

      // 步 1：runActive——同步中；长回答部分可见不伪装完成；无 success 徽章。
      expect(find.text('同步中'), findsWidgets);
      expect(find.byType(PixelSuccessBadge), findsNothing);
      expect(find.text('生成中（部分可见，不伪装完成态）'), findsOneWidget);
      expect(find.textContaining(kSeedLongAnswerFull.trim().substring(0, 12)),
          findsOneWidget,);

      // 步 2：committed——task.committed（成功面孔唯一合法步）。
      await tester.tap(advance);
      await settlePreview(tester);
      expect(find.text('任务已更新'), findsWidgets);
      expect(find.byType(PixelSuccessBadge), findsWidgets);
      // 星图真实映射（滚到懒构建尾部）：committed 回执抬升掌握度 45→82
      // → 推荐复习退出。
      for (var i = 0;
          i < 12 &&
              find
                  .byKey(const ValueKey('style-preview-face-starMap'))
                  .evaluate()
                  .isEmpty;
          i++) {
        await tester.fling(
          find.byType(ListView),
          const Offset(0, -600),
          2000,
        );
        await settlePreview(tester);
      }
      expect(find.byType(GalaxyNodePreviewCard), findsOneWidget);
      expect(find.text('推荐复习'), findsNothing);
      expect(find.text('${kSeedGalaxy.masteryCommitted}'), findsOneWidget);

      // 步 3：memorySaved——记忆高亮但永不成功面孔（F03 分层路由反例面）。
      await scrollToTop();
      await tester.tap(advance);
      await settlePreview(tester);
      expect(find.byType(PixelSuccessBadge), findsNothing,
          reason: 'memory.saved 拿到成功面孔 = F03 分层路由被绕过（红）',);
      expect(find.text('记忆已保存'), findsWidgets);
      expect(find.textContaining('3 OK'), findsOneWidget);

      // 步 4：versionConflict——冲突徽章 + 记忆证据降级 missing。
      await scrollToTop();
      await tester.tap(advance);
      await settlePreview(tester);
      expect(find.text('你的设置已更新，需要重新生成'), findsWidgets);
      expect(find.byType(PixelStateBadge), findsWidgets);
      expect(find.byType(PixelSuccessBadge), findsNothing);
      expect(find.textContaining('缺失'), findsOneWidget);

      // 状态流可复现：重放（第 5 次推进回到步 1）幂等。
      await scrollToTop();
      await tester.tap(advance);
      await settlePreview(tester);
      expect(find.text('同步中'), findsWidgets);
      expect(find.byType(PixelSuccessBadge), findsNothing);
    });
  });
  group('R1-C1a 泛化非空守卫｜未来新增流步拼错键不静默逃逸', () {
    test('全部流步的 F03 冻结 copy 均非空（遍历枚举，不只钉四键字面）', () {
      for (final step in StylePreviewFlowStep.values) {
        final frame = StylePreviewFlowFrame.of(step);
        expect(
          frame.copy,
          isNotEmpty,
          reason: '流步 $step 的冻结 copy 为空——疑似键拼错（?? '' 静默）',
        );
      }
    });
  });

}
