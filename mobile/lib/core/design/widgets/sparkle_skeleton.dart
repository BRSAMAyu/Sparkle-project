import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';

class SparkleSkeleton extends StatefulWidget {
  const SparkleSkeleton({
    super.key,
    this.width,
    this.height = 16,
    this.borderRadius = 8,
  });

  final double? width;
  final double height;
  final double borderRadius;

  @override
  State<SparkleSkeleton> createState() => _SparkleSkeletonState();
}

class _SparkleSkeletonState extends State<SparkleSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    unawaited(_controller.repeat());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = context.reduceMotion;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final baseColor = isDark ? DS.surfaceSecondary : DS.surfaceTertiary;
    final highlightColor = isDark ? DS.surfaceTertiary : DS.surfaceSecondary;

    final child = Container(
      width: widget.width,
      height: widget.height,
      decoration: BoxDecoration(
        color: baseColor,
        borderRadius: BorderRadius.circular(widget.borderRadius),
      ),
    );

    // U-08 a11y：骨架是非信息性占位（"这里是骨架条"对读屏是噪音节点，
    // 且会把真实内容的焦点序推后）。加载中的可感知语义由等待族 owner
    // （StagedSurfaceLoader / LoadingIndicator 的 liveRegion「加载中」播报）
    // 承担，骨架本身整体退出语义树——视觉渲染两分支逐字不变。
    if (reduceMotion) {
      return ExcludeSemantics(child: child);
    }

    return ExcludeSemantics(
      child: RepaintBoundary(
        child: AnimatedBuilder(
          animation: _controller,
          child: child,
          builder: (context, skeletonChild) {
            final t = _controller.value;
            final breathingScale =
                0.995 + (math.sin(t * math.pi * 2) + 1) * 0.0025;
            return Transform.scale(
              scale: breathingScale,
              child: ShaderMask(
                shaderCallback: (bounds) => LinearGradient(
                  begin: Alignment(-1.5 + t * 2.5, -0.5),
                  end: Alignment(-0.5 + t * 2.5, 0.5),
                  colors: [
                    baseColor,
                    highlightColor,
                    baseColor,
                  ],
                  stops: const [0.1, 0.5, 0.9],
                ).createShader(bounds),
                blendMode: BlendMode.srcATop,
                child: skeletonChild,
              ),
            );
          },
        ),
      ),
    );
  }
}

class SparkleCardSkeleton extends StatelessWidget {
  const SparkleCardSkeleton({
    super.key,
    this.padding = const EdgeInsets.all(DS.spacing16),
  });

  final EdgeInsetsGeometry padding;

  /// 固有内容高：22 + 12 + 14 + 8 + 14 + 16 + 10。
  static const double _fullContentHeight = 96;

  @override
  Widget build(BuildContext context) {
    final insets = padding.resolve(Directionality.of(context));
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? DS.surfacePrimary
            : DS.surfacePanel,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.borderSubtle),
      ),
      // 批次4 棘轮修复（router_smoke 存量失败根因）：调用方把骨架放进紧凑
      // 定高槽位（sync_center 72px、dashboard 40/48px）时，完整三行骨架
      // 放不下，会在晚到帧触发 58px 瞬态溢出。槽位不足时退化为单行骨架，
      // 骨架是非信息性占位，行数不影响语义。
      child: LayoutBuilder(
        builder: (context, constraints) {
          final maxInner =
              constraints.maxHeight - insets.vertical - 2; // 上下边框各 1
          if (!maxInner.isFinite || maxInner >= _fullContentHeight) {
            return const Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SparkleSkeleton(width: 148, height: 22, borderRadius: 10),
                SizedBox(height: DS.spacing12),
                SparkleSkeleton(height: 14),
                SizedBox(height: DS.spacing8),
                SparkleSkeleton(width: 220, height: 14),
                SizedBox(height: DS.spacing16),
                SparkleSkeleton(height: 10, borderRadius: 999),
              ],
            );
          }
          final barHeight = maxInner.clamp(4.0, 14.0);
          return Center(
            child: SizedBox(
              width: double.infinity,
              child: SparkleSkeleton(height: barHeight),
            ),
          );
        },
      ),
    );
  }
}

class SparkleListSkeleton extends StatelessWidget {
  const SparkleListSkeleton({
    super.key,
    this.count = 3,
    this.padding = const EdgeInsets.fromLTRB(
      DS.spacing16,
      DS.spacing12,
      DS.spacing16,
      DS.spacing32,
    ),
  });

  final int count;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => ListView.separated(
        physics: const NeverScrollableScrollPhysics(),
        shrinkWrap: true,
        padding: padding,
        itemCount: count,
        separatorBuilder: (_, __) => const SizedBox(height: DS.spacing12),
        itemBuilder: (context, index) => SparkleStaggerItem(
          index: index,
          motionToken: SparkleMotionToken.micro,
          child: const SparkleCardSkeleton(),
        ),
      );
}

class SparkleChatBubbleSkeleton extends StatelessWidget {
  const SparkleChatBubbleSkeleton({
    super.key,
    this.isUser = false,
  });

  final bool isUser;

  @override
  Widget build(BuildContext context) => Padding(
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
              const SparkleSkeleton(
                width: 36,
                height: 36,
                borderRadius: 999,
              ),
              const SizedBox(width: DS.spacing12),
            ],
            Flexible(
              child: Container(
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: Theme.of(context).brightness == Brightness.dark
                      ? DS.surfaceSecondary
                      : DS.surfacePanel,
                  borderRadius: DS.borderRadius16,
                  border: Border.all(color: DS.borderSubtle),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SparkleSkeleton(height: 14),
                    SizedBox(height: DS.spacing8),
                    SparkleSkeleton(width: 180, height: 14),
                    SizedBox(height: DS.spacing8),
                    SparkleSkeleton(width: 132, height: 14),
                  ],
                ),
              ),
            ),
            if (isUser) ...[
              const SizedBox(width: DS.spacing12),
              const SparkleSkeleton(
                width: 36,
                height: 36,
                borderRadius: 999,
              ),
            ],
          ],
        ),
      );
}

// ==================== 遗留 shimmer 骨架家族（U-01 Step 0 并入单一 owner） ====================
//
// U-01 Step 0：design 内双 skeleton 家族收敛——以下 4 个 shimmer 变体原在
// loading_indicator.dart，现并入本文件（骨架渲染唯一 owner）。渲染代码逐字
// 保留（shimmer 包、neutral 底色、尺寸均未动），保证视觉输出零变化。
// 后续 Step 1-6 按 surface 迁移到 SparkleSkeleton/SparkleCardSkeleton 后删除。

/// Shimmer包装器
class _ShimmerWrapper extends StatelessWidget {
  const _ShimmerWrapper({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (context.reduceMotion) {
      return child;
    }
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Shimmer.fromColors(
      baseColor: isDark ? DS.neutral700 : DS.neutral100,
      highlightColor: isDark ? DS.neutral600 : DS.neutral0,
      period: const Duration(milliseconds: 1200),
      child: child,
    );
  }
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
  Widget build(BuildContext context) => ExcludeSemantics(
        // U-08 a11y：与 SparkleSkeleton 同口径——遗留 shimmer 骨架同为
        // 非信息性占位，退出语义树。
        child: Container(
          width: width,
          height: height,
          decoration: BoxDecoration(
            color: Theme.of(context).brightness == Brightness.dark
                ? DS.neutral700
                : DS.neutral300,
            borderRadius: borderRadius ?? DS.borderRadius8,
          ),
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
