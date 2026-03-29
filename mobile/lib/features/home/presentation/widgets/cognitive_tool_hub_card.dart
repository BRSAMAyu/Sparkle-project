import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/providers/tool_preferences_provider.dart';
import 'package:sparkle/features/tools/tool_launcher.dart';
import 'package:sparkle/features/tools/tool_registry.dart';

class CognitiveToolHubCard extends ConsumerStatefulWidget {
  const CognitiveToolHubCard({
    super.key,
    this.compact = false,
    this.dense = false,
  });

  final bool compact;
  final bool dense;

  @override
  ConsumerState<CognitiveToolHubCard> createState() =>
      _CognitiveToolHubCardState();
}

class _CognitiveToolHubCardState extends ConsumerState<CognitiveToolHubCard> {
  bool _isExpanded = false;
  late final PageController _pageController;
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _pageController = PageController();
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final cognitive = dashboardState.cognitive;
    final pinnedIds = ref.watch(toolPreferencesProvider).pinnedToolIds;
    final pinnedTools = pinnedIds
        .map(ToolRegistry.tryGetById)
        .whereType<ToolDefinition>()
        .toList();
    final visibleCount = _isExpanded ? 8 : 4;
    final effectiveTools = pinnedTools.take(math.max(visibleCount, 4)).toList();
    final pagedTools = _chunkTools(
      pinnedTools,
      _isExpanded ? 8 : 4,
    );
    final weeklyPattern = cognitive.weeklyPattern;

    if (widget.compact) {
      final contentPadding = widget.dense ? DS.spacing8 : DS.spacing10;
      final topSpacing = widget.dense ? DS.spacing6 : DS.spacing8;
      final compactPages = _chunkTools(pinnedTools, 4);
      const title = '工具快捷';

      return ClipRRect(
        borderRadius: DS.borderRadius20,
        child: MaterialStyler(
          material: AppMaterials.ceramic(context).copyWith(
            backgroundGradient: LinearGradient(
              colors: [
                DS.prismPurple.withValues(alpha: 0.08),
                DS.surfaceSecondary,
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderColor: DS.prismPurple.withValues(alpha: 0.22),
            borderWidth: 1,
          ),
          borderRadius: DS.borderRadius20,
          padding: EdgeInsets.all(contentPadding),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.widgets_rounded,
                    color: DS.prismPurple,
                    size: 18,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: context.sparkleTypography.labelLarge.copyWith(
                            fontWeight: DS.fontWeightBold,
                            height: 1.0,
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    constraints: const BoxConstraints.tightFor(
                      width: 28,
                      height: 28,
                    ),
                    padding: EdgeInsets.zero,
                    visualDensity: VisualDensity.compact,
                    onPressed: () => context.push('/tools/library?tab=manage'),
                    icon: Icon(
                      Icons.tune_rounded,
                      size: 18,
                      color: DS.prismPurple,
                    ),
                    tooltip: '工具设置',
                  ),
                  if (!widget.dense && weeklyPattern != null) ...[
                    const SizedBox(width: DS.spacing8),
                    Flexible(
                      child: Text(
                        weeklyPattern,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.right,
                        style: context.sparkleTypography.labelSmall.copyWith(
                          color: DS.textSecondary,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              SizedBox(height: topSpacing),
              Expanded(
                child: pinnedTools.isEmpty
                    ? _buildEmptyToolsState(context)
                    : _buildCompactToolsPager(
                        context,
                        compactPages,
                        dense: widget.dense,
                      ),
              ),
            ],
          ),
        ),
      );
    }

    return ClipRRect(
      borderRadius: DS.borderRadius20,
      child: MaterialStyler(
        material: AppMaterials.ceramic(context).copyWith(
          backgroundGradient: LinearGradient(
            colors: [
              DS.prismPurple.withValues(alpha: 0.08),
              DS.surfaceSecondary,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderColor: DS.prismPurple.withValues(alpha: 0.22),
          borderWidth: 1,
        ),
        borderRadius: DS.borderRadius20,
        padding: const EdgeInsets.all(DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildCognitiveSummary(context, cognitive, weeklyPattern),
            const SizedBox(height: DS.spacing16),
            Container(
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.surfacePrimary.withValues(alpha: 0.78),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        '快捷工具',
                        style: context.sparkleTypography.labelLarge.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                      const Spacer(),
                      TextButton(
                        onPressed: () =>
                            context.push('/tools/library?tab=manage'),
                        child: const Text('管理工具'),
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing8),
                  if (pinnedTools.isEmpty)
                    _buildEmptyToolsState(context)
                  else if (_isExpanded)
                    _buildExpandedTools(context, pagedTools)
                  else
                    _buildCollapsedTools(context, effectiveTools),
                  const SizedBox(height: DS.spacing12),
                  Row(
                    children: [
                      Text(
                        _isExpanded
                            ? '已展开 ${math.min(pinnedTools.length, 8)} 个工具${pinnedTools.length > 8 ? '，可左右滑动查看更多' : ''}'
                            : '首屏展示前 4 个固定工具',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: DS.textSecondary,
                            ),
                      ),
                      const Spacer(),
                      SparkleButton.ghost(
                        label: _isExpanded ? '收起' : '展开',
                        onPressed: () {
                          setState(() {
                            _isExpanded = !_isExpanded;
                            _currentPage = 0;
                            _pageController.jumpToPage(0);
                          });
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCognitiveSummary(
    BuildContext context,
    CognitiveData cognitive,
    String? weeklyPattern,
  ) =>
      InkWell(
        onTap: () => context.push('/cognitive/patterns'),
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.diamond_outlined,
                    color: DS.prismPurple,
                    size: 18,
                  ),
                  const SizedBox(width: DS.spacing8),
                  Text(
                    '认知棱镜',
                    style: context.sparkleTypography.labelSmall.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  const Spacer(),
                  if (cognitive.hasNewInsight)
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: DS.prismPurple,
                        shape: BoxShape.circle,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                weeklyPattern ?? '认知核心摘要已就位',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                weeklyPattern != null
                    ? '行为定式分析已更新，下方保留你常用的独立工具入口。'
                    : '点击同步闪念与错题数据，快速查看最近的模式变化。',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.45,
                    ),
              ),
              const SizedBox(height: DS.spacing10),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  if (weeklyPattern != null)
                    _buildTag(context, '#$weeklyPattern'),
                  _buildTag(context, '#认知核心'),
                  InkWell(
                    onTap: () => context.push('/review?mode=today'),
                    borderRadius: BorderRadius.circular(999),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: DS.spacing4,
                      ),
                      decoration: BoxDecoration(
                        color: DS.prismPurple.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                          color: DS.prismPurple.withValues(alpha: 0.25),
                        ),
                      ),
                      child: Text(
                        '复习弱项: 分析',
                        style: context.sparkleTypography.labelSmall.copyWith(
                          fontWeight: DS.fontWeightSemiBold,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      );

  Widget _buildCollapsedTools(
    BuildContext context,
    List<ToolDefinition> tools,
  ) =>
      GridView.builder(
        itemCount: tools.length,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          mainAxisSpacing: DS.spacing10,
          crossAxisSpacing: DS.spacing10,
          childAspectRatio: 1.65,
        ),
        itemBuilder: (context, index) => _ToolShortcutChip(tool: tools[index]),
      );

  Widget _buildExpandedTools(
    BuildContext context,
    List<List<ToolDefinition>> pages,
  ) {
    if (pages.isEmpty) {
      return _buildEmptyToolsState(context);
    }

    return Column(
      children: [
        SizedBox(
          height: 236,
          child: PageView.builder(
            controller: _pageController,
            itemCount: pages.length,
            onPageChanged: (page) {
              setState(() {
                _currentPage = page;
              });
            },
            itemBuilder: (context, index) => GridView.builder(
              itemCount: pages[index].length,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisSpacing: DS.spacing10,
                crossAxisSpacing: DS.spacing10,
                childAspectRatio: 1.6,
              ),
              itemBuilder: (context, itemIndex) =>
                  _ToolShortcutChip(tool: pages[index][itemIndex]),
            ),
          ),
        ),
        if (pages.length > 1) ...[
          const SizedBox(height: DS.spacing8),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(
              pages.length,
              (index) => AnimatedContainer(
                duration: DS.durationFast,
                width: _currentPage == index ? 18 : 6,
                height: 6,
                margin: const EdgeInsets.symmetric(horizontal: 3),
                decoration: BoxDecoration(
                  color: _currentPage == index
                      ? DS.prismPurple
                      : DS.prismPurple.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildCompactToolsPager(
    BuildContext context,
    List<List<ToolDefinition>> pages, {
    required bool dense,
  }) {
    if (pages.isEmpty) {
      return _buildEmptyToolsState(context);
    }

    final gridSpacing = dense ? DS.spacing6 : DS.spacing8;

    return Column(
      children: [
        Expanded(
          child: PageView.builder(
            controller: _pageController,
            itemCount: pages.length,
            onPageChanged: (page) {
              setState(() {
                _currentPage = page;
              });
            },
            itemBuilder: (context, pageIndex) {
              final pageTools = pages[pageIndex];
              return GridView.builder(
                itemCount: 4,
                physics: const NeverScrollableScrollPhysics(),
                padding: EdgeInsets.zero,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  mainAxisSpacing: gridSpacing,
                  crossAxisSpacing: gridSpacing,
                  mainAxisExtent: dense ? 50 : 58,
                ),
                itemBuilder: (context, index) {
                  if (index >= pageTools.length) {
                    return const SizedBox.shrink();
                  }
                  return _CompactToolTile(
                    tool: pageTools[index],
                    dense: dense,
                  );
                },
              );
            },
          ),
        ),
        if (pages.length > 1) ...[
          const SizedBox(height: DS.spacing8),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(
              pages.length,
              (index) => AnimatedContainer(
                duration: DS.durationFast,
                width: _currentPage == index ? 18 : 6,
                height: 6,
                margin: const EdgeInsets.symmetric(horizontal: 3),
                decoration: BoxDecoration(
                  color: _currentPage == index
                      ? DS.prismPurple
                      : DS.prismPurple.withValues(alpha: 0.22),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildEmptyToolsState(BuildContext context) => InkWell(
        onTap: () => context.push('/tools/library?tab=manage'),
        borderRadius: BorderRadius.circular(16),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.all(DS.spacing16),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Column(
            children: [
              Icon(Icons.extension_outlined, color: DS.textSecondary),
              const SizedBox(height: DS.spacing8),
              Text(
                '还没有固定工具',
                style: context.sparkleTypography.labelLarge.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                '去工具库选择你想放到首页的能力入口。',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ],
          ),
        ),
      );

  Widget _buildTag(BuildContext context, String text) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.prismPurple.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          text,
          style: context.sparkleTypography.labelSmall.copyWith(
            fontWeight: DS.fontWeightSemiBold,
          ),
        ),
      );

  List<List<ToolDefinition>> _chunkTools(List<ToolDefinition> tools, int size) {
    if (tools.isEmpty) {
      return const [];
    }

    final pages = <List<ToolDefinition>>[];
    for (var index = 0; index < tools.length; index += size) {
      pages.add(
        tools.sublist(
          index,
          math.min(index + size, tools.length),
        ),
      );
    }
    return pages;
  }
}

class _ToolShortcutChip extends ConsumerWidget {
  const _ToolShortcutChip({required this.tool});

  final ToolDefinition tool;

  @override
  Widget build(BuildContext context, WidgetRef ref) => InkWell(
        onTap: () => launchTool(
          context,
          ref,
          tool.id,
          launchContext: ToolLaunchContext.home,
        ),
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing10,
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.spacing8),
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    tool.icon,
                    size: 16,
                    color: DS.brandPrimaryConst,
                  ),
                ),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: Text(
                    tool.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _CompactToolTile extends ConsumerWidget {
  const _CompactToolTile({
    required this.tool,
    this.dense = false,
  });

  final ToolDefinition tool;
  final bool dense;

  @override
  Widget build(BuildContext context, WidgetRef ref) => InkWell(
        onTap: () => launchTool(
          context,
          ref,
          tool.id,
          launchContext: ToolLaunchContext.home,
        ),
        borderRadius: BorderRadius.circular(18),
        child: Ink(
          decoration: BoxDecoration(
            color: DS.surfacePrimary.withValues(alpha: 0.76),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: DS.borderSubtle),
            boxShadow: [
              BoxShadow(
                color: DS.prismPurple.withValues(alpha: 0.06),
                blurRadius: 12,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Padding(
            padding: EdgeInsets.symmetric(
              horizontal: dense ? DS.spacing6 : DS.spacing8,
              vertical: dense ? DS.spacing4 : DS.spacing6,
            ),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final iconOnly = constraints.maxWidth < 88;
                final iconBoxSize = dense ? 24.0 : 30.0;
                final iconSize = dense ? 13.0 : 15.0;

                if (iconOnly) {
                  return Center(
                    child: Container(
                      width: iconBoxSize,
                      height: iconBoxSize,
                      decoration: BoxDecoration(
                        color: DS.brandPrimary.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        tool.icon,
                        size: iconSize,
                        color: DS.brandPrimaryConst,
                      ),
                    ),
                  );
                }

                return Row(
                  children: [
                    Container(
                      width: iconBoxSize,
                      height: iconBoxSize,
                      decoration: BoxDecoration(
                        color: DS.brandPrimary.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        tool.icon,
                        size: iconSize,
                        color: DS.brandPrimaryConst,
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: Text(
                        tool.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: context.sparkleTypography.labelSmall.copyWith(
                          color: DS.textPrimary,
                          fontSize: dense ? 10 : 10.5,
                          height: 1.15,
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ),
      );
}
