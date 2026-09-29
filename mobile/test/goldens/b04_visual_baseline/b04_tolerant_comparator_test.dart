/// B04TolerantGoldenComparator 带界单测（V3-FIX-383，wt702；FIX-581 扩）。
///
/// 单位口径钉死：flutter_test `ComparisonResult.diffPercent` 是**分数**
/// （pixelDiffCount / totalPixels ∈ [0,1]，SDK _goldens_io.dart:254
/// `final double diffPercent = pixelDiffCount / totalPixels;` 实证）。
/// 容差 [B04TolerantGoldenComparator.diffPercentTolerance] = 0.005 表示
/// 0.5%（修前误写 0.5 与分数直比 = 实际放行 50% 像素差，0.18% 环境漂移
/// 与 49% 布局崩坏同判过）。
///
/// 带界三类（V3-FIX-383 任务卡要求，FIX-581 起显式钉**本地语义**
/// `ciEnvironment: false`——CI runner 上本文件也会跑，若走真实环境检测
/// 会拿到 CI 放宽界，带界断言即失确定性）：
/// - 0.4%（120/30000 px，带内）→ 判过；
/// - 0.6%（180/30000 px，超带）→ 判挂（修前 0.5 容差下判过）；
/// - 49%（14700/30000 px，真实布局崩坏量级）→ 判挂（修前判过）。
/// 另钉：0 差判过（passed 直通）、0.5% 带界含等号判过、与
/// golden_family_drift_guard 的 kGoldenEnvDriftBand（V3-FIX-368 环境
/// 噪声带）同值对齐。
///
/// FIX-581 增钉（CI 跨机容差，实锚 CI53 run 36546247412）：
/// - CI 语义（`ciEnvironment: true`）：0.62% 实锚量级（186/30000）判过、
///   1.0% 放宽带界含等号（300/30000）判过、1.1%（330/30000）判挂；
/// - 同一 0.62% 差异在本地语义（`ciEnvironment: false`）仍判挂——
///   「本地阈值/口径一字不动」红线的机制级实证；
/// - 失败投递归属：超带失败必须以 TestFailure 落在自己的
///   `expectLater(matchesGoldenFile)` await 上（takeException 保持 null）。
///   修前抛 FlutterError 穿透 SDK binding.runAsync 的 reportError 通道
///   （binding.dart:2733-2744），失败被吞进框架异常队列、expectLater
///   正常返回，错误被下一轮迭代 takeException 错位取走（CI53 实证：
///   paperDay golden 失败挂上「PixelPreviewProfile.dusk 任务列表异常」）。
///
/// 测法：纯图像构造（PictureRecorder 白底 + 指定数量红像素 → PNG），
/// golden 落系统临时目录——不经、不触碰仓库内任何 golden 基线 PNG。
library;

// ignore_for_file: avoid_print

import 'dart:io';
import 'dart:typed_data' show ByteData, Uint8List;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../golden_family_drift_guard.dart' show kGoldenEnvDriftBand;
import 'b04_harness.dart';

const int _width = 200;
const int _height = 150;

/// 总像素面 30000：120px=0.4%、150px=0.5%、180px=0.6%、186px=0.62%、
/// 300px=1.0%、330px=1.1%、14700px=49%。
const int _totalPixels = _width * _height;

/// 画白底 [_width]×[_height] 图像并置入 [diffPixels] 个红像素（确定性
/// 逐像素摆放），编码 PNG 字节。红白通道差非零，逐像素精确计数。
Future<Uint8List> _encodeImage(int diffPixels) async {
  final recorder = ui.PictureRecorder();
  final canvas = ui.Canvas(recorder);
  canvas.drawRect(
    ui.Rect.fromLTWH(0, 0, _width.toDouble(), _height.toDouble()),
    ui.Paint()..color = const ui.Color(0xFFFFFFFF),
  );
  for (var i = 0; i < diffPixels; i++) {
    final x = (i % _width).toDouble();
    final y = (i ~/ _width).toDouble();
    canvas.drawRect(
      ui.Rect.fromLTWH(x, y, 1, 1),
      ui.Paint()..color = const ui.Color(0xFFFF0000),
    );
  }
  final picture = recorder.endRecording();
  final image = await picture.toImage(_width, _height);
  picture.dispose();
  final ByteData? data = await image.toByteData(format: ui.ImageByteFormat.png);
  image.dispose();
  if (data == null) {
    throw StateError('PNG 编码失败（b04 容差单测构造面）');
  }
  return data.buffer.asUint8List();
}

/// 本 SDK `runAsync<T>` 签名返回 `Future<T?>`（binding.dart:1102）——真值
/// 路径不会是 null，包一层去 nullable，让后续类型面干净。
Future<T> _runRealAsync<T>(WidgetTester tester, Future<T> Function() job) async {
  final result = await tester.runAsync(job);
  if (result == null) {
    throw StateError('runAsync 返回 null（b04 容差单测构造面）');
  }
  return result;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  /// 每例独立临时目录：golden 写盘 + 失败产物（generateFailureOutput 的
  /// failures/）都隔离在系统临时区，测后即删。
  ///
  /// [ciEnvironment] 显式注入比较器环境语义：本地带界断言一律 `false`
  /// （CI runner 上也跑本文件，必须钉死确定性，不走真实环境检测）；
  /// CI 语义断言传 `true` 模拟 GitHub Actions。
  Future<(B04TolerantGoldenComparator, Uri)> _setUpGolden(
    WidgetTester tester, {
    bool ciEnvironment = false,
  }) async {
    final Directory tempDir = await _runRealAsync(
      tester,
      () => Directory.systemTemp.createTemp('b04_tolerant_wt702'),
    );
    addTearDown(() => tempDir.deleteSync(recursive: true));
    final comparator = B04TolerantGoldenComparator(
      Uri.file('${tempDir.path}/fake_b04_test.dart'),
      ciEnvironment: ciEnvironment,
    );
    final goldenUri = Uri.parse('golden.png');
    final goldenBytes = await _runRealAsync(tester, () => _encodeImage(0));
    await _runRealAsync(
      tester,
      () => File('${tempDir.path}/golden.png').writeAsBytes(goldenBytes),
    );
    return (comparator, goldenUri);
  }

  testWidgets('常量钉死：本地容差 0.005（分数口径）= 0.5%，与 V3-FIX-368 环境带同值；CI 界 = 基带 × 2.0',
      (tester) async {
    expect(B04TolerantGoldenComparator.diffPercentTolerance, 0.005);
    expect(
      B04TolerantGoldenComparator.diffPercentTolerance,
      kGoldenEnvDriftBand,
      reason: 'B-04 容差与 golden_family_drift_guard 环境噪声带应同口径'
          '（都是 0.5% 分数），避免两处语义漂移',
    );
    expect(kCiGoldenToleranceScale, 2.0);
    // 阈值原值打印实证：本地逐字节口径不变（非静默放宽红线），CI = 1.0%。
    final localTolerance = b04GoldenTolerance(ciEnvironment: false);
    final ciTolerance = b04GoldenTolerance(ciEnvironment: true);
    print('FIX-581 golden 容差：本地(local)= $localTolerance（0.005 原值'
        '不变）；CI(GITHUB_ACTIONS)= $ciTolerance（0.005 × '
        '$kCiGoldenToleranceScale）');
    expect(localTolerance, 0.005, reason: '本地阈值必须等于修前原值');
    expect(ciTolerance, 0.010);
  });

  testWidgets('0 差 → passed 直通判过', (tester) async {
    final (comparator, goldenUri) = await _setUpGolden(tester);
    final candidate = await _runRealAsync(tester, () => _encodeImage(0));
    final passed = await _runRealAsync(
      tester,
      () => comparator.compare(candidate, goldenUri),
    );
    expect(passed, isTrue);
  });

  testWidgets('0.4% 差（120/30000，带内）→ 判过', (tester) async {
    final (comparator, goldenUri) = await _setUpGolden(tester);
    final candidate = await _runRealAsync(tester, () => _encodeImage(120));
    final passed = await _runRealAsync(
      tester,
      () => comparator.compare(candidate, goldenUri),
    );
    expect(passed, isTrue);
  });

  testWidgets('0.5% 差（150/30000，带界含等号）→ 判过', (tester) async {
    final (comparator, goldenUri) = await _setUpGolden(tester);
    final candidate = await _runRealAsync(tester, () => _encodeImage(150));
    final passed = await _runRealAsync(
      tester,
      () => comparator.compare(candidate, goldenUri),
    );
    expect(passed, isTrue);
  });

  /// 判挂路径：SDK `runAsync` 会捕获并 reportError 回调体抛错后返回
  /// null（binding.dart runAsync 实现），故在回调体内 try/catch 收集
  /// 异常，不落框架异常通道；顺带断言失败消息的百分数
  /// （SDK 失败消息 = `(diffPercent * 100).toStringAsFixed(2)%`）。
  ///
  /// FIX-581：捕获类型钉死为 TestFailure——SDK MatchesGoldenFile.matchAsync
  /// （_matchers_io.dart:123-131）只 `on TestFailure catch`，抛其他类型
  /// 会穿透进 runAsync 的 reportError 通道被吞（修前 FlutterError 即此
  /// 命运，golden 失败被下一轮 takeException 错位取走，见 CI53）。
  Future<Object> _expectCompareThrows(
    WidgetTester tester,
    B04TolerantGoldenComparator comparator,
    Uri goldenUri,
    Uint8List candidate,
  ) async {
    Object? thrown;
    await tester.runAsync(() async {
      try {
        await comparator.compare(candidate, goldenUri);
      } catch (error) {
        thrown = error;
      }
    });
    if (thrown == null) {
      fail('期望 comparator 对超带差异抛 TestFailure，实际判过');
    }
    expect(thrown, isA<TestFailure>(),
        reason: 'compare() 失败必须抛 TestFailure（SDK matchAsync 契约），'
            '抛其他类型会被 binding.runAsync 吞进 reportError 通道、'
            'golden 失败被下一轮 takeException 错位归属',);
    expect(thrown, isNot(isA<FlutterError>()));
    return thrown!;
  }

  testWidgets('0.6% 差（180/30000，超带）→ 本地语义判挂 TestFailure（修前判过）',
      (tester) async {
    final (comparator, goldenUri) = await _setUpGolden(tester);
    final candidate = await _runRealAsync(tester, () => _encodeImage(180));
    final error = await _expectCompareThrows(
      tester,
      comparator,
      goldenUri,
      candidate,
    );
    expect((error as TestFailure).message, contains('0.60%'),
        reason: '失败消息是百分数口径（diffPercent×100），钉死分数↔百分比换算语义',);
  });

  testWidgets('49% 差（14700/30000，真实布局崩坏量级）→ 判挂（修前 0.5 直比判过）',
      (tester) async {
    final (comparator, goldenUri) = await _setUpGolden(tester);
    final candidate = await _runRealAsync(tester, () => _encodeImage(14700));
    final error = await _expectCompareThrows(
      tester,
      comparator,
      goldenUri,
      candidate,
    );
    expect((error as TestFailure).message, contains('49.00%'),
        reason: '失败消息是百分数口径（diffPercent×100），钉死分数↔百分比换算语义',);
  });

  // ───────────── FIX-581：CI 跨机容差两态钉（实锚 CI53 0.62%） ─────────────

  testWidgets('CI 语义 0.62% 差（186/30000，CI53 paperDay 实锚量级）→ 判过',
      (tester) async {
    final (comparator, goldenUri) =
        await _setUpGolden(tester, ciEnvironment: true);
    expect(comparator.effectiveTolerance, 0.010);
    final candidate = await _runRealAsync(tester, () => _encodeImage(186));
    final passed = await _runRealAsync(
      tester,
      () => comparator.compare(candidate, goldenUri),
    );
    expect(passed, isTrue);
  });

  testWidgets('本地语义同帧 0.62% 差 → 仍判挂（本地阈值一字不动的机制实证）',
      (tester) async {
    final (comparator, goldenUri) =
        await _setUpGolden(tester);
    expect(comparator.effectiveTolerance, 0.005);
    final candidate = await _runRealAsync(tester, () => _encodeImage(186));
    final error = await _expectCompareThrows(
      tester,
      comparator,
      goldenUri,
      candidate,
    );
    expect((error as TestFailure).message, contains('0.62%'));
  });

  testWidgets('CI 语义 1.0% 差（300/30000，放宽带界含等号）→ 判过', (tester) async {
    final (comparator, goldenUri) =
        await _setUpGolden(tester, ciEnvironment: true);
    final candidate = await _runRealAsync(tester, () => _encodeImage(300));
    final passed = await _runRealAsync(
      tester,
      () => comparator.compare(candidate, goldenUri),
    );
    expect(passed, isTrue);
  });

  testWidgets('CI 语义 1.1% 差（330/30000，超放宽带）→ 判挂（CI 粗门仍在）',
      (tester) async {
    final (comparator, goldenUri) =
        await _setUpGolden(tester, ciEnvironment: true);
    final candidate = await _runRealAsync(tester, () => _encodeImage(330));
    final error = await _expectCompareThrows(
      tester,
      comparator,
      goldenUri,
      candidate,
    );
    expect((error as TestFailure).message, contains('1.10%'));
  });

  // ─────────── FIX-581：失败投递归属钉（matchesGoldenFile 全链路） ───────────

  testWidgets('超带失败经 matchesGoldenFile 落在自己的 expectLater await（TestFailure），'
      '不进框架异常队列（takeException 保持 null，修前泄漏实证 CI53 dusk 错位）',
      (tester) async {
    // 本钉测的是 B04 比较器经 matchesGoldenFile 全链路的投递语义——
    // 显式装比较器（g01 setUpAll 同款）。SDK 默认 LocalFileComparator
    // 超带也抛 FlutterError（_goldens_io.dart:108），走 runAsync 异步
    // 记账路径（expectLater 静默通过）——恰是 CI53 泄漏的对照面。
    b04InstallTolerantComparator();
    // 视口钉 200×150 @1.0：captureImage 捕根 RepaintBoundary，与临时
    // golden 同尺寸，确保失败路径是像素超带而非尺寸不匹配。
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(200, 150);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final tempDir = await _runRealAsync(
      tester,
      () => Directory.systemTemp.createTemp('b04_leak_pin_f581'),
    );
    addTearDown(() => tempDir.deleteSync(recursive: true));
    // golden = 白底；渲染面 = 红底 → 100% 差，必超带。
    final goldenBytes = await _runRealAsync(tester, () => _encodeImage(0));
    final goldenFile = File('${tempDir.path}/leak_pin_golden.png');
    await _runRealAsync(
      tester,
      () => goldenFile.writeAsBytes(goldenBytes),
    );

    await tester.pumpWidget(
      const ColoredBox(color: ui.Color(0xFFFF0000)),
    );
    await tester.pump();

    // absolute file URI：LocalFileComparator.basedir.resolve(绝对路径) =
    // 原样返回，golden 落临时区不触碰仓库。内层失败 future 同步交给外层
    // throwsA（无 await 间隙，避免未处理异步错误逃逸）。
    await expectLater(
      expectLater(
        find.byType(ColoredBox),
        matchesGoldenFile(Uri.file(goldenFile.path)),
      ),
      throwsA(isA<TestFailure>()),
    );
    expect(
      tester.takeException(),
      isNull,
      reason: 'golden 失败必须落在自己的 expectLater await 上；'
          '泄漏进框架异常队列会让下一轮迭代 takeException 错位取走'
          '（CI53「PixelPreviewProfile.dusk 任务列表异常」错位根因）',
    );
  });
}
