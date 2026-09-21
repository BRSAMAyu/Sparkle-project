import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 加载指示器类型
///
/// U-01 Step 0：骨架屏家族已收敛至 sparkle_skeleton.dart（唯一 owner，
/// 含遗留 shimmer 变体）；本组件只保留 circular/linear/fullScreen 职责。
enum LoadingType {
  circular, // 圆形进度指示器
  linear, // 线性进度条
  fullScreen, // 全屏加载
}

/// 自定义加载指示器组件
///
/// 支持多种加载样式：圆形进度、骨架屏、线性进度条、全屏加载
class LoadingIndicator extends StatelessWidget {
  const LoadingIndicator({
    super.key,
    this.type = LoadingType.circular,
    this.size,
    this.color,
    this.showText = false,
    this.loadingText,
  });

  /// 圆形加载指示器工厂构造函数
  factory LoadingIndicator.circular({
    Key? key,
    double? size,
    Color? color,
    bool showText = false,
    String? loadingText,
  }) =>
      LoadingIndicator(
        key: key,
        size: size,
        color: color,
        showText: showText,
        loadingText: loadingText,
      );

  /// 线性加载指示器工厂构造函数
  factory LoadingIndicator.linear({
    Key? key,
    Color? color,
  }) =>
      LoadingIndicator(
        key: key,
        type: LoadingType.linear,
        color: color,
      );

  /// 全屏加载指示器工厂构造函数
  factory LoadingIndicator.fullScreen({
    Key? key,
    String? loadingText,
  }) =>
      LoadingIndicator(
        key: key,
        type: LoadingType.fullScreen,
        loadingText: loadingText,
      );

  /// 加载类型
  final LoadingType type;

  /// 自定义尺寸（适用于circular类型）
  final double? size;

  /// 自定义颜色（适用于circular和linear类型）
  final Color? color;

  /// 是否显示加载文本
  final bool showText;

  /// 加载文本
  final String? loadingText;

  @override
  Widget build(BuildContext context) {
    switch (type) {
      case LoadingType.circular:
        return _buildCircularLoading(context);
      case LoadingType.linear:
        return _buildLinearLoading(context);
      case LoadingType.fullScreen:
        return _buildFullScreenLoading(context);
    }
  }

  Widget _buildCircularLoading(BuildContext context) {
    final indicator = SizedBox(
      width: size ?? 40.0,
      height: size ?? 40.0,
      child: CircularProgressIndicator(
        strokeWidth: 3.0,
        valueColor: AlwaysStoppedAnimation<Color>(
          color ?? DS.primaryBase,
        ),
      ),
    );

    if (showText) {
      return Semantics(
        container: true,
        liveRegion: true,
        label: loadingText ?? context.l10n.commonLoading,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            indicator,
            const SizedBox(height: DS.spacing12),
            Text(
              loadingText ?? context.l10n.commonLoading,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: context.colors.textSecondary,
              ),
            ),
          ],
        ),
      );
    }

    return Semantics(
      container: true,
      liveRegion: true,
      label: loadingText ?? context.l10n.commonLoading,
      child: indicator,
    );
  }

  Widget _buildLinearLoading(BuildContext context) => Semantics(
        container: true,
        liveRegion: true,
        label: loadingText ?? context.l10n.commonLoading,
        child: LinearProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(
            color ?? DS.primaryBase,
          ),
          backgroundColor: DS.neutral200,
        ),
      );

  Widget _buildFullScreenLoading(BuildContext context) => ColoredBox(
        color: DS.overlay30,
        child: Center(
          child: Semantics(
            container: true,
            liveRegion: true,
            label: loadingText ?? context.l10n.commonLoading,
            child: SparkleStaggerItem(
              index: 0,
              motionToken: SparkleMotionToken.micro,
              child: Container(
                padding: const EdgeInsets.all(DS.spacing32),
                decoration: BoxDecoration(
                  gradient: DS.cardGradientNeutral,
                  borderRadius: DS.borderRadius20,
                  boxShadow: DS.shadowXl,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 80.0,
                      height: 80.0,
                      decoration: BoxDecoration(
                        gradient: DS.primaryGradient,
                        borderRadius: DS.borderRadiusFull,
                      ),
                      child: Center(
                        child: SizedBox(
                          width: 40.0,
                          height: 40.0,
                          child: CircularProgressIndicator(
                            strokeWidth: 3.0,
                            valueColor:
                                AlwaysStoppedAnimation<Color>(DS.brandPrimary),
                          ),
                        ),
                      ),
                    ),
                    if (loadingText != null) ...[
                      const SizedBox(height: DS.spacing20),
                      Text(
                        loadingText!,
                        style: TextStyle(
                          fontSize: DS.fontSizeBase,
                          fontWeight: DS.fontWeightMedium,
                          color: context.colors.textPrimary,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}
