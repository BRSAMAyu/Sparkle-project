import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/user_routes.dart';

class UserPersonaScreen extends ConsumerWidget {
  const UserPersonaScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(transparentProfileProvider);
    final onboardingCompleted = ref.watch(onboardingCompletedProvider);
    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: const Text('我的画像'),
      ),
      child: profileAsync.when(
        data: (data) => _buildContent(context, ref, data, onboardingCompleted),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(
          child: Text('加载失败：$err'),
        ),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    Map<String, dynamic> data,
    bool completed,
  ) {
    final layer1 = data['layer_1'] as Map<String, dynamic>? ?? {};
    final layer2 = data['layer_2'] as Map<String, dynamic>? ?? {};
    final layer3 = data['layer_3'] as Map<String, dynamic>? ?? {};

    final preferences = _normalizeEntries(layer1['preferences']);
    final goals = _normalizeEntries(layer1['goals']);
    final persona = layer2['persona'] as Map<String, dynamic>? ?? {};
    final tags = _normalizeEntries(persona['tags'], keyName: 'value');
    final capabilities = _normalizeEntries(persona['capabilities']);
    final patterns = _normalizeEntries(layer3['patterns']);
    final fragments = _normalizeEntries(layer3['fragments']);

    return ContentConstraint(
      child: ListView(
        padding: const EdgeInsets.all(DS.spacing16),
        children: [
          _buildOnboardingBanner(context, completed),
          _sectionTitle('L1 用户声明'),
          _subSectionList(
            '偏好',
            preferences
                .map((item) => _preferenceRow(ref, context, item))
                .toList(),
          ),
          _subSectionList(
            '目标',
            goals.map((item) => _goalRow(ref, context, item)).toList(),
          ),
          const SizedBox(height: DS.spacing24),
          _sectionTitle('L2 协作校准'),
          _subSectionList(
            '标签',
            tags
                .map(
                  (item) => _suggestableRow(
                    ref,
                    context,
                    label: item['value']?.toString() ?? '',
                    metadata: item['metadata'] as Map<String, dynamic>? ?? {},
                    targetType: 'persona_tag',
                  ),
                )
                .toList(),
          ),
          _subSectionList(
            '能力',
            capabilities
                .map(
                  (item) => _suggestableRow(
                    ref,
                    context,
                    label: '${item['key']}: ${item['value']}',
                    metadata: item['metadata'] as Map<String, dynamic>? ?? {},
                    targetType: 'persona_capability',
                    fieldName: item['key']?.toString(),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: DS.spacing24),
          _sectionTitle('L3 系统推断'),
          Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing8),
            child: Text(
              '以下内容来自系统分析，仅供参考',
              style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeSm),
            ),
          ),
          _subSectionList(
            '行为模式',
            patterns.map(_readonlyRow).toList(),
          ),
          _subSectionList(
            '认知碎片',
            fragments.map(_readonlyRow).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildOnboardingBanner(BuildContext context, bool completed) =>
      Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing16),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.accent,
          padding: const EdgeInsets.all(DS.spacing12),
          child: Row(
            children: [
              Icon(
                Icons.assignment_turned_in_outlined,
                color: DS.primaryBase,
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Text(
                  completed ? '画像已完善，可随时重新填写' : '完善画像，提升个性化体验',
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              SparkleButton.ghost(
                onPressed: () {
                  context.push(UserRoutes.personaOnboarding);
                },
                label: completed ? '再次填写' : '开始',
              ),
            ],
          ),
        ),
      );

  Widget _sectionTitle(String title) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing8),
        child: Text(
          title,
          style: TextStyle(
            fontSize: DS.fontSizeLg,
            fontWeight: DS.fontWeightBold,
            color: DS.textPrimary,
          ),
        ),
      );

  Widget _subSectionList(String title, List<Widget> items) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing16),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          padding: const EdgeInsets.all(DS.spacing12),
          child: Column(
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
              if (items.isEmpty)
                Text(
                  '暂无数据',
                  style: TextStyle(color: DS.neutral500),
                )
              else
                ...items,
            ],
          ),
        ),
      );

  Widget _preferenceRow(
    WidgetRef ref,
    BuildContext context,
    Map<String, dynamic> item,
  ) {
    final key = item['key']?.toString() ?? 'unknown';
    final value = item['value'];
    final meta = item['metadata'] as Map<String, dynamic>? ?? {};
    final canRollback = item['can_rollback'] == true;
    final canEdit = meta['level']?.toString() == 'editable';
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: _metadataRow('$key: ${_formatValue(value)}', meta),
        ),
        if (canEdit)
          SparkleButton.ghost(
            onPressed: () =>
                _openEditPreferenceDialog(ref, context, key, value),
            label: '编辑',
          ),
        if (canRollback)
          SparkleButton.ghost(
            onPressed: () => _confirmRollback(ref, context, key),
            label: '回滚',
          ),
      ],
    );
  }

  Widget _goalRow(
    WidgetRef ref,
    BuildContext context,
    Map<String, dynamic> item,
  ) {
    final title =
        item['title']?.toString() ?? item['value']?.toString() ?? '目标';
    final status = item['status']?.toString() ?? 'unknown';
    final meta = item['metadata'] as Map<String, dynamic>? ?? {};
    final goalId = item['id']?.toString();
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: _metadataRow('$title ($status)', meta),
        ),
        if (goalId != null)
          SparkleButton.ghost(
            onPressed: () =>
                _openEditGoalDialog(ref, context, goalId, title, status),
            label: '编辑',
          ),
      ],
    );
  }

  String _formatValue(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value.entries.map((e) => '${e.key}: ${e.value}').join(', ');
    }
    return value?.toString() ?? '';
  }

  Widget _levelChip(String level) {
    String label;
    Color bg;
    Color fg;
    switch (level) {
      case 'editable':
        label = '可编辑';
        bg = DS.primaryBase.withValues(alpha: 0.12);
        fg = DS.primaryBase;
      case 'warn':
        label = '建议修正';
        bg = DS.warning.withValues(alpha: 0.12);
        fg = DS.warning;
      default:
        label = '只读';
        bg = DS.neutral100;
        fg = DS.neutral600;
    }
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: 2,
      ),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: DS.borderRadius12,
        border: Border.all(color: DS.neutral200),
      ),
      child: Text(
        label,
        style: TextStyle(color: fg, fontSize: DS.fontSizeSm),
      ),
    );
  }

  Widget _metadataRow(String label, Map<String, dynamic> metadata) {
    final reason = metadata['reason']?.toString() ?? '';
    final level = metadata['level']?.toString() ?? 'readonly';
    final confidence = metadata['confidence'];
    final confidenceLabel = confidence is num
        ? confidence.toStringAsFixed(2)
        : confidence?.toString();
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child:
                    Text('• $label', style: TextStyle(color: DS.textPrimary)),
              ),
              _levelChip(level),
            ],
          ),
          if (confidenceLabel != null && confidenceLabel.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: DS.spacing16, top: 2),
              child: Text(
                '置信度 $confidenceLabel',
                style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeSm),
              ),
            ),
          if (reason.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: DS.spacing16, top: 4),
              child: Text(
                reason,
                style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeSm),
              ),
            ),
        ],
      ),
    );
  }

  Widget _readonlyRow(Map<String, dynamic> item) {
    final label = item['name']?.toString() ??
        item['content']?.toString() ??
        item['value']?.toString() ??
        '条目';
    final meta = item['metadata'] as Map<String, dynamic>? ?? {};
    return _metadataRow(label, meta);
  }

  Widget _suggestableRow(
    WidgetRef ref,
    BuildContext context, {
    required String label,
    required Map<String, dynamic> metadata,
    required String targetType,
    String? fieldName,
  }) {
    final level = metadata['level']?.toString() ?? 'readonly';
    final canSuggest = level == 'warn';
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: _metadataRow(label, metadata),
          ),
          if (canSuggest)
            SparkleButton.ghost(
              onPressed: () => _openSuggestionDialog(
                ref,
                context,
                targetType: targetType,
                fieldName: fieldName,
                label: label,
              ),
              label: '建议修正',
            ),
        ],
      ),
    );
  }

  Future<void> _openSuggestionDialog(
    WidgetRef ref,
    BuildContext context, {
    required String targetType,
    required String label,
    String? fieldName,
  }) async {
    final controller = TextEditingController();
    final reasonController = TextEditingController();
    final repo = ref.read(userRepositoryProvider);
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('建议修正'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(label),
            const SizedBox(height: DS.spacing8),
            Text(
              '提交后系统会评估并逐步调整画像，可能影响推荐策略。',
              style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeSm),
            ),
            const SizedBox(height: DS.spacing12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: '你建议的内容',
              ),
            ),
            const SizedBox(height: DS.spacing12),
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                labelText: '原因（可选）',
              ),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(),
            label: '取消',
          ),
          SparkleButton(
            onPressed: () async {
              await repo.submitProfileCorrection({
                'target_type': targetType,
                'field_name': fieldName,
                'suggested_value': controller.text.trim(),
                'reason': reasonController.text.trim(),
              });
              if (context.mounted) {
                AppFeedback.success(context, '已提交修正建议');
              }
              if (context.mounted) {
                Navigator.of(context).pop();
              }
            },
            label: '提交',
          ),
        ],
      ),
    );
  }

  Future<void> _openEditPreferenceDialog(
    WidgetRef ref,
    BuildContext context,
    String prefKey,
    dynamic currentValue,
  ) async {
    final controller = TextEditingController(text: _formatValue(currentValue));
    final repo = ref.read(userRepositoryProvider);
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('编辑偏好'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(prefKey),
            const SizedBox(height: DS.spacing12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(labelText: '新的偏好值'),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(),
            label: '取消',
          ),
          SparkleButton(
            onPressed: () async {
              final nextValue = controller.text.trim();
              if (nextValue.isEmpty) {
                if (context.mounted) {
                  AppFeedback.info(context, '请输入偏好值');
                }
                return;
              }
              await repo.updateTransparentPreference(
                prefKey: prefKey,
                value: nextValue,
              );
              ref.invalidate(transparentProfileProvider);
              if (context.mounted) {
                Navigator.of(context).pop();
              }
            },
            label: '保存',
          ),
        ],
      ),
    );
  }

  Future<void> _confirmRollback(
    WidgetRef ref,
    BuildContext context,
    String prefKey,
  ) async {
    final repo = ref.read(userRepositoryProvider);
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('回滚偏好'),
        content: const Text('将偏好回滚到上一个版本，可能影响推荐效果。'),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(false),
            label: '取消',
          ),
          SparkleButton.destructive(
            onPressed: () => Navigator.of(context).pop(true),
            label: '确认回滚',
          ),
        ],
      ),
    );
    if (result ?? false) {
      await repo.rollbackTransparentPreference(prefKey);
      ref.invalidate(transparentProfileProvider);
    }
  }

  Future<void> _openEditGoalDialog(
    WidgetRef ref,
    BuildContext context,
    String goalId,
    String title,
    String status,
  ) async {
    final controller = TextEditingController(text: title);
    final allowedStatuses = ['active', 'completed', 'paused'];
    var nextStatus = allowedStatuses.contains(status) ? status : 'active';
    final repo = ref.read(userRepositoryProvider);
    await showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('编辑目标'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: controller,
                decoration: const InputDecoration(labelText: '目标内容'),
              ),
              const SizedBox(height: DS.spacing12),
              DropdownButtonFormField<String>(
                initialValue: nextStatus,
                decoration: const InputDecoration(labelText: '状态'),
                items: const [
                  DropdownMenuItem(value: 'active', child: Text('进行中')),
                  DropdownMenuItem(value: 'completed', child: Text('已完成')),
                  DropdownMenuItem(value: 'paused', child: Text('暂停')),
                ],
                onChanged: (value) {
                  if (value != null) {
                    setState(() {
                      nextStatus = value;
                    });
                  }
                },
              ),
            ],
          ),
          actions: [
            SparkleButton.ghost(
              onPressed: () => Navigator.of(context).pop(),
              label: '取消',
            ),
            SparkleButton(
              onPressed: () async {
                final nextTitle = controller.text.trim();
                if (nextTitle.isEmpty) {
                  if (context.mounted) {
                    AppFeedback.info(context, '请输入目标内容');
                  }
                  return;
                }
                await repo.updateGoal(
                  goalId: goalId,
                  title: nextTitle,
                  status: nextStatus,
                );
                ref.invalidate(transparentProfileProvider);
                if (context.mounted) {
                  Navigator.of(context).pop();
                }
              },
              label: '保存',
            ),
          ],
        ),
      ),
    );
  }

  List<Map<String, dynamic>> _normalizeEntries(
    dynamic source, {
    String keyName = 'key',
  }) {
    if (source is List) {
      return source.map((item) {
        if (item is Map) {
          return Map<String, dynamic>.from(item);
        }
        return <String, dynamic>{
          keyName: item.toString(),
          'value': item,
          'metadata': const <String, dynamic>{},
        };
      }).toList();
    }

    if (source is Map) {
      return source.entries
          .map(
            (entry) => <String, dynamic>{
              keyName: entry.key.toString(),
              'value': entry.value,
              'metadata': const <String, dynamic>{},
            },
          )
          .toList();
    }

    return const <Map<String, dynamic>>[];
  }
}
