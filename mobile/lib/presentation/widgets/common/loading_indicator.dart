import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/design_tokens.dart';

/// 加载指示器类型
enum LoadingType {
  circular, // 圆形进度指示器
  skeleton, // 骨架屏加载
  linear, // 线性进度条
  fullScreen, // 全屏加载
}

/// 骨架屏变体
enum SkeletonVariant {
  taskCard, // 任务卡片骨架屏
  chatBubble, // 聊天气泡骨架屏
  profileCard, // 个人资料卡片骨架屏
  listItem, // 列表项骨架屏
}

/// 自定义加载指示器组件
///
/// 支持多种加载样式：圆形进度、骨架屏、线性进度条、全屏加载
class LoadingIndicator extends StatelessWidget {
  /// 加载类型
  final LoadingType type;

  /// 骨架屏变体（仅在type为skeleton时有效）
  final SkeletonVariant? skeletonVariant;

  /// 自定义尺寸（适用于circular类型）
  final double? size;

  /// 自定义颜色（适用于circular和linear类型）
  final Color? color;

  /// 是否显示加载文本
  final bool showText;

  /// 加载文本
  final String? loadingText;

  /// 骨架屏数量（适用于skeleton类型）
  final int skeletonCount;

  const LoadingIndicator({
    super.key,
    this.type = LoadingType.circular,
    this.skeletonVariant,
    this.size,
    this.color,
    this.showText = false,
    this.loadingText,
    this.skeletonCount = 3,
  });

  /// 圆形加载指示器工厂构造函数
  factory LoadingIndicator.circular({
    Key? key,
    double? size,
    Color? color,
    bool showText = false,
    String? loadingText,
  }) {
    return LoadingIndicator(
      key: key,
      type: LoadingType.circular,
      size: size,
      color: color,
      showText: showText,
      loadingText: loadingText,
    );
  }

  /// 骨架屏加载指示器工厂构造函数
  factory LoadingIndicator.skeleton({
    required SkeletonVariant variant, Key? key,
    int count = 3,
  }) {
    return LoadingIndicator(
      key: key,
      type: LoadingType.skeleton,
      skeletonVariant: variant,
      skeletonCount: count,
    );
  }

  /// 线性加载指示器工厂构造函数
  factory LoadingIndicator.linear({
    Key? key,
    Color? color,
  }) {
    return LoadingIndicator(
      key: key,
      type: LoadingType.linear,
      color: color,
    );
  }

  /// 全屏加载指示器工厂构造函数
  factory LoadingIndicator.fullScreen({
    Key? key,
    String? loadingText,
  }) {
    return LoadingIndicator(
      key: key,
      type: LoadingType.fullScreen,
      loadingText: loadingText,
    );
  }

  @override
  Widget build(BuildContext context) {
    switch (type) {
      case LoadingType.circular:
        return _buildCircularLoading();
      case LoadingType.skeleton:
        return _buildSkeletonLoading();
      case LoadingType.linear:
        return _buildLinearLoading();
      case LoadingType.fullScreen:
        return _buildFullScreenLoading();
    }
  }

  Widget _buildCircularLoading() {
    final indicator = SizedBox(
      width: size ?? 40.0,
      height: size ?? 40.0,
      child: CircularProgressIndicator(
        strokeWidth: 3.0,
        valueColor: AlwaysStoppedAnimation<Color>(
          color ?? AppDesignTokens.primaryBase,
        ),
      ),
    );

    if (showText) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          indicator,
          const SizedBox(height: AppDesignTokens.spacing12),
          Text(
            loadingText ?? '加载中...',
            style: const TextStyle(
              fontSize: AppDesignTokens.fontSizeSm,
              color: AppDesignTokens.neutral600,
            ),
          ),
        ],
      );
    }

    return indicator;
  }

  Widget _buildSkeletonLoading() {
    final variant = skeletonVariant ?? SkeletonVariant.listItem;

    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: skeletonCount,
      separatorBuilder: (context, index) =>
          const SizedBox(height: AppDesignTokens.spacing12),
      itemBuilder: (context, index) {
        switch (variant) {
          case SkeletonVariant.taskCard:
            return const TaskCardSkeleton();
          case SkeletonVariant.chatBubble:
            return ChatBubbleSkeleton(isUser: index % 2 == 0);
          case SkeletonVariant.profileCard:
            return const ProfileCardSkeleton();
          case SkeletonVariant.listItem:
            return const ListItemSkeleton();
        }
      },
    );
  }

  Widget _buildLinearLoading() {
    return LinearProgressIndicator(
      valueColor: AlwaysStoppedAnimation<Color>(
        color ?? AppDesignTokens.primaryBase,
      ),
      backgroundColor: AppDesignTokens.neutral200,
    );
  }

  Widget _buildFullScreenLoading() {
    return Container(
      color: AppDesignTokens.overlay30,
      child: Center(
        child: Container(
          padding: const EdgeInsets.all(AppDesignTokens.spacing32),
          decoration: BoxDecoration(
            gradient: AppDesignTokens.cardGradientNeutral,
            borderRadius: AppDesignTokens.borderRadius20,
            boxShadow: AppDesignTokens.shadowXl,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 80.0,
                height: 80.0,
                decoration: BoxDecoration(
                  gradient: AppDesignTokens.primaryGradient,
                  borderRadius: AppDesignTokens.borderRadiusFull,
                ),
                child: const Center(
                  child: SizedBox(
                    width: 40.0,
                    height: 40.0,
                    child: CircularProgressIndicator(
                      strokeWidth: 3.0,
                      valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
                    ),
                  ),
                ),
              ),
              if (loadingText != null) ...[
                const SizedBox(height: AppDesignTokens.spacing20),
                Text(
                  loadingText!,
                  style: const TextStyle(
                    fontSize: AppDesignTokens.fontSizeBase,
                    fontWeight: AppDesignTokens.fontWeightMedium,
                    color: AppDesignTokens.neutral900,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ==================== 骨架屏组件 ====================

/// Shimmer包装器
class _ShimmerWrapper extends StatelessWidget {
  final Widget child;

  const _ShimmerWrapper({required this.child});

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppDesignTokens.neutral200,
      highlightColor: AppDesignTokens.neutral100,
      period: const Duration(milliseconds: 1500),
      child: child,
    );
  }
}

/// 骨架屏占位容器
class _SkeletonBox extends StatelessWidget {
  final double? width;
  final double? height;
  final BorderRadius? borderRadius;

  const _SkeletonBox({
    this.width,
    this.height,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: AppDesignTokens.neutral300,
        borderRadius: borderRadius ?? AppDesignTokens.borderRadius8,
      ),
    );
  }
}

/// 任务卡片骨架屏
class TaskCardSkeleton extends StatelessWidget {
  const TaskCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return _ShimmerWrapper(
      child: Container(
        padding: const EdgeInsets.all(AppDesignTokens.spacing16),
        decoration: BoxDecoration(
          color: DS.brandPrimary,
          borderRadius: AppDesignTokens.borderRadius16,
          boxShadow: AppDesignTokens.shadowSm,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题行
            Row(
              children: [
                _SkeletonBox(
                  width: 4.0,
                  height: 40.0,
                  borderRadius: AppDesignTokens.borderRadius4,
                ),
                const SizedBox(width: AppDesignTokens.spacing12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _SkeletonBox(
                        width: double.infinity,
                        height: 20.0,
                      ),
                      SizedBox(height: AppDesignTokens.spacing8),
                      _SkeletonBox(
                        width: 150.0,
                        height: 14.0,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            // 标签行
            Row(
              children: [
                _SkeletonBox(
                  width: 60.0,
                  height: 24.0,
                  borderRadius: AppDesignTokens.borderRadius12,
                ),
                const SizedBox(width: AppDesignTokens.spacing8),
                _SkeletonBox(
                  width: 80.0,
                  height: 24.0,
                  borderRadius: AppDesignTokens.borderRadius12,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// 聊天气泡骨架屏
class ChatBubbleSkeleton extends StatelessWidget {
  final bool isUser;

  const ChatBubbleSkeleton({
    super.key,
    this.isUser = false,
  });

  @override
  Widget build(BuildContext context) {
    return _ShimmerWrapper(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing16,
          vertical: AppDesignTokens.spacing8,
        ),
        child: Row(
          mainAxisAlignment:
              isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!isUser) ...[
              _SkeletonBox(
                width: 40.0,
                height: 40.0,
                borderRadius: AppDesignTokens.borderRadiusFull,
              ),
              const SizedBox(width: AppDesignTokens.spacing12),
            ],
            Flexible(
              child: Container(
                padding: const EdgeInsets.all(AppDesignTokens.spacing12),
                decoration: BoxDecoration(
                  color: AppDesignTokens.neutral200,
                  borderRadius: AppDesignTokens.borderRadius16,
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _SkeletonBox(
                      width: double.infinity,
                      height: 16.0,
                    ),
                    SizedBox(height: AppDesignTokens.spacing8),
                    _SkeletonBox(
                      width: 200.0,
                      height: 16.0,
                    ),
                    SizedBox(height: AppDesignTokens.spacing8),
                    _SkeletonBox(
                      width: 150.0,
                      height: 16.0,
                    ),
                  ],
                ),
              ),
            ),
            if (isUser) ...[
              const SizedBox(width: AppDesignTokens.spacing12),
              _SkeletonBox(
                width: 40.0,
                height: 40.0,
                borderRadius: AppDesignTokens.borderRadiusFull,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// 个人资料卡片骨架屏
class ProfileCardSkeleton extends StatelessWidget {
  const ProfileCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return _ShimmerWrapper(
      child: Container(
        padding: const EdgeInsets.all(AppDesignTokens.spacing20),
        decoration: BoxDecoration(
          color: DS.brandPrimary,
          borderRadius: AppDesignTokens.borderRadius20,
          boxShadow: AppDesignTokens.shadowMd,
        ),
        child: Column(
          children: [
            // 头像
            _SkeletonBox(
              width: 80.0,
              height: 80.0,
              borderRadius: AppDesignTokens.borderRadiusFull,
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            // 用户名
            const _SkeletonBox(
              width: 120.0,
              height: 20.0,
            ),
            const SizedBox(height: AppDesignTokens.spacing8),
            // 邮箱
            const _SkeletonBox(
              width: 180.0,
              height: 14.0,
            ),
            const SizedBox(height: AppDesignTokens.spacing24),
            // 统计数据行
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStatSkeleton(),
                _buildStatSkeleton(),
                _buildStatSkeleton(),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatSkeleton() {
    return const Column(
      children: [
        _SkeletonBox(
          width: 40.0,
          height: 24.0,
        ),
        SizedBox(height: AppDesignTokens.spacing4),
        _SkeletonBox(
          width: 60.0,
          height: 12.0,
        ),
      ],
    );
  }
}

/// 列表项骨架屏
class ListItemSkeleton extends StatelessWidget {
  const ListItemSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return _ShimmerWrapper(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppDesignTokens.spacing16,
          vertical: AppDesignTokens.spacing12,
        ),
        child: Row(
          children: [
            _SkeletonBox(
              width: 48.0,
              height: 48.0,
              borderRadius: AppDesignTokens.borderRadius12,
            ),
            const SizedBox(width: AppDesignTokens.spacing12),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SkeletonBox(
                    width: double.infinity,
                    height: 18.0,
                  ),
                  SizedBox(height: AppDesignTokens.spacing8),
                  _SkeletonBox(
                    width: 200.0,
                    height: 14.0,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
