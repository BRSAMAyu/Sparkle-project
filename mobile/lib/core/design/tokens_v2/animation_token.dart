import 'package:flutter/material.dart';

/// 动画系统 - 物理模拟 + 语义化
@immutable
class AnimationSystem {
  const AnimationSystem._();

  // 物理模拟曲线
  static const Curve spring = Curves.elasticOut;
  static const Curve bounce = Curves.bounceOut;
  static const Curve smooth = Curves.easeInOutCubic;
  static const Curve easeOut = Curves.easeOut;
  static const Curve easeIn = Curves.easeIn;

  // 语义化时长
  static const Duration instant = Duration();
  static const Duration quick = Duration(milliseconds: 150);
  static const Duration normal = Duration(milliseconds: 250);
  static const Duration slow = Duration(milliseconds: 400);
  static const Duration deliberate = Duration(milliseconds: 600);

  // 组合配置
  static const Map<AnimationPurpose, AnimationConfig> configs = {
    AnimationPurpose.buttonTap: AnimationConfig(
      duration: Duration(milliseconds: 100),
      curve: Curves.easeOut,
      scale: 0.95,
    ),
    AnimationPurpose.pageTransition: AnimationConfig(
      duration: Duration(milliseconds: 350),
      curve: Curves.easeInOutCubic,
      offset: Offset(0.1, 0),
    ),
    AnimationPurpose.loading: AnimationConfig(
      duration: Duration(milliseconds: 1000),
      curve: Curves.linear,
      rotation: 2 * 3.14159,
    ),
    AnimationPurpose.expand: AnimationConfig(
      duration: Duration(milliseconds: 300),
      curve: Curves.easeOut,
    ),
    AnimationPurpose.feedback: AnimationConfig(
      duration: Duration(milliseconds: 50),
      curve: Curves.easeOut,
      scale: 0.98,
    ),
  };
}

enum AnimationPurpose {
  buttonTap,
  pageTransition,
  loading,
  feedback,
  expand,
  fade,
  slide,
}

@immutable
class AnimationConfig {

  const AnimationConfig({
    required this.duration,
    required this.curve,
    this.scale,
    this.offset,
    this.rotation,
    this.opacity,
  });
  final Duration duration;
  final Curve curve;
  final double? scale;
  final Offset? offset;
  final double? rotation;
  final double? opacity;

  /// 创建动画Tween序列
  List<TweenSequenceItem<double>> createTweenSequence() {
    final items = <TweenSequenceItem<double>>[];

    if (scale != null) {
      items.add(TweenSequenceItem<double>(
        tween: Tween<double>(begin: 1.0, end: scale),
        weight: 1,
      ),);
    }

    if (opacity != null) {
      items.add(TweenSequenceItem<double>(
        tween: Tween<double>(begin: 1.0, end: opacity),
        weight: 1,
      ),);
    }

    // 如果没有任何动画，返回默认的
    if (items.isEmpty) {
      items.add(TweenSequenceItem<double>(
        tween: Tween<double>(begin: 1.0, end: 1.0),
        weight: 1,
      ),);
    }

    return items;
  }

  /// 应用动画到Widget
  Widget animate({
    required Widget child,
    required AnimationController controller,
  }) => AnimatedBuilder(
      animation: controller,
      builder: (context, child) {
        var result = child!;

        if (scale != null) {
          final scaleTween = Tween<double>(begin: 1.0, end: scale);
          result = Transform.scale(
            scale: scaleTween.evaluate(controller),
            child: result,
          );
        }

        if (offset != null) {
          result = Transform.translate(
            offset: Offset.lerp(
              Offset.zero,
              offset,
              controller.value,
            )!,
            child: result,
          );
        }

        if (rotation != null) {
          result = Transform.rotate(
            angle: controller.value * rotation!,
            child: result,
          );
        }

        if (opacity != null) {
          final opacityTween = Tween<double>(begin: 1.0, end: opacity);
          result = Opacity(
            opacity: opacityTween.evaluate(controller),
            child: result,
          );
        }

        return result;
      },
      child: child,
    );
}

/// 动画令牌 - 语义化命名
@immutable
class AnimationToken {

  const AnimationToken(this.name, this.duration, this.curve);
  final String name;
  final Duration duration;
  final Curve curve;

  /// 创建动画控制器配置
  AnimationConfig toConfig({double? scale, Offset? offset, double? rotation}) => AnimationConfig(
      duration: duration,
      curve: curve,
      scale: scale,
      offset: offset,
      rotation: rotation,
    );

  /// 应用到动画
  Animation<double> apply(AnimationController controller) => controller.drive(CurveTween(curve: curve));

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AnimationToken &&
          runtimeType == other.runtimeType &&
          duration == other.duration &&
          curve == other.curve;

  @override
  int get hashCode => Object.hash(duration, curve);
}

/// 便捷动画扩展
extension AnimationExtensions on Widget {
  /// 淡入动画
  Widget fadeIn({Duration duration = AnimationSystem.normal}) => AnimatedOpacity(
      opacity: 1.0,
      duration: duration,
      child: this,
    );

  /// 上滑动画
  Widget slideUp({Duration duration = AnimationSystem.normal}) => AnimatedSlide(
      offset: const Offset(0, 0),
      from: const Offset(0, 0.2),
      duration: duration,
      child: this,
    );

  /// 缩放动画
  Widget scaleIn({Duration duration = AnimationSystem.normal}) => SparkleAnimatedScale(
      scale: 1.0,
      from: 0.8,
      duration: duration,
      child: this,
    );
}

/// 自定义AnimatedSlide扩展
class AnimatedSlide extends ImplicitlyAnimatedWidget {

  const AnimatedSlide({
    required this.child, required this.offset, super.key,
    this.from = Offset.zero,
    super.duration = AnimationSystem.normal,
    super.curve = Curves.easeOut,
  });
  final Widget child;
  final Offset offset;
  final Offset from;

  @override
  ImplicitlyAnimatedWidgetState<AnimatedSlide> createState() => _AnimatedSlideState();
}

class _AnimatedSlideState extends ImplicitlyAnimatedWidgetState<AnimatedSlide> {
  Tween<Offset>? _offsetTween;
  Animation<Offset>? _offsetAnimation;

  @override
  void forEachTween(TweenVisitor<dynamic> visitor) {
    _offsetTween = visitor(
      _offsetTween,
      widget.offset,
      (dynamic value) => Tween<Offset>(begin: value),
    ) as Tween<Offset>?;
  }

  @override
  void didUpdateTweens() {
    _offsetAnimation = animation.drive(_offsetTween!);
  }

  @override
  Widget build(BuildContext context) => SlideTransition(
      position: _offsetAnimation!,
      child: widget.child,
    );
}

/// 自定义AnimatedScale扩展 - renamed to avoid conflict with Flutter's AnimatedScale
class SparkleAnimatedScale extends ImplicitlyAnimatedWidget {

  const SparkleAnimatedScale({
    required this.child, required this.scale, super.key,
    this.from = 1.0,
    super.duration = AnimationSystem.normal,
    super.curve = Curves.easeOut,
  });
  final Widget child;
  final double scale;
  final double from;

  @override
  ImplicitlyAnimatedWidgetState<SparkleAnimatedScale> createState() => _SparkleAnimatedScaleState();
}

class _SparkleAnimatedScaleState extends ImplicitlyAnimatedWidgetState<SparkleAnimatedScale> {
  Tween<double>? _scaleTween;
  Animation<double>? _scaleAnimation;

  @override
  void forEachTween(TweenVisitor<dynamic> visitor) {
    _scaleTween = visitor(
      _scaleTween,
      widget.scale,
      (dynamic value) => Tween<double>(begin: value),
    ) as Tween<double>?;
  }

  @override
  void didUpdateTweens() {
    _scaleAnimation = animation.drive(_scaleTween!);
  }

  @override
  Widget build(BuildContext context) => ScaleTransition(
      scale: _scaleAnimation!,
      child: widget.child,
    );
}
