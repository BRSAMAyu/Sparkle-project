import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/l10n/app_localizations.dart';

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
/// 支持多种加载样式：圆形进度、线性进度条、全屏加载
class LoadingIndicator extends StatelessWidget {
  const LoadingIndicator({
    super.key,
    this.type = LoadingType.circular,
    this.size,
    this.color,
    this.showText = false,
    this.loadingText,
    this.strokeWidth,
    this.value,
    this.backgroundColor,
    this.liveRegion = true,
    this.strokeCap,
    this.borderRadius,
  });

  /// 圆形加载指示器工厂构造函数
  factory LoadingIndicator.circular({
    Key? key,
    double? size,
    Color? color,
    bool showText = false,
    String? loadingText,
    double? strokeWidth,
    double? value,
    Color? backgroundColor,
    bool liveRegion = true,
    StrokeCap? strokeCap,
  }) =>
      LoadingIndicator(
        key: key,
        size: size,
        color: color,
        showText: showText,
        loadingText: loadingText,
        strokeWidth: strokeWidth,
        value: value,
        backgroundColor: backgroundColor,
        liveRegion: liveRegion,
        strokeCap: strokeCap,
      );

  /// 线性加载指示器工厂构造函数
  factory LoadingIndicator.linear({
    Key? key,
    double? size,
    Color? color,
    double? value,
    Color? backgroundColor,
    bool liveRegion = true,
    BorderRadius? borderRadius,
  }) =>
      LoadingIndicator(
        key: key,
        type: LoadingType.linear,
        size: size,
        color: color,
        value: value,
        backgroundColor: backgroundColor,
        liveRegion: liveRegion,
        borderRadius: borderRadius,
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

  /// 自定义尺寸（circular 为直径；linear 为厚度 minHeight）
  final double? size;

  /// 自定义颜色（适用于circular和linear类型）
  final Color? color;

  /// 是否显示加载文本
  final bool showText;

  /// 加载文本
  final String? loadingText;

  /// 圆形指示器线宽（U-01 Step 3 扩展：内联小尺寸场景视觉等价所需，
  /// null 时保持历史默认 3.0）
  final double? strokeWidth;

  /// 确定性进度值 0..1（U-01 Step 3 扩展：进度条/进度环迁移所需，
  /// null 时为不确定态加载，与历史行为一致）
  final double? value;

  /// 进度轨道背景色（U-01 Step 3 扩展：circular 底环/linear 轨道，
  /// null 时保持历史默认——linear 为 DS.neutral200，circular 无底环）
  final Color? backgroundColor;

  /// 是否作为 liveRegion 播报（U-01 Step 3 扩展：内联在已带语义标签的
  /// 交互控件内的指示器传 false，避免频繁重建造成播报刷屏；默认 true
  /// 与历史行为一致）
  final bool liveRegion;

  /// 圆形指示器线帽（U-01 Step 3 扩展：进度环视觉等价所需，
  /// null 时为平台默认）
  final StrokeCap? strokeCap;

  /// 线性指示器圆角（U-01 Step 3 扩展：圆角进度条视觉等价所需，
  /// null 时为直角，与历史行为一致）
  final BorderRadius? borderRadius;

  @override
  Widget build(BuildContext context) {
    // U-01 Step 3：label 求值对 l10n 缺失容错（与 error_widget.dart 同惯例），
    // 保证无本地化代理的宿主（如部分测试 harness）不因 owner 迁移而崩溃。
    final l10n = AppLocalizations.of(context);
    final resolvedLabel = loadingText ?? l10n?.commonLoading ?? 'Loading';
    switch (type) {
      case LoadingType.circular:
        return _buildCircularLoading(context, resolvedLabel);
      case LoadingType.linear:
        return _buildLinearLoading(context, resolvedLabel);
      case LoadingType.fullScreen:
        return _buildFullScreenLoading(context, resolvedLabel);
    }
  }

  Widget _buildCircularLoading(BuildContext context, String resolvedLabel) {
    final indicator = SizedBox(
      width: size ?? 40.0,
      height: size ?? 40.0,
      child: CircularProgressIndicator(
        strokeWidth: strokeWidth ?? 3.0,
        value: value,
        backgroundColor: backgroundColor,
        strokeCap: strokeCap,
        valueColor: AlwaysStoppedAnimation<Color>(
          color ?? DS.primaryBase,
        ),
      ),
    );

    if (showText) {
      return Semantics(
        container: true,
        liveRegion: liveRegion,
        label: resolvedLabel,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            indicator,
            const SizedBox(height: DS.spacing12),
            Text(
              resolvedLabel,
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
      liveRegion: liveRegion,
      label: resolvedLabel,
      child: indicator,
    );
  }

  Widget _buildLinearLoading(BuildContext context, String resolvedLabel) => Semantics(
        container: true,
        liveRegion: liveRegion,
        label: resolvedLabel,
        child: LinearProgressIndicator(
          value: value,
          minHeight: size,
          borderRadius: borderRadius,
          valueColor: AlwaysStoppedAnimation<Color>(
            color ?? DS.primaryBase,
          ),
          backgroundColor: backgroundColor ?? DS.neutral200,
        ),
      );

  Widget _buildFullScreenLoading(BuildContext context, String resolvedLabel) => ColoredBox(
        color: DS.overlay30,
        child: Center(
          child: Semantics(
            container: true,
            liveRegion: true,
            label: resolvedLabel,
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
