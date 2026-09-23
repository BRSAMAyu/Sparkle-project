import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

/// EE-G5（A-SPEC3 §4.4.2，改造 #5）：tool body 首路径加载骨架。
///
/// 替代 body 级裸 `CircularProgressIndicator`（居中转圈：无结构、无阶段感，
/// 弱网备考场景秒开不成立）。形状贴内容侧布局——ToolMetricRow 指标卡 +
/// ToolSectionCard 区块（SparkleSkeleton 家族出灰条），骨架→内容保持同构
/// 容器节奏，避免布局跳变；首帧即有结构可读。
class ToolBodySkeleton extends StatelessWidget {
  const ToolBodySkeleton({
    required this.metricCount,
    required this.sectionContentHeights,
    super.key,
  });

  /// 指标卡占位数——贴内容侧 `ToolMetricRow` 的卡数。
  final int metricCount;

  /// 各区块（`ToolSectionCard`）**内容区**高度——传内容侧同款高度
  /// （如图表 168、编辑器 clamp 值），保证骨架与内容区块等高。
  final List<double> sectionContentHeights;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ToolMetricRow(
            children: [
              for (var i = 0; i < metricCount; i++)
                const _ToolMetricCardSkeleton(),
            ],
          ),
          for (final contentHeight in sectionContentHeights) ...[
            const SizedBox(height: DS.spacing16),
            ToolSectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 标题占位条（内容侧 title 同级高度节奏）。
                  const SparkleSkeleton(width: 132, height: 18, borderRadius: 6),
                  const SizedBox(height: DS.spacing12),
                  SparkleSkeleton(
                    height: contentHeight,
                    borderRadius: 12,
                  ),
                ],
              ),
            ),
          ],
        ],
      );
}

/// 指标卡骨架——贴 [ToolMetricCard] 容器（圆角 20、内边距 h16/v12、
/// label 行 16 + 间距 8 + value 行 ~22），数据到达时盒子形状不跳变。
class _ToolMetricCardSkeleton extends StatelessWidget {
  const _ToolMetricCardSkeleton();

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: isDark ? DS.surfaceSecondary : DS.surfacePanel,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: DS.borderSubtle),
      ),
      child: const Padding(
        padding: EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            SparkleSkeleton(width: 72, borderRadius: 6),
            SizedBox(height: DS.spacing8),
            SparkleSkeleton(width: 96, height: 22),
          ],
        ),
      ),
    );
  }
}
