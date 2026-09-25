import 'package:flutter/material.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';

/// U-02 状态令牌——calm / celebrate / attention 三态装饰预算。
///
/// DESIGN_DIRECTION「装饰预算」的令牌化：装饰对比度不得高于核心信息、
/// 同屏最多一个强视觉焦点。每个状态给出一组**无量纲预算**（发光透明度、
/// 强调缩放、动效时长倍率、庆祝粒子倍率、是否允许弹性），消费点据预算
/// 渲染，不允许 feature 内自定魔法值。
///
/// 全部为数值预算，不含颜色——颜色仍由 [SparkleColors] 唯一真源负责
/// （Forbidden：不新增颜色魔法值、不重建既有真源）。
@immutable
class SparkleStateTokens {
  const SparkleStateTokens({
    required this.glowOpacity,
    required this.emphasisScale,
    required this.motionScale,
    required this.particleScale,
    required this.allowBounce,
  });

  /// 按"状态 × 刺激档位"解析预算（两档输出真实不同的减法表）。
  ///
  /// - calm：本征低装饰，两档一致（平静态不靠刺激表达）。
  /// - celebrate：standard 档允许完整的庆祝表达（发光/粒子/弹性）；
  ///   low 档粒子归零、弹性撤除、时长收缩——庆祝降为静态确认，
  ///   低刺激模式"真实减少挑战性/奖励性元素"。
  /// - attention：attention 需求保留（不能减到看不见），但 standard 档
  ///   即克制，low 档只再收紧发光与时长。
  factory SparkleStateTokens.forMood(
    SparkleStateMood mood, {
    StimulationLevel level = StimulationLevel.standard,
  }) {
    final low = level == StimulationLevel.low;
    return switch (mood) {
      SparkleStateMood.calm => const SparkleStateTokens(
          glowOpacity: 0.05,
          emphasisScale: 1.0,
          motionScale: 1.0,
          particleScale: 0,
          allowBounce: false,
        ),
      SparkleStateMood.celebrate => low
          ? const SparkleStateTokens(
              glowOpacity: 0.08,
              emphasisScale: 1.0,
              motionScale: 0.6,
              particleScale: 0,
              allowBounce: false,
            )
          : const SparkleStateTokens(
              glowOpacity: 0.16,
              emphasisScale: 1.02,
              motionScale: 1.0,
              particleScale: 1.0,
              allowBounce: true,
            ),
      SparkleStateMood.attention => low
          ? const SparkleStateTokens(
              glowOpacity: 0.06,
              emphasisScale: 1.0,
              motionScale: 0.6,
              particleScale: 0,
              allowBounce: false,
            )
          : const SparkleStateTokens(
              glowOpacity: 0.10,
              emphasisScale: 1.0,
              motionScale: 1.0,
              particleScale: 0,
              allowBounce: false,
            ),
    };
  }

  /// 装饰发光/光晕透明度上限（装饰对比度不得高于核心信息的数值表达）。
  final double glowOpacity;

  /// 强调缩放（1.0 = 不放大；庆祝 standard 档允许极轻微 1.02）。
  final double emphasisScale;

  /// 动效时长倍率（消费点将既有时长乘以此系数；low 档 0.6 收缩）。
  final double motionScale;

  /// 庆祝粒子倍率（1.0 = 全额，0 = 归零；低刺激 celebrate/attention 归零）。
  final double particleScale;

  /// 是否允许弹性/过冲类奖励性曲线。
  final bool allowBounce;
}

/// U-02 三种产品状态。
enum SparkleStateMood {
  /// 平静/日常态——阅读、等待、普通浏览。
  calm,

  /// 庆祝态——里程碑达成、任务完成等真实 outcome 时刻。
  celebrate,

  /// 引起注意态——截止提醒、错误、需要用户介入。
  attention,
}
