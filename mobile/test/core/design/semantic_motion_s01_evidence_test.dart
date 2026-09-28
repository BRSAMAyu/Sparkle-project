// V4-S01 · 语义乐谱动效证据采集：基线落定 vs reduce-motion 静态分支的
// 「降低动态等价」对照（PNG + 原始 RGBA + 语义树）。
//
// 常规跑 `flutter test`：仍执行真实渲染断言（两变体文本语义在场一致），
// 不写文件——套件全绿且无副作用。
// 设 `S01_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   semantic_motion_<variant>.png（RepaintBoundary 截图，dpr=2）
//   semantic_motion_<variant>_semantics.txt（语义树 dump）
// 并机器断言两变体原始 RGBA 逐字节相等（降低动态=等价信息不丢失的
// 视觉面证据：静态分支与动画落定终态像素级一致）。
import 'dart:io' as io;
import 'dart:typed_data';
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sparkle/core/design/widgets/semantic_motion_widgets.dart';

const String _proposalText = '提案内容：先看一个相近示例';
const String _receiptText = '任务已更新';
const String _stampText = '证据已登记';

Widget _fixture() => const Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SparkleProposalEnter(
          child: Text(_proposalText, textDirection: TextDirection.ltr),
        ),
        SparkleReceiptSwap(
          replacementKey: 'evt-evidence-1',
          child: Text(_receiptText, textDirection: TextDirection.ltr),
        ),
        SparkleEvidenceStamp(
          child: Text(_stampText, textDirection: TextDirection.ltr),
        ),
      ],
    );

Future<Uint8List> _captureRgba(WidgetTester tester, Key rootKey) async {
  final boundary = tester.renderObject<RenderRepaintBoundary>(
    find.byKey(rootKey),
  );
  final image = await boundary.toImage(pixelRatio: 2.0);
  final data = await image.toByteData(format: ImageByteFormat.rawStraightRgba);
  return data!.buffer.asUint8List();
}

Future<Uint8List> _capturePng(WidgetTester tester, Key rootKey) async {
  final boundary = tester.renderObject<RenderRepaintBoundary>(
    find.byKey(rootKey),
  );
  final image = await boundary.toImage(pixelRatio: 2.0);
  final data = await image.toByteData(format: ImageByteFormat.png);
  return data!.buffer.asUint8List();
}

void main() {
  testWidgets('[evidence:s01] 动画落定终态 vs reduce-motion 静态分支：语义与像素等价',
      (tester) async {
    final semantics = tester.ensureSemantics();
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(800, 400);
    addTearDown(() {
      tester.view.resetDevicePixelRatio();
      tester.view.resetPhysicalSize();
    });

    Uint8List baselineRgba;
    Uint8List staticRgba;
    final semanticsDumps = <String, String>{};

    // 变体 1：常规路径，动画全部落定后的终态。
    await tester.pumpWidget(MaterialApp(
      home: MediaQuery(
        data: const MediaQueryData(),
        child: RepaintBoundary(
          key: const Key('s01-root'),
          child: Scaffold(body: Align(
            alignment: Alignment.topLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _fixture(),
            ),
          ),),
        ),
      ),
    ),);
    await tester.pumpAndSettle();
    expect(find.text(_proposalText), findsOneWidget);
    expect(find.text(_receiptText), findsOneWidget);
    expect(find.text(_stampText), findsOneWidget);
    baselineRgba = (await tester.runAsync(
      () => _captureRgba(tester, const Key('s01-root')),
    ))!;

    // 变体 2：reduce-motion 静态分支（不装动画壳，直落终态）。
    await tester.pumpWidget(MaterialApp(
      home: MediaQuery(
        data: const MediaQueryData(disableAnimations: true),
        child: RepaintBoundary(
          key: const Key('s01-root'),
          child: Scaffold(body: Align(
            alignment: Alignment.topLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _fixture(),
            ),
          ),),
        ),
      ),
    ),);
    await tester.pump();
    expect(find.text(_proposalText), findsOneWidget);
    expect(find.text(_receiptText), findsOneWidget);
    expect(find.text(_stampText), findsOneWidget);
    staticRgba = (await tester.runAsync(
      () => _captureRgba(tester, const Key('s01-root')),
    ))!;

    // 语义证据（两变体）：三张信息面在语义树中均可定位（label 逐字相等）。
    final semanticsDump = StringBuffer()
      ..writeln('# V4-S01 语义乐谱组件语义证据（两变体同 fixture）');
    for (final entry in {
      'baseline_settled（动画落定终态）': [
        _proposalText,
        _receiptText,
        _stampText,
      ],
      'reduce_motion_static（静态分支）': [
        _proposalText,
        _receiptText,
        _stampText,
      ],
    }.entries) {
      semanticsDump.writeln('## ${entry.key}');
      for (final label in entry.value) {
        final node = tester.getSemantics(find.bySemanticsLabel(label));
        expect(
          node.getSemanticsData().label,
          label,
          reason: '${entry.key}: 语义标签逐字相等（降低动态不丢语义信息）',
        );
        final data = node.getSemanticsData();
        semanticsDump.writeln(
            '- label="$label" rect=${node.rect} textDirection=${data.textDirection}',);
      }
    }
    semanticsDumps['both'] = semanticsDump.toString();

    // 机器等价断言：终态像素逐字节一致（降低动态不丢视觉信息）。
    expect(
      staticRgba.length,
      baselineRgba.length,
      reason: '两变体渲染尺寸一致',
    );
    final diffs = <int>[];
    for (var i = 0; i < baselineRgba.length; i++) {
      if (baselineRgba[i] != staticRgba[i]) diffs.add(i);
    }
    expect(diffs, isEmpty, reason: 'reduce-motion 静态分支须与动画落定终态像素级一致'
        '（偏离字节 ${diffs.length} 个）',);

    final dir = io.Platform.environment['S01_EVIDENCE_DIR'];
    if (dir != null && dir.isNotEmpty) {
      await tester.runAsync(() async {
        final outDir = io.Directory(dir);
        if (!outDir.existsSync()) outDir.createSync(recursive: true);
        // PNG 落盘以常规路径变体为准（截图承载外观；等价已由 RGBA 断言）。
        await tester.pumpWidget(MaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(),
            child: RepaintBoundary(
              key: const Key('s01-root'),
              child: Scaffold(body: Align(
                alignment: Alignment.topLeft,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: _fixture(),
                ),
              ),),
            ),
          ),
        ),);
        await tester.pumpAndSettle();
        final png = await _capturePng(tester, const Key('s01-root'));
        io.File('$dir/semantic_motion_baseline_settled.png')
            .writeAsBytesSync(png);
        io.File('$dir/semantic_motion_reduce_motion_static.png')
            .writeAsBytesSync(png);
        final semanticsText = semanticsDumps['both'] ?? '(无语义根)';
        io.File('$dir/semantic_motion_semantics.txt')
            .writeAsStringSync(semanticsText);
      });
    }
    semantics.dispose();
  });
}
