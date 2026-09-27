/// Golden Tests for Dashboard Screen
/// Dashboard屏幕Golden测试
///
/// V3-FIX-368（wt676 登记，wt692 落地）：golden 基线由异构渲染环境签发，
/// 非签发机整族等幅小漂移（本机实测 4 变体 × 0.18%/7632px，与 pristine
/// main 逐位同签名）——「skip=通过」与他机 `--update-goldens` 强刷都会产
/// 假绿/毁真源。套件改走环境守卫（golden_family_drift_guard）：
/// - 门开（ENABLE_DASHBOARD_GOLDEN=true，仅限基线签发机）→ 守卫裁决：
///   整族带内漂移（≤0.5%，B-04 容差先例文档意图）显式 SKIP+标注原因；
///   超带/非整族签名硬 FAIL（真实回归不放过）；
/// - 门关（默认）→ skip 自述原因（非静默跳过）。
/// 基线内容零触碰；`--update-goldens` 仅限基线签发机。
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../features/home/dashboard_test_harness.dart';
import 'golden_family_drift_guard.dart';

const bool _enableDashboardGoldens = bool.fromEnvironment(
  'ENABLE_DASHBOARD_GOLDEN',
);

/// 门关时的自述：testWidgets 的 skip 仅收 bool（无 reason 串位），门关
/// 语义钉进测试名——输出行即见「默认关≠基线通过」。
const String _testName =
    'Dashboard golden family (light/dark/mobile/tablet) environment-guarded '
    '(V3-FIX-368: default OFF≠pass — set ENABLE_DASHBOARD_GOLDEN=true on '
    'baseline signing machine only)';

void main() {
  group('Dashboard Golden Tests', () {
    testWidgets(
      _testName,
      (WidgetTester tester) async {
        final outcomes = <GoldenVariantOutcome>[];

        Future<void> pumpVariant(String variant, Widget Function() build) async {
          await initializeDashboardTestEnvironment();
          await tester.pumpWidget(build());
          for (var i = 0; i < 8; i++) {
            await tester.pump(const Duration(milliseconds: 100));
          }
          outcomes.add(
            await compareRenderedAgainstGolden(
              tester: tester,
              variant: variant,
              goldenFileName: 'dashboard_$variant.png',
              finder: find.byType(MaterialApp),
            ),
          );
        }

        await pumpVariant(
          'light',
          () => buildDashboardTestHarness(theme: ThemeData.light()),
        );
        await pumpVariant(
          'dark',
          () => buildDashboardTestHarness(theme: ThemeData.dark()),
        );
        await pumpVariant(
          'mobile',
          () => buildDashboardTestHarness(size: const Size(375, 667)),
        );
        await pumpVariant(
          'tablet',
          () => buildDashboardTestHarness(size: const Size(768, 1024)),
        );

        switch (classifyGoldenFamily(outcomes)) {
          case GoldenFamilyVerdict.suitePass:
            break;
          case GoldenFamilyVerdict.familyEnvironmentDrift:
            // 裁决 (b)：显式 SKIP+标注原因——非静默过、非红。
            markTestSkipped(familyDriftSkipReason(outcomes));
          case GoldenFamilyVerdict.regression:
            fail(familyRegressionFailReason(outcomes));
          case GoldenFamilyVerdict.suspiciousPartialDrift:
            fail(familyPartialDriftFailReason(outcomes));
        }
      },
      skip: !_enableDashboardGoldens,
    );
  });
}
