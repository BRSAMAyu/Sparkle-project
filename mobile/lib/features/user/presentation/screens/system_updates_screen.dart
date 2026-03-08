import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

class SystemUpdatesScreen extends ConsumerStatefulWidget {
  const SystemUpdatesScreen({super.key});

  @override
  ConsumerState<SystemUpdatesScreen> createState() =>
      _SystemUpdatesScreenState();
}

class _SystemUpdatesScreenState extends ConsumerState<SystemUpdatesScreen> {
  final TextEditingController _searchController = TextEditingController();
  String _categoryFilter = '全部';
  String _priorityFilter = '全部';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final updatesAsync = ref.watch(systemUpdatesProvider);
    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: const Text('系统活动'),
      ),
      child: updatesAsync.when(
        data: (items) => ContentConstraint(child: _buildList(context, items)),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('加载失败：$err')),
      ),
    );
  }

  Widget _buildList(
    BuildContext context,
    List<Map<String, dynamic>> items,
  ) {
    final categories = _collectOptions(items, 'category');
    final priorities = _collectOptions(items, 'priority');
    final filtered = _applyFilters(items);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(systemUpdatesProvider);
        await ref.read(systemUpdatesProvider.future);
      },
      child: ListView(
        padding: const EdgeInsets.all(DS.spacing16),
        children: [
          GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildSearchField(),
                const SizedBox(height: DS.spacing12),
                _buildFilterRow(
                  title: '类型',
                  options: categories,
                  selected: _categoryFilter,
                  onSelected: (value) =>
                      setState(() => _categoryFilter = value),
                ),
                const SizedBox(height: DS.spacing12),
                _buildFilterRow(
                  title: '优先级',
                  options: priorities,
                  selected: _priorityFilter,
                  onSelected: (value) =>
                      setState(() => _priorityFilter = value),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            '共 ${filtered.length} 条',
            style: TextStyle(color: DS.neutral600, fontSize: DS.fontSizeSm),
          ),
          const SizedBox(height: DS.spacing12),
          if (filtered.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.only(top: DS.spacing32),
                child: Text(
                  '暂无系统更新',
                  style: TextStyle(color: DS.neutral500),
                ),
              ),
            )
          else
            ...filtered.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing12),
                child: _buildUpdateCard(item),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSearchField() => TextField(
        controller: _searchController,
        onChanged: (_) => setState(() {}),
        decoration: InputDecoration(
          prefixIcon: const Icon(Icons.search_rounded),
          hintText: '搜索标题或描述',
          filled: true,
          fillColor: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
          border: OutlineInputBorder(
            borderRadius: DS.borderRadius12,
            borderSide: BorderSide(color: DS.neutral200),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: DS.borderRadius12,
            borderSide: BorderSide(color: DS.neutral200),
          ),
          contentPadding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12, vertical: 12),
        ),
      );

  Widget _buildFilterRow({
    required String title,
    required List<String> options,
    required String selected,
    required ValueChanged<String> onSelected,
  }) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontWeight: DS.fontWeightSemibold,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: options
                .map(
                  (item) => ChoiceChip(
                    label: Text(item),
                    selected: selected == item,
                    selectedColor: DS.primaryBase.withValues(alpha: 0.15),
                    labelStyle: TextStyle(
                      color: selected == item ? DS.primaryBase : DS.neutral600,
                    ),
                    onSelected: (_) => onSelected(item),
                  ),
                )
                .toList(),
          ),
        ],
      );

  Widget _buildUpdateCard(Map<String, dynamic> item) {
    final title = item['title']?.toString() ?? '系统更新';
    final description = item['description']?.toString() ?? '';
    final category = item['category']?.toString() ?? '';
    final priority = item['priority']?.toString() ?? '';
    final createdAt = _formatTime(item['created_at']);

    final priorityStyle = _priorityStyle(priority);

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(DS.spacing12),
      borderColor: priorityStyle.border,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontWeight: DS.fontWeightSemibold,
                    color: DS.textPrimary,
                  ),
                ),
              ),
              if (priority.isNotEmpty)
                _pill(priority, priorityStyle.bg, priorityStyle.fg),
            ],
          ),
          if (createdAt.isNotEmpty)
            Text(
              createdAt,
              style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeSm),
            ),
          if (description.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              description,
              style: TextStyle(color: DS.textSecondary),
            ),
          ],
          if (category.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            _pill(category, DS.neutral100, DS.neutral600),
          ],
        ],
      ),
    );
  }

  List<String> _collectOptions(List<Map<String, dynamic>> items, String key) {
    final values = <String>{'全部'};
    for (final item in items) {
      final value = item[key]?.toString();
      if (value != null && value.isNotEmpty) {
        values.add(value);
      }
    }
    final sorted = values.toList()..sort();
    if (sorted.first != '全部' && sorted.contains('全部')) {
      sorted.remove('全部');
      sorted.insert(0, '全部');
    }
    return sorted;
  }

  List<Map<String, dynamic>> _applyFilters(List<Map<String, dynamic>> items) {
    final keyword = _searchController.text.trim().toLowerCase();
    return items.where((item) {
      final title = item['title']?.toString().toLowerCase() ?? '';
      final description = item['description']?.toString().toLowerCase() ?? '';
      final category = item['category']?.toString() ?? '';
      final priority = item['priority']?.toString() ?? '';

      if (_categoryFilter != '全部' && category != _categoryFilter) {
        return false;
      }
      if (_priorityFilter != '全部' && priority != _priorityFilter) {
        return false;
      }
      if (keyword.isNotEmpty &&
          !title.contains(keyword) &&
          !description.contains(keyword) &&
          !category.toLowerCase().contains(keyword)) {
        return false;
      }
      return true;
    }).toList();
  }

  _PriorityStyle _priorityStyle(String value) {
    switch (value.toLowerCase()) {
      case 'high':
        return _PriorityStyle(
          bg: DS.warning.withValues(alpha: 0.12),
          fg: DS.warning,
          border: DS.warning.withValues(alpha: 0.3),
        );
      case 'medium':
        return _PriorityStyle(
          bg: DS.info.withValues(alpha: 0.12),
          fg: DS.info,
          border: DS.info.withValues(alpha: 0.3),
        );
      case 'low':
      default:
        return _PriorityStyle(
          bg: DS.neutral100,
          fg: DS.neutral600,
          border: DS.neutral200,
        );
    }
  }

  Widget _pill(String text, Color bg, Color fg) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: DS.borderRadius20,
          border: Border.all(color: DS.neutral200),
        ),
        child: Text(
          text,
          style: TextStyle(color: fg, fontSize: DS.fontSizeSm),
        ),
      );

  String _formatTime(dynamic raw) {
    if (raw is int && raw > 0) {
      final dt = DateTime.fromMillisecondsSinceEpoch(raw * 1000);
      return '${dt.month.toString().padLeft(2, '0')}-'
          '${dt.day.toString().padLeft(2, '0')} '
          '${dt.hour.toString().padLeft(2, '0')}:'
          '${dt.minute.toString().padLeft(2, '0')}';
    }
    return '';
  }
}

class _PriorityStyle {
  const _PriorityStyle({
    required this.bg,
    required this.fg,
    required this.border,
  });
  final Color bg;
  final Color fg;
  final Color border;
}
