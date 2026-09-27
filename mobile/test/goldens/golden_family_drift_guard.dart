/// V3-FIX-368（wt676 登记，wt692 落地）· golden 套件环境守卫。
///
/// 背景：dashboard golden 基线由异构渲染环境签发，非签发机上整族
/// （跨变体）出现等幅小像素漂移——本机实测 4 变体 × 0.18%（7632px）
/// FAIL 且与 pristine main 逐位同签名（wt676 A/B 双跑实证）。此边界下：
/// - 套件红不能证伪任何改动（既有环境漂移）；
/// - 「skip=通过」或他机 `--update-goldens` 强刷都会产出假绿/毁真源。
///
/// 裁决 (b) 最小诚实面：套件对**整族带内漂移**显式 SKIP 并标注原因
/// （非静默过、非红）；对**带外漂移**与**非整族签名**（部分变体精确）
/// 硬 FAIL——环境漂移必然整族等幅，单独/不等幅漂移按真实回归排查。
/// golden 基线内容零触碰；`--update-goldens` 仅限基线签发机。
///
/// 单位口径：flutter_test `ComparisonResult.diffPercent` 是**分数**
/// （pixelDiffCount / totalPixels ∈ [0,1]），0.18% = 0.0018。带值
/// [kGoldenEnvDriftBand] = 0.005（0.5%）取 B-04
/// `TolerantGoldenComparator` 容差先例的**文档意图**；其代码以 0.5 与
/// 分数直比（实际 50% 容差）已登记 V3-FIX-383 归 wt667 在航面处置。
library;

import 'dart:typed_data' show ByteData, Uint8List;
import 'dart:ui' as ui show ImageByteFormat;

import 'package:flutter/rendering.dart' show OffsetLayer;
import 'package:flutter_test/flutter_test.dart';

/// 环境噪声带（分数口径）：0.5%。
///
/// 依据：帧相位/相对时间类噪声实测 ≈0.01%（B-04 容差先例注释）；跨机
/// 整族渲染漂移实测 ≈0.18%（wt676/wt692 A/B）；真实布局回归远超此界。
const double kGoldenEnvDriftBand = 0.005;

/// 单变体比对结论。
enum GoldenVariantVerdict {
  /// 逐位一致。
  exactMatch,

  /// 带内小漂移（≤0.5%）——可能是环境签名差，也可能被带掩盖的微回归。
  envBandDrift,

  /// 超带（>0.5%，含 golden 缺失/解码失败的 1.0 语义）。
  overBandDrift,
}

/// 整族裁决。
enum GoldenFamilyVerdict {
  /// 全变体逐位一致——真绿。
  suitePass,

  /// 全变体（≥2 个）带内漂移——整族等幅环境签名差，显式 SKIP。
  familyEnvironmentDrift,

  /// 任一变体超带——真实回归（或基线缺失），FAIL。
  regression,

  /// 精确/带内漂移混合——环境漂移应整族等幅，混合签名按回归排查，FAIL。
  suspiciousPartialDrift,
}

/// 单变体比对结果记录。
class GoldenVariantOutcome {
  const GoldenVariantOutcome(this.variant, this.diffPercent, [this.note]);

  /// 变体名（进入 SKIP/FAIL 原因串，供人读）。
  final String variant;

  /// diff 分数（0.18% = 0.0018）；golden 缺失/解码失败按 1.0 记。
  final double diffPercent;

  /// 附加说明（如缺失路径），可为 null。
  final String? note;

  GoldenVariantVerdict get verdict => verdictFor(diffPercent);

  /// 人读百分比（两位小数）。
  String get percentLabel => '${(diffPercent * 100).toStringAsFixed(2)}%';
}

/// diff 分数 → 单变体结论（带界含等号：0.5% 恰在带内）。
GoldenVariantVerdict verdictFor(double diffPercent) {
  if (diffPercent <= 0.0) {
    return GoldenVariantVerdict.exactMatch;
  }
  if (diffPercent <= kGoldenEnvDriftBand) {
    return GoldenVariantVerdict.envBandDrift;
  }
  return GoldenVariantVerdict.overBandDrift;
}

/// 整族裁决（纯函数）。
///
/// - 全 exact → [GoldenFamilyVerdict.suitePass]；
/// - 全 drifted 且漂移变体 ≥2（整族等幅签名）→
///   [GoldenFamilyVerdict.familyEnvironmentDrift]；
/// - 任一 overBand → [GoldenFamilyVerdict.regression]；
/// - 其余（精确/漂移混合、单变体漂移）→
///   [GoldenFamilyVerdict.suspiciousPartialDrift]。
GoldenFamilyVerdict classifyGoldenFamily(List<GoldenVariantOutcome> outcomes) {
  if (outcomes.isEmpty) {
    return GoldenFamilyVerdict.suitePass;
  }
  final verdicts = outcomes.map((o) => o.verdict).toList();
  if (verdicts.any((v) => v == GoldenVariantVerdict.overBandDrift)) {
    return GoldenFamilyVerdict.regression;
  }
  final drifted = verdicts
      .where((v) => v == GoldenVariantVerdict.envBandDrift)
      .length;
  if (drifted == 0) {
    return GoldenFamilyVerdict.suitePass;
  }
  if (drifted == verdicts.length && drifted >= 2) {
    return GoldenFamilyVerdict.familyEnvironmentDrift;
  }
  return GoldenFamilyVerdict.suspiciousPartialDrift;
}

/// 整族环境漂移的 SKIP 原因（显式标注，非静默过）。
String familyDriftSkipReason(List<GoldenVariantOutcome> outcomes) {
  final detail =
      outcomes.map((o) => '${o.variant}=${o.percentLabel}').join(', ');
  return 'golden 环境守卫（V3-FIX-368）：整族带内漂移 $detail（带 0.5%）'
      '——基线为异构渲染环境签名，非本次改动回归；本机不得'
      ' --update-goldens（仅限基线签发机）。若本次未变更渲染环境'
      '（Flutter/OS 升级），请到签发机复核此带内漂移是否微回归。';
}

/// 超带回归的 FAIL 原因。
String familyRegressionFailReason(List<GoldenVariantOutcome> outcomes) {
  final over =
      outcomes.where((o) => o.verdict == GoldenVariantVerdict.overBandDrift);
  final detail = over
      .map(
        (o) => '${o.variant}=${o.percentLabel}'
            '${o.note == null ? '' : '（${o.note}）'}',
      )
      .join(', ');
  return 'golden 超带差异（>0.5% 带宽，V3-FIX-368 环境守卫）：$detail'
      '——真实回归或基线缺失，不属环境噪声；先排查本次改动，确认渲染'
      '管线变更后仅在基线签发机 --update-goldens 重建。';
}

/// 非整族签名（精确/漂移混合）的 FAIL 原因。
String familyPartialDriftFailReason(List<GoldenVariantOutcome> outcomes) {
  final drifted =
      outcomes.where((o) => o.verdict == GoldenVariantVerdict.envBandDrift);
  final exact =
      outcomes.where((o) => o.verdict == GoldenVariantVerdict.exactMatch);
  return 'golden 非整族漂移签名（V3-FIX-368 环境守卫）：漂移 '
      '${drifted.map((o) => o.variant).join('/')} vs 精确 '
      '${exact.map((o) => o.variant).join('/')}——环境漂移应整族等幅，'
      '混合签名更可能为局部微回归，请按回归排查（勿在本机'
      ' --update-goldens）。';
}

/// 渲染 [finder] 单个元素为 PNG 字节（复刻 flutter_test
/// `matchesGoldenFile` 的 captureImage→toByteData(png) 管线，含
/// runAsync 包裹）。
Future<Uint8List> renderGoldenPng(WidgetTester tester, Finder finder) async {
  final bytes = await tester.runAsync<ByteData?>(() async {
    final element = finder.evaluate().single;
    var renderObject = element.renderObject!;
    while (!renderObject.isRepaintBoundary) {
      renderObject = renderObject.parent!;
    }
    final layer = renderObject.debugLayer! as OffsetLayer;
    final image = await layer.toImage(renderObject.paintBounds);
    try {
      return await image.toByteData(format: ui.ImageByteFormat.png);
    } finally {
      image.dispose();
    }
  });
  if (bytes == null) {
    throw StateError('golden 环境守卫：PNG 编码失败');
  }
  return bytes.buffer.asUint8List();
}

/// 渲染字节对既有 golden 文件比对（不抛，结果进 [GoldenVariantOutcome]）。
///
/// golden 文件名相对测试文件目录解析（与 `matchesGoldenFile` 同基準，
/// 即默认 [LocalFileComparator] 的 basedir）。缺失/解码失败按
/// diffPercent=1.0 记（带外 → regression FAIL，指引签发机重建）。
Future<GoldenVariantOutcome> compareRenderedAgainstGolden({
  required WidgetTester tester,
  required String variant,
  required String goldenFileName,
  required Finder finder,
}) async {
  final bytes = await renderGoldenPng(tester, finder);
  final comparator = goldenFileComparator;
  if (comparator is! LocalFileComparator) {
    return GoldenVariantOutcome(
      variant,
      1.0,
      'comparator 非 LocalFileComparator（${comparator.runtimeType}），'
      '无法定位 golden 文件',
    );
  }
  final goldenUri = comparator.basedir.resolve(goldenFileName);
  final goldenBytes = await tester.runAsync<List<int>>(
    () => comparator.getGoldenBytes(goldenUri),
  );
  if (goldenBytes == null) {
    return GoldenVariantOutcome(variant, 1.0, 'golden 读取失败（runAsync）');
  }
  final result = await tester.runAsync(
    () => GoldenFileComparator.compareLists(bytes, goldenBytes),
  );
  if (result == null) {
    return GoldenVariantOutcome(variant, 1.0, '比对失败（runAsync null）');
  }
  final diffPercent = result.passed ? 0.0 : result.diffPercent;
  return GoldenVariantOutcome(variant, diffPercent);
}
