import 'package:flutter/material.dart';

/// Sparkle 动效设计系统
/// 
/// 包含统一的动画时长、曲线和常用动画构建器
class SparkleMotion {
  SparkleMotion._();

  // ---------------------------------------------------------------------------
  // 1. 标准时长 (Durations)
  // ---------------------------------------------------------------------------
  
  /// 无动画 (0ms)
  static const Duration instant = Duration.zero;

  /// 快速交互反馈 (150ms) - 按钮点击、开关、复选框
  static const Duration fast = Duration(milliseconds: 150);

  /// 标准过渡 (250ms) - 列表项入场、小组件展开
  static const Duration normal = Duration(milliseconds: 250);

  /// 复杂动画 (350ms) - 页面转场、模态框弹出
  static const Duration slow = Duration(milliseconds: 350);

  /// 入场/退场动画 (500ms) - 启动画面、大面积内容变化
  static const Duration slower = Duration(milliseconds: 500);

  // ---------------------------------------------------------------------------
  // 2. 标准曲线 (Curves)
  // ---------------------------------------------------------------------------

  /// 标准曲线 (EaseInOut) - 最通用的曲线，用于大多数UI变化
  static const Curve standard = Curves.easeInOut;

  /// 入场曲线 (EaseOut) - 元素进入屏幕，快速开始慢速结束
  static const Curve enter = Curves.easeOut;

  /// 退场曲线 (EaseIn) - 元素离开屏幕，慢速开始快速结束
  static const Curve exit = Curves.easeIn;

  /// 弹性效果 (ElasticOut) - 用于强调性动画
  static const Curve bounce = Curves.elasticOut;

  /// 过冲效果 (EaseOutBack) - 稍微超出目标值再回弹，用于卡片入场等
  static const Curve overshoot = Curves.easeOutBack;

  // ---------------------------------------------------------------------------
  // 3. 常用动画构建器 (Builders)
  // ---------------------------------------------------------------------------

  /// 按压缩放动画构建器
  /// scale: 1.0 -> 0.98
  static Widget pressScale({
    required Widget child,
    required Animation<double> animation,
  }) => ScaleTransition(
      scale: Tween<double>(begin: 1.0, end: 0.98).animate(animation),
      child: child,
    );

  /// 淡入动画构建器
  /// opacity: 0.0 -> 1.0
  static Widget fadeIn({
    required Widget child,
    required Animation<double> animation,
  }) => FadeTransition(
      opacity: animation,
      child: child,
    );

  /// 上滑入场动画构建器
  /// translate Y: 20 -> 0
  /// opacity: 0 -> 1
  static Widget slideUp({
    required Widget child,
    required Animation<double> animation,
    double offset = 20.0,
  }) => FadeTransition(
      opacity: animation,
      child: SlideTransition(
        position: Tween<Offset>(
          begin: Offset(0, offset / 100), // Approximate relative offset
          end: Offset.zero,
        ).animate(animation),
        child: child,
      ),
    );

  /// 呼吸动画控制器配置 (Helper)
  /// return AnimationController configured for breathing
  static AnimationController createBreathingController(TickerProvider vsync) => AnimationController(
      vsync: vsync,
      duration: const Duration(seconds: 4), // 4秒一个周期
    )..repeat(reverse: true);
}
