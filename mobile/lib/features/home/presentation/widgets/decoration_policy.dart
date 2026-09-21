import 'package:flutter/material.dart';
import 'package:sparkle/core/design/theme/performance_tier.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/services/performance_service.dart';

/// Home 装饰降档唯一决策点（U-01 Step 2）。
///
/// 此前 home 的 PerformanceTier 门控只盖 `layers/background_layer.dart` 一层，
/// WeatherHeader（全屏天气/星域/粒子）、OmniBar 呼吸辉光、冲刺卡浮动、
/// 专注卡火焰等主装饰挂载点全部无条件 `repeat()` 跑满 60fps——低性能设备
/// 卡顿的首要嫌疑。本决策点把 CONVENTION 规则 4（动效必须过 PerformanceTier
/// 与 reduce-motion 门控）扩展到全部 home 装饰挂载点，档位口径对齐既有
/// `background_layer` 门控（ultra/high 全量）与 `PerformanceService` 语义：
///
/// - [DecorationMode.animated]：完整动效（ultra/high，且系统未要求降动效）；
/// - [DecorationMode.staticFrame]：单帧静态化（medium，或 reduce-motion）——
///   保留天气/星域的视觉锤色彩氛围，动画控制器停表，绘制仅一帧；
/// - [DecorationMode.off]：不挂载非必要装饰（low）——仅保留静态底色。
enum DecorationMode { off, staticFrame, animated }

/// 按 tier 与 reduce-motion 解析当前应使用的装饰档位。
DecorationMode resolveDecorationMode(BuildContext context) {
  final tier = PerformanceService.instance.currentTier.value;
  switch (tier) {
    case PerformanceTier.low:
      return DecorationMode.off;
    case PerformanceTier.medium:
      return DecorationMode.staticFrame;
    case PerformanceTier.high:
    case PerformanceTier.ultra:
      return context.reduceMotion
          ? DecorationMode.staticFrame
          : DecorationMode.animated;
  }
}

/// 装饰密度降档：按档位缩放粒子/星体数量（视觉锤保留，数量收敛）。
///
/// animated 档按 `isUltra` 再分两档（ultra 全量 / high 收敛约 30%），
/// staticFrame 用减半的静态帧数量，off 恒 0（调用方应直接跳过挂载）。
int scaleDecorationCount(
  DecorationMode mode, {
  required bool isUltra,
  required int animatedCount,
  int staticCount = 0,
}) {
  switch (mode) {
    case DecorationMode.off:
      return 0;
    case DecorationMode.staticFrame:
      return staticCount;
    case DecorationMode.animated:
      return isUltra ? animatedCount : (animatedCount * 0.7).round();
  }
}
