import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/models/tool_preferences.dart';
import 'package:sparkle/features/tools/providers/tool_preferences_provider.dart';
import 'package:sparkle/features/tools/tool_launcher.dart';
import 'package:sparkle/features/tools/tool_registry.dart';

class ToolLibraryScreen extends ConsumerStatefulWidget {
  const ToolLibraryScreen({
    super.key,
    this.initialTab = 0,
  });

  final int initialTab;

  @override
  ConsumerState<ToolLibraryScreen> createState() => _ToolLibraryScreenState();
}

class _ToolLibraryScreenState extends ConsumerState<ToolLibraryScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _tabController.index = widget.initialTab.clamp(0, 1);
    _searchController.addListener(() {
      setState(() {});
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final prefs = ref.watch(toolPreferencesProvider);
    final allTools = ToolRegistry.pinnableTools;
    final recentTools = prefs.recentToolIds
        .map(ToolRegistry.tryGetById)
        .whereType<ToolDefinition>()
        .toList();

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: const Text('工具库'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: '浏览'),
            Tab(text: '管理'),
          ],
        ),
      ),
      child: SafeArea(
        child: TabBarView(
          controller: _tabController,
          children: [
            _buildBrowseTab(context, prefs, allTools, recentTools),
            _buildManageTab(context, prefs),
          ],
        ),
      ),
    );
  }

  Widget _buildBrowseTab(
    BuildContext context,
    ToolPreferences prefs,
    List<ToolDefinition> allTools,
    List<ToolDefinition> recentTools,
  ) {
    final query = _searchController.text.trim().toLowerCase();
    final filtered = allTools.where((tool) {
      if (query.isEmpty) {
        return true;
      }
      return tool.title.toLowerCase().contains(query) ||
          (tool.description ?? '').toLowerCase().contains(query) ||
          tool.searchTerms.any((term) => term.toLowerCase().contains(query));
    }).toList();

    final grouped = <ToolCategory, List<ToolDefinition>>{};
    for (final tool in filtered) {
      grouped.putIfAbsent(tool.category, () => <ToolDefinition>[]).add(tool);
    }

    return ListView(
      padding: const EdgeInsets.all(DS.spacing16),
      children: [
        TextField(
          controller: _searchController,
          decoration: InputDecoration(
            hintText: '搜索工具、能力或关键词',
            prefixIcon: const Icon(Icons.search_rounded),
            suffixIcon: query.isEmpty
                ? null
                : IconButton(
                    onPressed: _searchController.clear,
                    icon: const Icon(Icons.close_rounded),
                  ),
          ),
        ),
        if (recentTools.isNotEmpty && query.isEmpty) ...[
          const SizedBox(height: DS.spacing20),
          _SectionHeader(
            title: '最近使用',
            actionLabel: '管理固定',
            onTap: () {
              _tabController.animateTo(1);
            },
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: recentTools
                .map(
                  (tool) => _LibraryToolCard(
                    tool: tool,
                    pinned: prefs.pinnedToolIds.contains(tool.id),
                    onOpen: () => launchTool(
                      context,
                      ref,
                      tool.id,
                      launchContext: ToolLaunchContext.toolLibrary,
                    ),
                    onTogglePin: () => ref
                        .read(toolPreferencesProvider.notifier)
                        .togglePinned(tool.id),
                  ),
                )
                .toList(),
          ),
        ],
        const SizedBox(height: DS.spacing20),
        for (final entry in grouped.entries) ...[
          _SectionHeader(title: _categoryLabel(entry.key)),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: entry.value
                .map(
                  (tool) => _LibraryToolCard(
                    tool: tool,
                    pinned: prefs.pinnedToolIds.contains(tool.id),
                    onOpen: () => launchTool(
                      context,
                      ref,
                      tool.id,
                      launchContext: ToolLaunchContext.toolLibrary,
                    ),
                    onTogglePin: () => ref
                        .read(toolPreferencesProvider.notifier)
                        .togglePinned(tool.id),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: DS.spacing20),
        ],
      ],
    );
  }

  Widget _buildManageTab(BuildContext context, ToolPreferences prefs) {
    final pinned = prefs.pinnedToolIds.map(ToolRegistry.getById).toList();
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing16,
            DS.spacing16,
            DS.spacing8,
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  '首页首屏显示前 4 个，展开显示前 8 个。拖动可调整顺序。',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              ),
              SparkleButton.ghost(
                label: '回到浏览',
                onPressed: () => _tabController.animateTo(0),
              ),
            ],
          ),
        ),
        Expanded(
          child: ReorderableListView.builder(
            padding: const EdgeInsets.all(DS.spacing16),
            itemCount: pinned.length,
            onReorder: (oldIndex, newIndex) => ref
                .read(toolPreferencesProvider.notifier)
                .reorderPinned(oldIndex, newIndex),
            itemBuilder: (context, index) {
              final tool = pinned[index];
              return Card(
                key: ValueKey(tool.id),
                margin: const EdgeInsets.only(bottom: DS.spacing12),
                child: ListTile(
                  leading: Icon(tool.icon, color: DS.brandPrimaryConst),
                  title: Text(tool.title),
                  subtitle: Text(
                    '${index < 4 ? '首屏' : index < 8 ? '展开区' : '更多页'} · ${_categoryLabel(tool.category)}',
                  ),
                  trailing: IconButton(
                    onPressed: () => ref
                        .read(toolPreferencesProvider.notifier)
                        .unpin(tool.id),
                    icon: const Icon(Icons.push_pin_outlined),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  String _categoryLabel(ToolCategory category) {
    switch (category) {
      case ToolCategory.input:
        return '输入处理';
      case ToolCategory.study:
        return '学习辅助';
      case ToolCategory.efficiency:
        return '效率辅助';
      case ToolCategory.cognition:
        return '认知洞察';
    }
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    this.actionLabel,
    this.onTap,
  });

  final String title;
  final String? actionLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const Spacer(),
          if (actionLabel != null)
            TextButton(
              onPressed: onTap,
              child: Text(actionLabel!),
            ),
        ],
      );
}

class _LibraryToolCard extends StatelessWidget {
  const _LibraryToolCard({
    required this.tool,
    required this.pinned,
    required this.onOpen,
    required this.onTogglePin,
  });

  final ToolDefinition tool;
  final bool pinned;
  final VoidCallback onOpen;
  final VoidCallback onTogglePin;

  @override
  Widget build(BuildContext context) {
    final accent = _accentForCategory(tool.category);
    final background = Color.lerp(
          DS.surfacePrimary,
          accent,
          Theme.of(context).brightness == Brightness.dark ? 0.12 : 0.05,
        ) ??
        DS.surfacePrimary;
    return SizedBox(
      width: 168,
      child: Material(
        color: background,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: onOpen,
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: accent.withValues(alpha: 0.18)),
            ),
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(DS.spacing10),
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(tool.icon, color: accent),
                    ),
                    const Spacer(),
                    IconButton(
                      onPressed: onTogglePin,
                      icon: Icon(
                        pinned ? Icons.push_pin : Icons.push_pin_outlined,
                        size: 18,
                        color: pinned ? DS.warning : DS.textSecondary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing12),
                Text(
                  tool.title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  _categoryLabel(tool.category),
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: accent,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                if (tool.description != null) ...[
                  const SizedBox(height: DS.spacing8),
                  Text(
                    tool.description!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.45,
                        ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

String _categoryLabel(ToolCategory category) {
  switch (category) {
    case ToolCategory.input:
      return '输入处理';
    case ToolCategory.study:
      return '学习辅助';
    case ToolCategory.efficiency:
      return '效率辅助';
    case ToolCategory.cognition:
      return '认知洞察';
  }
}

Color _accentForCategory(ToolCategory category) {
  switch (category) {
    case ToolCategory.input:
      return DS.info;
    case ToolCategory.study:
      return DS.prismPurple;
    case ToolCategory.efficiency:
      return DS.brandPrimary;
    case ToolCategory.cognition:
      return DS.capsuleAccent;
  }
}
