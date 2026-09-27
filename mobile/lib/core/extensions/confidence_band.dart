/// 置信度定性档位映射（V3-FIX-361）。
///
/// PRODUCT_LANGUAGE 禁止 raw "0.73 confidence" / 「置信度 0.73」直达用户；
/// 展示面改为「定性档位词 + 百分比细节」形态（如「我比较确定（73%）」），
/// 档位词经 arb `select` 占位符本地化。
///
/// 档位阈值与 backend `ux_envelope._confidence_band` 对齐：
/// high >= 0.8，medium >= 0.55，其余 low。
/// 输入归一化约定与 source explanation pill 一致：<=1 视为 0-1 小数，
/// >1 视为已是百分数。
library;

/// 返回 arb select 占位符使用的 band token（'high' | 'medium' | 'low'）。
String confidenceBandToken(double confidence) {
  final frac = confidence <= 1 ? confidence : confidence / 100;
  final v = frac.clamp(0.0, 1.0);
  if (v >= 0.80) {
    return 'high';
  }
  if (v >= 0.55) {
    return 'medium';
  }
  return 'low';
}

/// 置信度百分比（0-100 整数），与 [confidenceBandToken] 同一归一化约定。
int confidencePercent(double confidence) {
  final frac = confidence <= 1 ? confidence : confidence / 100;
  return (frac.clamp(0.0, 1.0) * 100).round();
}
