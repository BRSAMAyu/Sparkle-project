// V4-F02 · 验收 2：取消/unknown/conflict/失败四态均有区分且无成功动效。
//
// 正例：
//   (a) 四非成功态的「令牌槽 + 字形 + 轮廓 + 动效」四元组两两互异
//       （PixelStateSpec 唯一事实源 + 渲染出的语义标签/颜色双确认）；
//   (b) 四态渲染互异：语义标签各不相同、状态色逐对不等（浅/深两档）。
// 反例（钉死）：
//   (c) 每个非成功态的组件树**绝不**含成功动效元素
//       （PixelSuccessBadge / check_circle / 上升 Transform），
//       celebrates 恒 false；
//   (d) 控制组：同一查找器在故意含 PixelSuccessBadge 的树上必须命中
//       ——证明 (c) 的反例断言是活的，不是恒真。
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel.dart';

/// 验收覆盖的四非成功态。
const List<PixelRunState> kNonSuccessStates = <PixelRunState>[
  PixelRunState.cancelled,
  PixelRunState.unknown,
  PixelRunState.conflict,
  PixelRunState.failed,
];

/// (令牌槽解析键, 字形, 轮廓, 动效) 四元组 → 区分性断言的规范投影。
({String colorKey, IconData icon, PixelStateOutline outline, bool motion})
    _specSignature(PixelRunState s, SparkleColors colors) {
  final spec = PixelStateSpec.forState(s);
  return (
    colorKey: '0x${spec.colorOf(colors).toARGB32().toRadixString(16)}',
    icon: spec.icon,
    outline: spec.outline,
    motion: spec.celebrates,
  );
}

Future<void> _pumpPixel(WidgetTester tester, Widget child) async {
  SharedPreferences.setMockInitialValues({});
  final manager = ThemeManager();
  if (!manager.initialized) await manager.initialize();
  await manager.setPixelPreviewProfile(PixelPreviewProfile.paperDay);
  await tester.pumpWidget(
    MaterialApp(theme: AppThemes.lightTheme, home: Scaffold(body: child)),
  );
  await tester.pump();
}

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final manager = ThemeManager();
    if (!manager.initialized) await manager.initialize();
    await manager.setPixelPreviewProfile(PixelPreviewProfile.paperDay);
  });

  group('四元组区分性（PixelStateSpec 唯一事实源）', () {
    test('四非成功态两两互异（令牌槽+字形+轮廓+动效）', () {
      final colors = SparkleColors.light();
      final sigs = {
        for (final s in kNonSuccessStates) s: _specSignature(s, colors),
      };
      for (var i = 0; i < kNonSuccessStates.length; i++) {
        for (var j = i + 1; j < kNonSuccessStates.length; j++) {
          expect(
            sigs[kNonSuccessStates[i]],
            isNot(sigs[kNonSuccessStates[j]]),
            reason:
                '${kNonSuccessStates[i]} 与 ${kNonSuccessStates[j]} 四元组撞车',
          );
        }
      }
    });

    test('动效维度：celebrates 只有 success 为 true', () {
      for (final s in PixelRunState.values) {
        expect(
          PixelStateSpec.forState(s).celebrates,
          s == PixelRunState.success,
          reason: '$s 的庆祝位违反「非成功无成功动效」合同',
        );
      }
    });

    test('轮廓区分维：cancelled/unknown/conflict/failed 各占一形', () {
      expect(
        kNonSuccessStates
            .map((s) => PixelStateSpec.forState(s).outline)
            .toSet(),
        hasLength(4),
      );
    });
  });

  group('渲染面区分 + 无成功动效（反例钉死）', () {
    for (final profile in [PixelPreviewProfile.paperDay, PixelPreviewProfile.dusk]) {
      testWidgets('[$profile] 四态语义标签互异、状态色逐对不等', (tester) async {
        SharedPreferences.setMockInitialValues({});
        final manager = ThemeManager();
        if (!manager.initialized) await manager.initialize();
        await manager.setPixelPreviewProfile(profile);
        final semantics = tester.ensureSemantics();
        await tester.pumpWidget(
          MaterialApp(
            theme: AppThemes.lightTheme,
            home: Scaffold(
              body: Column(
                children: [
                  for (final s in kNonSuccessStates)
                    PixelStateBadge(key: ValueKey(s), state: s),
                ],
              ),
            ),
          ),
        );
        await tester.pump();
        // 语义标签四态互异。
        final labels = kNonSuccessStates
            .map((s) => PixelStateSpec.forState(s).label)
            .toSet();
        expect(labels, hasLength(4));
        for (final label in labels) {
          expect(find.bySemanticsLabel(label), findsOneWidget);
        }
        // 状态色逐对不等（badge 内 Icon 颜色 = spec 状态色）。
        Color? iconColorOf(PixelRunState s) {
          final icon = tester.widget<Icon>(
            find
                .descendant(
                  of: find.byKey(ValueKey(s)),
                  matching: find.byType(Icon),
                )
                .first,
          );
          return icon.color;
        }

        for (var i = 0; i < kNonSuccessStates.length; i++) {
          for (var j = i + 1; j < kNonSuccessStates.length; j++) {
            expect(
              iconColorOf(kNonSuccessStates[i]),
              isNot(iconColorOf(kNonSuccessStates[j])),
              reason:
                  '$profile 下 ${kNonSuccessStates[i]}/${kNonSuccessStates[j]} 状态色相同',
            );
          }
        }
        semantics.dispose();
      });
    }

    for (final s in kNonSuccessStates) {
      testWidgets('[$s] 组件树绝不含成功动效元素（反例钉死）', (tester) async {
        final semantics = tester.ensureSemantics();
        await _pumpPixel(
          tester,
          PixelPrimaryCard(
            title: '状态承载',
            state: s,
            child: const Text('内容'),
          ),
        );
        await tester.pumpAndSettle();
        // (c) 无成功徽章类型、无成功字形、无庆祝上升变换。
        expect(find.byType(PixelSuccessBadge), findsNothing,
            reason: '$s 渲染出了成功徽章',);
        expect(find.byIcon(Icons.check_circle), findsNothing);
        expect(find.byIcon(Icons.check), findsNothing);
        // 语义不庆祝：状态语义不出现「已完成」。
        expect(find.bySemanticsLabel('已完成'), findsNothing);
        // spec 动效位恒 false。
        expect(PixelStateSpec.forState(s).celebrates, isFalse);
        semantics.dispose();
      });
    }

    testWidgets('控制组：同一查找器在含成功徽章的树上必须命中（可失败性）',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await _pumpPixel(
        tester,
        const Column(
          children: [
            PixelSuccessBadge(),
            PixelPrimaryCard(
              title: '成功对照',
              state: PixelRunState.success,
              child: Text('庆祝'),
            ),
          ],
        ),
      );
      await tester.pumpAndSettle();
      // (d) 反例断言的活性证明：查找器找到成功徽章与对勾字形
      //     （2 = 直接示例 + success 态卡片徽章，计数钉死防漂移）。
      expect(find.byType(PixelSuccessBadge), findsNWidgets(2));
      expect(find.byIcon(Icons.check_circle), findsNWidgets(2));
      expect(find.bySemanticsLabel('已完成'), findsWidgets);
      semantics.dispose();
    });
  });

  group('状态故事页（preview 路由种子）', () {
    testWidgets('故事页完整渲染：四非成功态 + 成功对照各就位', (tester) async {
      final semantics = tester.ensureSemantics();
      await _pumpPixel(tester, const PixelStateStoryPage());
      await tester.pumpAndSettle();
      // 四态徽章语义各存在。
      for (final s in PixelRunState.values) {
        final label = PixelStateSpec.forState(s).label;
        expect(
          find.bySemanticsLabel(label),
          findsWidgets,
          reason: '$label 未在故事页出现',
        );
      }
      // 成功庆祝元素计数钉死：状态族示例 1 + 成功对照卡 1。
      expect(find.byType(PixelSuccessBadge), findsNWidgets(2));
      // 组件族各组件在页。
      expect(find.byType(PixelPrimaryCard), findsWidgets);
      expect(find.byType(PixelSecondaryCard), findsWidgets);
      expect(find.byType(PixelReceiptCard), findsOneWidget);
      expect(find.byType(PixelDiffCard), findsWidgets);
      expect(find.byType(PixelRunCard), findsOneWidget);
      expect(find.byType(PixelEvidenceStamp), findsWidgets);
      expect(find.byType(PixelDivider), findsOneWidget);
      semantics.dispose();
    });
  });
}
