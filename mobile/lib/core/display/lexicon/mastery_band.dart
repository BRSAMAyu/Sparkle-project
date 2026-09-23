library;
import 'dart:ui' show Color;

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// 掌握度连续量分档唯一 owner（A-SPEC2 v1.2 N12：0.8/0.5 阈值单源 + error 槽退出）。
///
/// 存量双写靶（已由本文件收编，两文件改引用）：
/// - error_card.dart `_getMasteryColor`（0.8/0.5 双写 + error 槽挪用）
/// - error_detail_screen.dart 掌握度徽章 / 统计卡内联三元（同阈值异实现 ×3）
///
/// 档位语义（N12）：
/// - 高（≥0.8）= success（「已掌握」）
/// - 中（0.5–0.8）= warning（「该行动」）
/// - 低（<0.5）= warning（原 error 槽迁移而来——「尚未掌握」不是「失败/错误」，
///   error 槽只留给失败/错误/逾期原义）
///
/// 低/中档必须配 [masteryBandLabel] 档位人话（「还在学」级），
/// 百分数降为次级显示（EB-G5 裁决）。

/// 掌握度分档。
enum MasteryBand { high, mid, low }

/// 0.8/0.5 阈值的唯一事实源；调阈值只改这里。
MasteryBand masteryBandOf(double mastery) {
  if (mastery >= 0.8) {
    return MasteryBand.high;
  }
  if (mastery >= 0.5) {
    return MasteryBand.mid;
  }
  return MasteryBand.low;
}

/// 掌握度分档色（语义槽投影，全 app 唯一入口）。
///
/// 同输入必同色：所有掌握度取色点都经本函数；返回值永不落在 error 槽
/// （N12 负向约束，mastery_band_test 有负向断言钉住）。
Color masteryBandColor(double mastery) => switch (masteryBandOf(mastery)) {
      MasteryBand.high => DS.semanticSuccess,
      MasteryBand.mid || MasteryBand.low => DS.semanticWarning,
    };

/// 档位人话（「还在学」级；arb `errorBook*` 前缀，zh/en 双语）。
String masteryBandLabel(double mastery, AppLocalizations l10n) =>
    switch (masteryBandOf(mastery)) {
      MasteryBand.high => l10n.errorBookMasteryBandHigh,
      MasteryBand.mid => l10n.errorBookMasteryBandMid,
      MasteryBand.low => l10n.errorBookMasteryBandLow,
    };
