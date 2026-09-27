import 'package:flutter_test/flutter_test.dart';

import 'golden_family_drift_guard.dart';

/// V3-FIX-368（wt676 登记，wt692 收口）环境守卫纯逻辑验收。
///
/// 背景：dashboard golden 基线由异构渲染环境签发，本机整族渲染漂移
/// 4 变体 × 0.18%（7632px）FAIL，与 pristine main 逐位同签名（wt676
/// A/B 双跑实证）——本机红不能证伪改动、强刷基线即毁真源。
/// 裁决 (b)：套件自检测整族带内漂移 → 显式 SKIP+标注原因；带外或
/// 非整族签名 → 硬 FAIL（真实回归不放过）。
///
/// 单位口径（本测试钉死）：flutter_test `ComparisonResult.diffPercent`
/// 是 **分数**（pixelDiffCount / totalPixels ∈ [0,1]），0.18% = 0.0018。
/// 带值 0.005 = B-04 容差先例的**文档意图**（0.5%），非其代码实现值
/// （B-04 比较器以 0.5 与分数比较 = 50% 实际容差，已登记 V3-FIX-383，
/// 归 wt667 在航面处置）。
void main() {
  group('单变体判定 verdictFor', () {
    test('0（逐位一致）→ exactMatch', () {
      expect(verdictFor(0.0), GoldenVariantVerdict.exactMatch);
    });

    test('本机实测漂移签名 0.0018（0.18%）→ envBandDrift', () {
      expect(verdictFor(0.0018), GoldenVariantVerdict.envBandDrift);
    });

    test('带界 0.005（0.5%）含边界 → envBandDrift', () {
      expect(verdictFor(kGoldenEnvDriftBand), GoldenVariantVerdict.envBandDrift);
    });

    test('超带 0.006 → overBandDrift', () {
      expect(verdictFor(0.006), GoldenVariantVerdict.overBandDrift);
    });

    test('golden 缺失语义（diffPercent=1.0）→ overBandDrift', () {
      expect(verdictFor(1.0), GoldenVariantVerdict.overBandDrift);
    });
  });

  group('整族裁决 classifyGoldenFamily', () {
    const exact = GoldenVariantOutcome('v', 0.0);
    const drift = GoldenVariantOutcome('v', 0.0018);

    test('四变体全精确 → suitePass', () {
      expect(
        classifyGoldenFamily([exact, exact, exact, exact]),
        GoldenFamilyVerdict.suitePass,
      );
    });

    test('四变体全带内漂移（本机实测签名）→ familyEnvironmentDrift', () {
      expect(
        classifyGoldenFamily([drift, drift, drift, drift]),
        GoldenFamilyVerdict.familyEnvironmentDrift,
      );
    });

    test('任一变体超带 → regression（真实回归不放进噪声带）', () {
      expect(
        classifyGoldenFamily([
          drift,
          drift,
          const GoldenVariantOutcome('v', 0.02),
          drift,
        ]),
        GoldenFamilyVerdict.regression,
      );
      expect(
        classifyGoldenFamily([exact, exact, const GoldenVariantOutcome('v', 1.0), exact]),
        GoldenFamilyVerdict.regression,
      );
    });

    test('混合精确/带内漂移 → suspiciousPartialDrift（环境漂移应整族等幅）', () {
      expect(
        classifyGoldenFamily([drift, exact, drift, drift]),
        GoldenFamilyVerdict.suspiciousPartialDrift,
      );
      expect(
        classifyGoldenFamily([exact, exact, drift, exact]),
        GoldenFamilyVerdict.suspiciousPartialDrift,
      );
    });

    test('单变体套件带内漂移不构成整族签名 → suspiciousPartialDrift', () {
      // 整族判定要求 ≥2 变体共同漂移；单变体带内漂移无法与环境漂移区分。
      expect(
        classifyGoldenFamily([drift]),
        GoldenFamilyVerdict.suspiciousPartialDrift,
      );
    });

    test('空集 → suitePass（无变体无主张）', () {
      expect(classifyGoldenFamily(const []), GoldenFamilyVerdict.suitePass);
    });
  });

  group('SKIP 原因标注 familyDriftSkipReason', () {
    test('含逐变体百分比、噪声带宽与签发机纪律', () {
      final reason = familyDriftSkipReason([
        const GoldenVariantOutcome('light', 0.0018),
        const GoldenVariantOutcome('dark', 0.0018),
        const GoldenVariantOutcome('mobile', 0.0018),
        const GoldenVariantOutcome('tablet', 0.0018),
      ]);
      expect(reason, contains('V3-FIX-368'));
      expect(reason, contains('light'));
      expect(reason, contains('dark'));
      expect(reason, contains('mobile'));
      expect(reason, contains('tablet'));
      expect(reason, contains('0.18%'));
      expect(reason, contains('0.5%'));
      expect(reason, contains('update-goldens'));
    });
  });

  group('FAIL 原因标注', () {
    test('regression 原因含超带变体与处置指引', () {
      final reason = familyRegressionFailReason([
        const GoldenVariantOutcome('light', 0.0018),
        const GoldenVariantOutcome('dark', 0.05),
      ]);
      expect(reason, contains('dark'));
      expect(reason, contains('5.00%'));
      expect(reason, contains('update-goldens'));
    });

    test('partial drift 原因含精确/漂移两组成员', () {
      final reason = familyPartialDriftFailReason([
        const GoldenVariantOutcome('light', 0.0018),
        const GoldenVariantOutcome('dark', 0.0),
      ]);
      expect(reason, contains('light'));
      expect(reason, contains('dark'));
    });
  });
}
