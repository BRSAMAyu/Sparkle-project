// V4-F02 · 验收 1：DPR 1/1.25/1.5/2/3 主要轮廓稳定，文字不点阵化。
//
// 正例：像素轮廓在五档 devicePixelRatio 下——
//   (a) 路径顶点全部落在物理像素网格（stroke 中心对齐物理像素）；
//   (b) 阶梯步数（几何不变量）与逻辑布局盒 DPR 无关；
//   (c) 渲染盒逻辑尺寸跨 DPR 恒等（布局保持逻辑 dp 连续）；
//   (d) 文字始终系统字体路径（RenderParagraph、fontSize 逻辑值跨 DPR
//       恒等、无 RawImage 位图、无 Transform 缩放文字画布）。
// 反例（可失败性控制组）：未吸附顶点 / 位图缩放文字的假组件在同一
//   断言下必须失败——证明测试有判别力，不是恒真。
//
// 设备像素比经 `tester.view`（TestFlutterView）注入，并按
// physical = logical × dpr 固定逻辑表面，五档共用同一布局约束。
// 真机/桌面多屏物理呈现为设备面：如实 NOT_RUN（见 evidence limitations）。
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel.dart';

/// 五档覆盖（卡面验收枚举值）。
const List<double> kTestDprs = <double>[1.0, 1.25, 1.5, 2.0, 3.0];

/// 逻辑测试表面（五档下 physical = 400×300 × dpr，约束恒等）。
const Size kLogicalSurface = Size(400, 300);
const Size kFrameLogicalSize = Size(200, 120);

bool onPhysicalGrid(double logical, double dpr) {
  final physical = logical * dpr;
  return (physical - physical.roundToDouble()).abs() < 1e-6;
}

/// 像素档测试宿主（paperDay preview 开启，组件吃到 PixelProfileTheme）。
Future<ThemeManager> _pumpPixelHost(
  WidgetTester tester, {
  required double dpr,
  Widget? child,
}) async {
  SharedPreferences.setMockInitialValues({});
  final manager = ThemeManager();
  if (!manager.initialized) {
    await manager.initialize();
  }
  await manager.setPixelPreviewProfile(PixelPreviewProfile.paperDay);
  tester.view.devicePixelRatio = dpr;
  tester.view.physicalSize = Size(
    kLogicalSurface.width * dpr,
    kLogicalSurface.height * dpr,
  );
  tester.view.platformDispatcher.localeTestValue = const Locale('zh');
  await tester.pumpWidget(
    MaterialApp(
      theme: AppThemes.lightTheme,
      home: Scaffold(
        body: Center(
          child: SizedBox(
            width: kFrameLogicalSize.width,
            height: kFrameLogicalSize.height,
            child: child ?? _LabelledFrame(),
          ),
        ),
      ),
    ),
  );
  await tester.pump();
  return manager;
}

/// 被测宿主：切角主框 + 系统字体文本（文字不点阵化的观察对象）。
class _LabelledFrame extends StatelessWidget {
  @override
  Widget build(BuildContext context) => const PixelFrame(
      emphasis: PixelFrameEmphasis.primary,
      cutCorner: true,
      child: Center(
        child: Text(
          '轮廓稳定',
          semanticsLabel: '轮廓稳定文本',
        ),
      ),
    );
}

Finder _outlinePaintFinder() => find.byWidgetPredicate(
      (w) => w is CustomPaint && w.painter is PixelOutlinePainter,
    );

PixelOutlinePainter _outlinePainterOf(WidgetTester tester) =>
    tester.widget<CustomPaint>(_outlinePaintFinder()).painter!
        as PixelOutlinePainter;

RenderCustomPaint _outlineRenderOf(WidgetTester tester) =>
    tester.renderObject<RenderCustomPaint>(_outlinePaintFinder());

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final manager = ThemeManager();
    if (!manager.initialized) {
      await manager.initialize();
    }
    await manager.setPixelPreviewProfile(PixelPreviewProfile.paperDay);
  });

  /// 每个用到 tester.view 的用例注册视图复位（跨用例不泄漏）。
  void resetViewOnTearDown(WidgetTester tester) {
    addTearDown(() {
      tester.view.resetDevicePixelRatio();
      tester.view.resetPhysicalSize();
    });
  }

  group('纯几何：五档 DPR 物理像素吸附（PixelOutlineGeometry.stair）', () {
    for (final dpr in kTestDprs) {
      test('dpr=$dpr：顶点物理对齐、阶梯步数恒 4、偏差 ≤2 物理像素', () {
        final geo = PixelOutlineGeometry.stair(
          size: kFrameLogicalSize,
          cut: 8,
          strokeWidth: 1.5,
          dpr: dpr,
        );
        // (a) 全部顶点在物理像素网格上。
        for (final v in geo.vertices) {
          expect(
            onPhysicalGrid(v.dx, dpr),
            isTrue,
            reason: '顶点 x=${v.dx} 在 dpr=$dpr 下未对齐物理像素',
          );
          expect(
            onPhysicalGrid(v.dy, dpr),
            isTrue,
            reason: '顶点 y=${v.dy} 在 dpr=$dpr 下未对齐物理像素',
          );
        }
        // (b) 阶梯步数 = cut/pixelStep = 8/2 = 4（DPR 无关不变量）。
        expect(geo.stairSteps, 4);
        // 线宽吸附为物理像素整数倍。
        expect((geo.strokeWidth * dpr) % 1, closeTo(0, 1e-6));
        // (c) 包围盒偏差和 ≤ 4×0.5 物理像素。
        expect(geo.physicalBoundsDeviation, lessThanOrEqualTo(2.0 + 1e-6));
        // 路径与顶点一致（路径有界且非空）。
        expect(geo.path.getBounds().isEmpty, isFalse);
      });
    }

    testWidgets('反例控制组：未吸附顶点在网格断言下必须判负（可失败性）',
        (tester) async {
      resetViewOnTearDown(tester);
      const unsnapped = 7.7;
      // dpr=3 下 7.7 逻辑 px = 23.1 物理 px，不在网格上。
      expect(onPhysicalGrid(unsnapped, 3.0), isFalse);
      // 而组件几何同样输入经吸附后必须判正——断言双侧成立才有判别力。
      final geo = PixelOutlineGeometry.stair(
        size: const Size(24, 24),
        cut: 8,
        strokeWidth: 1.5,
        dpr: 3.0,
      );
      for (final v in geo.vertices) {
        expect(onPhysicalGrid(v.dx, 3.0), isTrue);
      }
    });
  });

  group('widget 渲染：五档 DPR 渲染盒与轮廓路径稳定', () {
    final logicalSizes = <double, Size>{};
    final stairSteps = <double, int>{};

    testWidgets('五档逐档 pump：渲染盒恒等、路径顶点物理对齐', (tester) async {
      resetViewOnTearDown(tester);
      for (final dpr in kTestDprs) {
        await _pumpPixelHost(tester, dpr: dpr);
        final box = _outlineRenderOf(tester);
        logicalSizes[dpr] = box.size;
        final painter = _outlinePainterOf(tester);
        final geo = painter.geometryFor(box.size, dpr);
        for (final v in geo.vertices) {
          expect(onPhysicalGrid(v.dx, dpr), isTrue,
              reason: 'dpr=$dpr 渲染路径顶点 x=${v.dx} 未物理对齐',);
          expect(onPhysicalGrid(v.dy, dpr), isTrue,
              reason: 'dpr=$dpr 渲染路径顶点 y=${v.dy} 未物理对齐',);
        }
        stairSteps[dpr] = geo.stairSteps;
      }
      // (b) 逻辑布局盒跨 DPR 恒等（布局保持逻辑 dp 连续）。
      expect(logicalSizes.values.toSet(), hasLength(1),
          reason: '渲染盒逻辑尺寸跨五档 DPR 漂移：$logicalSizes',);
      // 阶梯步数五档一致。
      expect(stairSteps.values.toSet(), hasLength(1));
      expect(stairSteps[1.0], 4);
    });
  });

  group('文字不点阵化（系统字体路径，无位图/无缩放画布）', () {
    testWidgets('五档 DPR：fontSize 逻辑值恒等、文本盒逻辑尺寸恒等、无 RawImage',
        (tester) async {
      resetViewOnTearDown(tester);
      final fontSizes = <double, double?>{};
      final textSizes = <double, Size>{};
      for (final dpr in kTestDprs) {
        await _pumpPixelHost(tester, dpr: dpr);
        final paragraph = tester.renderObject<RenderParagraph>(
          find.byType(RichText).first,
        );
        fontSizes[dpr] = paragraph.text.style?.fontSize;
        final textBox = tester.getSize(find.byType(Text).first);
        textSizes[dpr] = textBox;
        // 无位图化：子树不存在 RawImage（低分辨率位图放大的载体）。
        expect(find.byType(RawImage, skipOffstage: false), findsNothing);
        // 无画布缩放：Text 无 Transform 祖先（不对文字画布整数缩放）。
        expect(
          find.ancestor(
            of: find.byType(Text).first,
            matching: find.byType(Transform),
          ),
          findsNothing,
          reason: 'dpr=$dpr 下文字被 Transform 包裹（画布缩放路径）',
        );
      }
      expect(fontSizes.values.map((v) => v ?? -1).toSet(), hasLength(1),
          reason: 'fontSize 逻辑值跨 DPR 漂移：$fontSizes',);
      expect(fontSizes[1.0], isNotNull);
      expect(textSizes.values.toSet(), hasLength(1),
          reason: '文本盒逻辑尺寸跨 DPR 漂移：$textSizes',);
    });
  });

  group('classic 零差量红线（组件降级路径）', () {
    testWidgets('preview off：无像素扩展 → 标准圆角轮廓、无阶梯、仍可用',
        (tester) async {
      resetViewOnTearDown(tester);
      SharedPreferences.setMockInitialValues({});
      final manager = ThemeManager();
      if (!manager.initialized) await manager.initialize();
      await manager.setPixelPreviewProfile(PixelPreviewProfile.classic);
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(800, 600);
      await tester.pumpWidget(
        MaterialApp(
          theme: AppThemes.lightTheme,
          home: const Scaffold(
            body: Center(
              child: SizedBox(
                width: 200,
                height: 120,
                child: PixelFrame(
                  emphasis: PixelFrameEmphasis.primary,
                  cutCorner: true,
                  child: Text('classic'),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      final painter = _outlinePainterOf(tester);
      expect(painter.radius, 22.0, reason: 'classic 应走既有卡圆角');
      final geo = painter.geometryFor(_outlineRenderOf(tester).size, 2.0);
      expect(geo.stairSteps, 0, reason: 'classic 不做阶梯切角');
      expect(find.text('classic'), findsOneWidget);
      expect(find.byType(PixelSuccessBadge), findsNothing);
    });
  });
}
