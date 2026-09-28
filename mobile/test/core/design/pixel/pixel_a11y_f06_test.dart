// V4-F06 · 像素组件族无障碍与文本缩放基础能力（验收①②③的族级面）。
//
// 每验收面一正一反（控制组证明探针有判别力，防测试自证）：
//   验收③ 200%：A+ 故事页+组件族 200% 零异常零越界 / A- 探针活性控制组；
//   验收③ reduce-motion：B+ 减弱动效静态分支零 ticker / B- 常规分支动效在航
//         （探针活性）/ B2 accessibleNavigation 同享静态分支；
//   验收① 48dp：C+ PrimaryAction 语义命中面 ≥48dp / C- 32dp 控制组被探针判负；
//   验收② 同义重复朗读：D+ 徽章语义标签逐字相等（无拼接重复）/
//         D- 故意重复标签控制组被探针判负；
//   验收① 对比度：E+ 组件族正文对（classic 深/浅 + 3 像素档）≥4.5:1 /
//         E- 已知不达标对被探针判负。
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel.dart';

/// 与 a11y_contrast_test 同口径的 WCAG 对比度（2.1 相对亮度定义）。
double contrastRatio(Color a, Color b) {
  double channel(double c) {
    final sRGB = c / 255.0;
    return sRGB <= 0.03928
        ? sRGB / 12.92
        : math.pow((sRGB + 0.055) / 1.055, 2.4).toDouble();
  }

  final l1 = 0.2126 * channel(a.r * 255.0) +
      0.7152 * channel(a.g * 255.0) +
      0.0722 * channel(a.b * 255.0);
  final l2 = 0.2126 * channel(b.r * 255.0) +
      0.7152 * channel(b.g * 255.0) +
      0.0722 * channel(b.b * 255.0);
  final lighter = math.max(l1, l2);
  final darker = math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

Future<void> _pumpPixel(
  WidgetTester tester,
  Widget child, {
  PixelPreviewProfile profile = PixelPreviewProfile.paperDay,
  TextScaler? textScaler,
  bool disableAnimations = false,
  bool accessibleNavigation = false,
}) async {
  SharedPreferences.setMockInitialValues({});
  final manager = ThemeManager();
  if (!manager.initialized) await manager.initialize();
  await manager.setPixelPreviewProfile(profile);
  await tester.pumpWidget(
    MaterialApp(
      theme: AppThemes.lightTheme,
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context).copyWith(
          textScaler: textScaler,
          disableAnimations: disableAnimations,
          accessibleNavigation: accessibleNavigation,
        ),
        child: child ?? const SizedBox.shrink(),
      ),
      home: Scaffold(body: child),
    ),
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

  group('验收③ · 200% 文本缩放（像素组件族 + 故事页）', () {
    testWidgets('A+：200% 下故事页全族渲染零异常，五态语义与 CTA 仍在',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await _pumpPixel(
        tester,
        const PixelStateStoryPage(),
        textScaler: const TextScaler.linear(2.0),
      );
      // 状态族区域在视口内先滚出前即有断言面：五态语义在树。
      for (final s in PixelRunState.values) {
        expect(
          find.bySemanticsLabel(PixelStateSpec.forState(s).label),
          findsWidgets,
          reason: '${s.name} 在 200% 下语义缺失',
        );
      }
      expect(find.byType(PixelPrimaryAction), findsWidgets);
      expect(find.byType(PixelReceiptCard), findsOneWidget);
      // 无布局异常（RenderFlex overflow 会经 takeException 暴露）。
      expect(
        tester.takeException(),
        isNull,
        reason: '200% 文本不得在像素组件族产生布局异常',
      );
      semantics.dispose();
    });

    testWidgets('A-：溢出探针活性——故意超宽子树同法必报异常（防自证）',
        (tester) async {
      await _pumpPixel(
        tester,
        // 故意不可收缩的 2000dp 宽盒子：默认测试视口（800×600）必溢出。
        const SizedBox(
          width: 2000,
          child: Row(
            children: [SizedBox(width: 2000, child: Text('OVERFLOW_PROBE'))],
          ),
        ),
      );
      await tester.pump();
      expect(
        tester.takeException(),
        isNotNull,
        reason: '溢出探针必须能捕获布局异常（否则 A+ 的零异常断言无判别力）',
      );
    });
  });

  group('验收③ · reduce-motion 静态分支（PixelSuccessBadge）', () {
    testWidgets('B+：disableAnimations 下零 ticker，直落静止终态',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await _pumpPixel(
        tester,
        const PixelSuccessBadge(),
        disableAnimations: true,
      );
      await tester.pump();
      // 静态分支：无动画控制器（零 ticker）——「零 duration 崩溃」面在
      // 分支前短路。
      expect(
        tester.binding.transientCallbackCount,
        0,
        reason: '减弱动效下成功徽章不得启动 ticker',
      );
      // 终态静止：徽章子树无动效包装器，对勾字形直接呈现。
      expect(
        find.descendant(
          of: find.byType(PixelSuccessBadge),
          matching: find.byType(AnimatedBuilder),
        ),
        findsNothing,
        reason: '静态分支下徽章子树不得存在 AnimatedBuilder 动效包装',
      );
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
      expect(find.bySemanticsLabel('已完成'), findsOneWidget);
      semantics.dispose();
    });

    testWidgets('B-：常规分支动效在航（探针活性——ticker 探针能看见动画）',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await _pumpPixel(tester, const PixelSuccessBadge());
      // 未减弱动效：上升动效在航（650ms 预算内 ticker 存活）。
      await tester.pump(const Duration(milliseconds: 100));
      expect(
        tester.binding.transientCallbackCount,
        greaterThan(0),
        reason: '常规分支必须有在航 ticker（否则 B+ 的零 ticker 断言无判别力）',
      );
      await tester.pumpAndSettle();
      semantics.dispose();
    });

    testWidgets('B2：accessibleNavigation 同享静态分支（双源并集口径）',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await _pumpPixel(
        tester,
        const PixelSuccessBadge(),
        accessibleNavigation: true,
      );
      await tester.pump();
      expect(
        tester.binding.transientCallbackCount,
        0,
        reason: '读屏导航（accessibleNavigation）与 disableAnimations 同入静态分支',
      );
      semantics.dispose();
    });
  });

  group('验收① · 关键目标 ≥48dp', () {
    testWidgets('C+：PixelPrimaryAction 语义命中面 ≥48×48dp', (tester) async {
      final semantics = tester.ensureSemantics();
      await _pumpPixel(
        tester,
        PixelPrimaryAction(label: '主操作', onPressed: () {}),
      );
      await tester.pump();
      final node = tester.getSemantics(find.bySemanticsLabel('主操作'));
      expect(
        node.getSemanticsData().flagsCollection.isButton,
        isTrue,
      );
      expect(
        node.rect.size.width,
        greaterThanOrEqualTo(48),
        reason: '主 CTA 语义宽度不得低于项目 48dp 标准',
      );
      expect(
        node.rect.size.height,
        greaterThanOrEqualTo(48),
        reason: '主 CTA 语义高度不得低于项目 48dp 标准',
      );
      semantics.dispose();
    });

    testWidgets('C-：32dp 控制目标被同一探针判负（探针有判别力）',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await _pumpPixel(
        tester,
        Semantics(
          container: true,
          button: true,
          onTap: () {},
          child: const SizedBox(
            width: 32,
            height: 32,
            child: Text(' undersized probe target '),
          ),
        ),
      );
      await tester.pump();
      final node = tester.getSemantics(find.bySemanticsLabel(' undersized probe target '));
      expect(
        node.rect.size.width,
        lessThan(48),
        reason: '32dp 控制组必须被 48dp 探针判负（否则 C+ 无判别力）',
      );
      expect(node.rect.size.height, lessThan(48));
      semantics.dispose();
    });
  });

  group('验收② · screenreader 无同义重复朗读', () {
    testWidgets('D+：五态徽章语义标签逐字相等（无「X换行X」拼接重复）',
        (tester) async {
      final semantics = tester.ensureSemantics();
      await _pumpPixel(
        tester,
        Column(
          children: [
            for (final s in PixelRunState.values) PixelStateBadge(state: s),
          ],
        ),
      );
      await tester.pump();
      for (final s in PixelRunState.values) {
        final label = PixelStateSpec.forState(s).label;
        final node = tester.getSemantics(find.bySemanticsLabel(label));
        expect(
          node.getSemanticsData().label,
          label,
          reason: '$label 的读屏内容必须逐字相等（子树文本不入语义，不重复拼接）',
        );
      }
      semantics.dispose();
    });

    testWidgets('D-：故意拼接的控制组被同一探针判负（探针有判别力）',
        (tester) async {
      final semantics = tester.ensureSemantics();
      // 反面教材：container 语义 + 未排除的子树文本 → 同义重复拼接
      // （正是 F02 失败史 round 2 的形态，此处钉住探针能看见它）。
      await _pumpPixel(
        tester,
        Semantics(
          container: true,
          label: '已取消',
          child: const Text('已取消'),
        ),
      );
      await tester.pump();
      final node =
          tester.getSemantics(find.bySemanticsLabel(RegExp('已取消')));
      expect(
        node.getSemanticsData().label,
        isNot('已取消'),
        reason: '拼接控制组必须被「逐字相等」探针判负（否则 D+ 无判别力）',
      );
      semantics.dispose();
    });
  });

  group('验收① · 正文对比度 ≥4.5:1（组件族实际用色组合）', () {
    final cases = <String, ({Color fg, Color bg})>{
      // 故事页画布（Scaffold backgroundColor: colors.surfacePrimary）上的
      // 正文/标题 = 组件族 bodyMedium/titleMedium 的实际组合。
      'classic-light textPrimary/surfacePrimary': (
        fg: SparkleColors.light().textPrimary,
        bg: SparkleColors.light().surfacePrimary,
      ),
      'classic-light textSecondary/surfacePrimary': (
        fg: SparkleColors.light().textSecondary,
        bg: SparkleColors.light().surfacePrimary,
      ),
      'classic-dark textPrimary/surfacePrimary': (
        fg: SparkleColors.dark().textPrimary,
        bg: SparkleColors.dark().surfacePrimary,
      ),
      'classic-dark textSecondary/surfacePrimary': (
        fg: SparkleColors.dark().textSecondary,
        bg: SparkleColors.dark().surfacePrimary,
      ),
      // 星图画布正文（galaxy_screen 深色画布 + neutral0 前景）。
      'galaxy neutral0/darkCanvas': (
        fg: DS.neutral0,
        bg: const Color(0xFF101929),
      ),
      // 聊天气泡正文（chat 两侧气泡前景/背景对）。
      'chat userBubble classic-light': (
        fg: SparkleColors.light().chatBubbleUserText,
        bg: SparkleColors.light().chatBubbleUser,
      ),
      'chat otherBubble classic-light': (
        fg: SparkleColors.light().chatBubbleOtherText,
        bg: SparkleColors.light().chatBubbleOther,
      ),
      'chat userBubble classic-dark': (
        fg: SparkleColors.dark().chatBubbleUserText,
        bg: SparkleColors.dark().chatBubbleUser,
      ),
      'chat otherBubble classic-dark': (
        fg: SparkleColors.dark().chatBubbleOtherText,
        bg: SparkleColors.dark().chatBubbleOther,
      ),
      // 像素三档（preview 通道）画布正文。
      'paperDay ink/canvas': (
        fg: pixelPreviewColors(PixelPreviewProfile.paperDay).textPrimary,
        bg: pixelPreviewColors(PixelPreviewProfile.paperDay).surfacePrimary,
      ),
      'paperDay muted/canvas': (
        fg: pixelPreviewColors(PixelPreviewProfile.paperDay).textSecondary,
        bg: pixelPreviewColors(PixelPreviewProfile.paperDay).surfacePrimary,
      ),
      'dusk ink/surface': (
        fg: pixelPreviewColors(PixelPreviewProfile.dusk).textPrimary,
        bg: pixelPreviewColors(PixelPreviewProfile.dusk).surfacePrimary,
      ),
      'dusk muted/surface': (
        fg: pixelPreviewColors(PixelPreviewProfile.dusk).textSecondary,
        bg: pixelPreviewColors(PixelPreviewProfile.dusk).surfacePrimary,
      ),
      'quiet ink/canvas': (
        fg: pixelPreviewColors(PixelPreviewProfile.quiet).textPrimary,
        bg: pixelPreviewColors(PixelPreviewProfile.quiet).surfacePrimary,
      ),
      'quiet muted/canvas': (
        fg: pixelPreviewColors(PixelPreviewProfile.quiet).textSecondary,
        bg: pixelPreviewColors(PixelPreviewProfile.quiet).surfacePrimary,
      ),
    };

    test('E+：全部正文组合 ≥4.5:1（${cases.length} 对）', () {
      for (final entry in cases.entries) {
        final ratio = contrastRatio(entry.value.fg, entry.value.bg);
        expect(
          ratio,
          greaterThanOrEqualTo(4.5),
          reason: '${entry.key} = ${ratio.toStringAsFixed(2)}:1，正文须 ≥4.5:1',
        );
      }
    });

    test('E-：已知不达标对被同一探针判负（探针有判别力）', () {
      // textDisabled (#999999) 在浅画布上 ≈2.85:1——禁用态豁免，但不得混入正文。
      final ratio = contrastRatio(
        SparkleColors.light().textDisabled,
        SparkleColors.light().surfacePrimary,
      );
      expect(
        ratio,
        lessThan(4.5),
        reason: '禁用灰控制组必须被 4.5:1 探针判负（否则 E+ 无判别力）',
      );
    });
  });
}
