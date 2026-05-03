import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
    final l10n = context.l10n;

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        backgroundColor: DS.surfaceOverlay.withValues(alpha: 0.94),
        surfaceTintColor: Colors.transparent,
        scrolledUnderElevation: 0,
        title: Text(
          l10n.toolsLibraryTitle,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: DS.fontWeightBold,
                color: DS.textPrimary,
              ),
        ),
        bottom: TabBar(
          controller: _tabController,
          dividerColor: Colors.transparent,
          labelColor: DS.textPrimary,
          unselectedLabelColor: DS.textSecondary,
          tabs: [
            Tab(text: l10n.toolsTabBrowse),
            Tab(text: l10n.toolsTabManage),
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
      final localizedTitle = tool.getLocalizedTitle(l10n: context.l10n).toLowerCase();
      final localizedDesc = (tool.getLocalizedDescription(l10n: context.l10n) ?? '').toLowerCase();
      return localizedTitle.contains(query) ||
          localizedDesc.contains(query) ||
          tool.getLocalizedSearchTerms().any((term) => term.toLowerCase().contains(query));
    }).toList();

    final grouped = <ToolCategory, List<ToolDefinition>>{};
    for (final tool in filtered) {
      grouped.putIfAbsent(tool.category, () => <ToolDefinition>[]).add(tool);
    }

    final l10n = context.l10n;

    return ListView(
      padding: const EdgeInsets.all(DS.spacing16),
      children: [
        SparkleStaggerItem(
          index: 0,
          child: TextField(
            controller: _searchController,
            decoration: InputDecoration(
              filled: true,
              fillColor: Color.alphaBlend(
                DS.info.withValues(alpha: 0.02),
                DS.surfacePrimary,
              ),
              hintText: l10n.toolsSearchHint,
              prefixIcon: const Icon(Icons.search_rounded),
              suffixIcon: query.isEmpty
                  ? null
                  : IconButton(
                      onPressed: _searchController.clear,
                      icon: const Icon(Icons.close_rounded),
                    ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18),
                borderSide: BorderSide(
                  color: DS.border.withValues(alpha: 0.45),
                ),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(18),
                borderSide: BorderSide(
                  color: DS.info.withValues(alpha: 0.35),
                ),
              ),
            ),
          ),
        ),
        if (recentTools.isNotEmpty && query.isEmpty) ...[
          const SizedBox(height: DS.spacing20),
          SparkleStaggerItem(
            index: 1,
            child: _SectionHeader(
              title: l10n.toolsRecentTitle,
              actionLabel: l10n.toolsManagePinned,
              onTap: () {
                _tabController.animateTo(1);
              },
            ),
          ),
          const SizedBox(height: DS.spacing12),
          SparkleStaggerItem(
            index: 2,
            child: Wrap(
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
          ),
        ],
        const SizedBox(height: DS.spacing20),
        for (final indexedEntry in grouped.entries.indexed) ...[
          SparkleStaggerItem(
            index: indexedEntry.$1 + 3,
            child: _SectionHeader(
              title: _categoryLabel(indexedEntry.$2.key, context),
            ),
          ),
          const SizedBox(height: DS.spacing12),
          SparkleStaggerItem(
            index: indexedEntry.$1 + 4,
            child: Wrap(
              spacing: DS.spacing12,
              runSpacing: DS.spacing12,
              children: indexedEntry.$2.value
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
          ),
          const SizedBox(height: DS.spacing20),
        ],
      ],
    );
  }

  Widget _buildManageTab(BuildContext context, ToolPreferences prefs) {
    final pinned = prefs.pinnedToolIds
        .map(ToolRegistry.tryGetById)
        .whereType<ToolDefinition>()
        .toList();
    final l10n = context.l10n;

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
                  l10n.toolsManageHint,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
              ),
              SparkleButton.ghost(
                label: l10n.toolsBackToBrowse,
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
              final positionLabel = index < 4
                  ? l10n.toolsPositionFirstScreen
                  : index < 8
                      ? l10n.toolsPositionExpanded
                      : l10n.toolsPositionMore;
              return Card(
                key: ValueKey(tool.id),
                margin: const EdgeInsets.only(bottom: DS.spacing12),
                elevation: 0,
                color: Color.lerp(DS.surfacePrimary, DS.info, 0.02),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(18),
                  side: BorderSide(color: DS.border.withValues(alpha: 0.45)),
                ),
                child: ListTile(
                  leading: Icon(tool.icon, color: DS.brandPrimaryConst),
                  title: Text(tool.getLocalizedTitle(l10n: context.l10n)),
                  subtitle: Text(
                    '$positionLabel · ${_categoryLabel(tool.category, context)}',
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

  String _categoryLabel(ToolCategory category, BuildContext context) {
    final l10n = context.l10n;
    switch (category) {
      case ToolCategory.input:
        return l10n.toolsCategoryInput;
      case ToolCategory.study:
        return l10n.toolsCategoryStudy;
      case ToolCategory.efficiency:
        return l10n.toolsCategoryEfficiency;
      case ToolCategory.cognition:
        return l10n.toolsCategoryCognition;
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
                  color: DS.textPrimary,
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
      height: 196,
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: onOpen,
          child: Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  background,
                  Color.alphaBlend(
                    accent.withValues(alpha: 0.04),
                    DS.surfacePrimary,
                  ),
                ],
              ),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: accent.withValues(alpha: 0.18)),
              boxShadow: [
                BoxShadow(
                  color: DS.textPrimary.withValues(alpha: 0.05),
                  blurRadius: 16,
                  offset: const Offset(0, 8),
                ),
              ],
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
                      constraints: const BoxConstraints.tightFor(
                        width: 32,
                        height: 32,
                      ),
                      padding: EdgeInsets.zero,
                      visualDensity: VisualDensity.compact,
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
                  tool.getLocalizedTitle(l10n: context.l10n),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  _categoryLabel(tool.category, context),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: accent,
                        fontWeight: DS.fontWeightBold,
                      ),
                ),
                const Spacer(),
                final localizedDesc = tool.getLocalizedDescription(l10n: context.l10n);
                if (localizedDesc != null) ...[
                  const SizedBox(height: DS.spacing8),
                  Text(
                    localizedDesc,
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

String _categoryLabel(ToolCategory category, BuildContext context) {
  final l10n = context.l10n;
  switch (category) {
    case ToolCategory.input:
      return l10n.toolsCategoryInput;
    case ToolCategory.study:
      return l10n.toolsCategoryStudy;
    case ToolCategory.efficiency:
      return l10n.toolsCategoryEfficiency;
    case ToolCategory.cognition:
      return l10n.toolsCategoryCognition;
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
