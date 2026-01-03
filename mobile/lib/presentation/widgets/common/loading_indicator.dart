import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/design_system.dart';

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
  }) => LoadingIndicator(
      key: key,
      size: size,
      color: color,
      showText: showText,
      loadingText: loadingText,
    );

  /// 骨架屏加载指示器工厂构造函数
  factory LoadingIndicator.skeleton({
    required SkeletonVariant variant, Key? key,
    int count = 3,
  }) => LoadingIndicator(
      key: key,
      type: LoadingType.skeleton,
      skeletonVariant: variant,
      skeletonCount: count,
    );

  /// 线性加载指示器工厂构造函数
  factory LoadingIndicator.linear({
    Key? key,
    Color? color,
  }) => LoadingIndicator(
      key: key,
      type: LoadingType.linear,
      color: color,
    );

  /// 全屏加载指示器工厂构造函数
  factory LoadingIndicator.fullScreen({
    Key? key,
    String? loadingText,
  }) => LoadingIndicator(
      key: key,
      type: LoadingType.fullScreen,
      loadingText: loadingText,
    );
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
          color ?? DS.primaryBase,
        ),
      ),
    );

    if (showText) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          indicator,
          const SizedBox(height: DS.spacing12),
          Text(
            loadingText ?? '加载中...',
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.neutral600,
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
          const SizedBox(height: DS.spacing12),
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

  Widget _buildLinearLoading() => LinearProgressIndicator(
      valueColor: AlwaysStoppedAnimation<Color>(
        color ?? DS.primaryBase,
      ),
      backgroundColor: DS.neutral200,
    );

  Widget _buildFullScreenLoading() => ColoredBox(
      color: DS.overlay30,
      child: Center(
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
                      valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
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
                    color: DS.neutral900,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
}

// ==================== 骨架屏组件 ====================

/// Shimmer包装器
class _ShimmerWrapper extends StatelessWidget {

  const _ShimmerWrapper({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Shimmer.fromColors(
      baseColor: DS.neutral200,
      highlightColor: DS.neutral100,
      child: child,
    );
}

/// 骨架屏占位容器
class _SkeletonBox extends StatelessWidget {

  const _SkeletonBox({
    this.width,
    this.height,
    this.borderRadius,
  });
  final double? width;
  final double? height;
  final BorderRadius? borderRadius;

  @override
  Widget build(BuildContext context) => Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: DS.neutral300,
        borderRadius: borderRadius ?? DS.borderRadius8,
      ),
    );
}

/// 任务卡片骨架屏
class TaskCardSkeleton extends StatelessWidget {
  const TaskCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) => _ShimmerWrapper(
      child: Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.brandPrimaryConst,
          borderRadius: DS.borderRadius16,
          boxShadow: DS.shadowSm,
        ),
        child: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题行
            Row(
              children: [
                _SkeletonBox(
                  width: 4.0,
                  height: 40.0,
                  borderRadius: DS.borderRadius4,
                ),
                SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _SkeletonBox(
                        width: double.infinity,
                        height: 20.0,
                      ),
                      SizedBox(height: DS.spacing8),
                      _SkeletonBox(
                        width: 150.0,
                        height: 14.0,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            SizedBox(height: DS.spacing16),
            // 标签行
            Row(
              children: [
                _SkeletonBox(
                  width: 60.0,
                  height: 24.0,
                  borderRadius: DS.borderRadius12,
                ),
                SizedBox(width: DS.spacing8),
                _SkeletonBox(
                  width: 80.0,
                  height: 24.0,
                  borderRadius: DS.borderRadius12,
                ),
              ],
            ),
          ],
        ),
      ),
    );
}

/// 聊天气泡骨架屏
class ChatBubbleSkeleton extends StatelessWidget {

  const ChatBubbleSkeleton({
    super.key,
    this.isUser = false,
  });
  final bool isUser;

  @override
  Widget build(BuildContext context) => _ShimmerWrapper(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
        child: Row(
          mainAxisAlignment:
              isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!isUser) ...[
              const _SkeletonBox(
                width: 40.0,
                height: 40.0,
                borderRadius: DS.borderRadiusFull,
              ),
              const SizedBox(width: DS.spacing12),
            ],
            Flexible(
              child: Container(
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: DS.neutral200,
                  borderRadius: DS.borderRadius16,
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _SkeletonBox(
                      width: double.infinity,
                      height: 16.0,
                    ),
                    SizedBox(height: DS.spacing8),
                    _SkeletonBox(
                      width: 200.0,
                      height: 16.0,
                    ),
                    SizedBox(height: DS.spacing8),
                    _SkeletonBox(
                      width: 150.0,
                      height: 16.0,
                    ),
                  ],
                ),
              ),
            ),
            if (isUser) ...[
              const SizedBox(width: DS.spacing12),
              const _SkeletonBox(
                width: 40.0,
                height: 40.0,
                borderRadius: DS.borderRadiusFull,
              ),
            ],
          ],
        ),
      ),
    );
}

/// 个人资料卡片骨架屏
class ProfileCardSkeleton extends StatelessWidget {
  const ProfileCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) => _ShimmerWrapper(
      child: Container(
        padding: const EdgeInsets.all(DS.spacing20),
        decoration: BoxDecoration(
          color: DS.brandPrimaryConst,
          borderRadius: DS.borderRadius20,
          boxShadow: DS.shadowMd,
        ),
        child: Column(
          children: [
            // 头像
            const _SkeletonBox(
              width: 80.0,
              height: 80.0,
              borderRadius: DS.borderRadiusFull,
            ),
            const SizedBox(height: DS.spacing16),
            // 用户名
            const _SkeletonBox(
              width: 120.0,
              height: 20.0,
            ),
            const SizedBox(height: DS.spacing8),
            // 邮箱
            const _SkeletonBox(
              width: 180.0,
              height: 14.0,
            ),
            const SizedBox(height: DS.spacing24),
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

  Widget _buildStatSkeleton() => const Column(
      children: [
        _SkeletonBox(
          width: 40.0,
          height: 24.0,
        ),
        SizedBox(height: DS.spacing4),
        _SkeletonBox(
          width: 60.0,
          height: 12.0,
        ),
      ],
    );
}

/// 列表项骨架屏
class ListItemSkeleton extends StatelessWidget {
  const ListItemSkeleton({super.key});

  @override
  Widget build(BuildContext context) => const _ShimmerWrapper(
      child: Padding(
        padding: EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        child: Row(
          children: [
            _SkeletonBox(
              width: 48.0,
              height: 48.0,
              borderRadius: DS.borderRadius12,
            ),
            SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SkeletonBox(
                    width: double.infinity,
                    height: 18.0,
                  ),
                  SizedBox(height: DS.spacing8),
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
