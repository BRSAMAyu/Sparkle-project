/// B04TolerantGoldenComparator 带界单测（V3-FIX-383，wt702）。
///
/// 单位口径钉死：flutter_test `ComparisonResult.diffPercent` 是**分数**
/// （pixelDiffCount / totalPixels ∈ [0,1]，SDK _goldens_io.dart:254
/// `final double diffPercent = pixelDiffCount / totalPixels;` 实证）。
/// 容差 [B04TolerantGoldenComparator.diffPercentTolerance] = 0.005 表示
/// 0.5%（修前误写 0.5 与分数直比 = 实际放行 50% 像素差，0.18% 环境漂移
/// 与 49% 布局崩坏同判过）。
///
/// 带界三类（任务卡要求）：
/// - 0.4%（120/30000 px，带内）→ 判过；
/// - 0.6%（180/30000 px，超带）→ 判挂（修前 0.5 容差下判过）；
/// - 49%（14700/30000 px，真实布局崩坏量级）→ 判挂（修前判过）。
/// 另钉：0 差判过（passed 直通）、0.5% 带界含等号判过、与
/// golden_family_drift_guard 的 kGoldenEnvDriftBand（V3-FIX-368 环境
/// 噪声带）同值对齐。
///
/// 测法：纯图像构造（PictureRecorder 白底 + 指定数量红像素 → PNG），
/// golden 落系统临时目录——不经、不触碰仓库内任何 golden 基线 PNG。
library;

import 'dart:io';
import 'dart:typed_data' show ByteData, Uint8List;
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show FlutterError;
import 'package:flutter_test/flutter_test.dart';

import '../golden_family_drift_guard.dart' show kGoldenEnvDriftBand;
import 'b04_harness.dart';

const int _width = 200;
const int _height = 150;

/// 总像素面 30000：120px=0.4%、150px=0.5%、180px=0.6%、14700px=49%。
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
  Future<(B04TolerantGoldenComparator, Uri)> _setUpGolden(
    WidgetTester tester,
  ) async {
    final Directory tempDir = await _runRealAsync(
      tester,
      () => Directory.systemTemp.createTemp('b04_tolerant_wt702'),
    );
    addTearDown(() => tempDir.deleteSync(recursive: true));
    final comparator = B04TolerantGoldenComparator(
      Uri.file('${tempDir.path}/fake_b04_test.dart'),
    );
    final goldenUri = Uri.parse('golden.png');
    final goldenBytes = await _runRealAsync(tester, () => _encodeImage(0));
    await _runRealAsync(
      tester,
      () => File('${tempDir.path}/golden.png').writeAsBytes(goldenBytes),
    );
    return (comparator, goldenUri);
  }

  testWidgets('常量钉死：容差 0.005（分数口径）= 0.5%，与 V3-FIX-368 环境带同值',
      (tester) async {
    expect(B04TolerantGoldenComparator.diffPercentTolerance, 0.005);
    expect(
      B04TolerantGoldenComparator.diffPercentTolerance,
      kGoldenEnvDriftBand,
      reason: 'B-04 容差与 golden_family_drift_guard 环境噪声带应同口径'
          '（都是 0.5% 分数），避免两处语义漂移',
    );
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
  /// FlutterError，不落框架异常通道；顺带断言失败消息的百分数
  /// （SDK 失败消息 = `(diffPercent * 100).toStringAsFixed(2)%`）。
  Future<FlutterError> _expectCompareThrows(
    WidgetTester tester,
    B04TolerantGoldenComparator comparator,
    Uri goldenUri,
    Uint8List candidate,
  ) async {
    FlutterError? thrown;
    await tester.runAsync(() async {
      try {
        await comparator.compare(candidate, goldenUri);
      } on FlutterError catch (error) {
        thrown = error;
      }
    });
    if (thrown == null) {
      fail('期望 comparator 对超带差异抛 FlutterError，实际判过');
    }
    return thrown!;
  }

  testWidgets('0.6% 差（180/30000，超带）→ 判挂 FlutterError（修前判过）',
      (tester) async {
    final (comparator, goldenUri) = await _setUpGolden(tester);
    final candidate = await _runRealAsync(tester, () => _encodeImage(180));
    final error = await _expectCompareThrows(
      tester,
      comparator,
      goldenUri,
      candidate,
    );
    expect(error.message, contains('0.60%'), reason: '失败消息是百分数口径'
        '（diffPercent×100），钉死分数↔百分比换算语义');
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
    expect(error.message, contains('49.00%'), reason: '失败消息是百分数口径'
        '（diffPercent×100），钉死分数↔百分比换算语义');
  });
}
