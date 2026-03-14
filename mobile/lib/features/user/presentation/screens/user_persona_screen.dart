import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/memory/memory.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class UserPersonaScreen extends ConsumerStatefulWidget {
  const UserPersonaScreen({
    super.key,
    this.initialOverrideKey,
  });

  final String? initialOverrideKey;

  @override
  ConsumerState<UserPersonaScreen> createState() => _UserPersonaScreenState();
}

class _UserPersonaScreenState extends ConsumerState<UserPersonaScreen> {
  final ScrollController _scrollController = ScrollController();
  final Map<String, GlobalKey> _inferredItemKeys = <String, GlobalKey>{};
  String? _handledInitialOverrideKey;

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final profileAsync = ref.watch(transparentProfileProvider);
    ref.watch(profileContextProvider);
    final inferredAsync = ref.watch(inferredPreferencesProvider);
    final policiesAsync = ref.watch(activePoliciesProvider);
    final onboardingCompleted = ref.watch(onboardingCompletedProvider);
    final inferredItems = inferredAsync.maybeWhen(
      data: (items) => items,
      orElse: () => const <Map<String, dynamic>>[],
    );
    _maybeHandleInitialOverride(context, ref, inferredItems);
    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: Text(l10n.personaMyProfile),
      ),
      child: profileAsync.when(
        data: (data) => _buildContent(
          context,
          ref,
          l10n,
          data,
          onboardingCompleted,
          inferredItems,
          policiesAsync.maybeWhen(
            data: (items) => items,
            orElse: () => const <Map<String, dynamic>>[],
          ),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(
          child: Text(l10n.personaLoadFailed(err.toString())),
        ),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
    Map<String, dynamic> data,
    bool completed,
    List<Map<String, dynamic>> inferredPreferences,
    List<Map<String, dynamic>> activePolicies,
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
        controller: _scrollController,
        padding: const EdgeInsets.all(DS.spacing16),
        children: [
          _buildOnboardingBanner(context, l10n, completed),
          _sectionTitle(l10n.personaL1Title),
          _subSectionList(
            l10n.personaPreferences,
            preferences
                .map((item) => _preferenceRow(ref, context, l10n, item))
                .toList(),
            l10n,
          ),
          _subSectionList(
            l10n.personaGoals,
            goals.map((item) => _goalRow(ref, context, l10n, item)).toList(),
            l10n,
          ),
          const SizedBox(height: DS.spacing24),
          _sectionTitle('System Inference'),
          _subSectionList(
            'Inferred Preferences',
            inferredPreferences
                .map((item) => _inferredPreferenceRow(ref, context, l10n, item))
                .toList(),
            l10n,
          ),
          _subSectionList(
            'Active Policies',
            activePolicies
                .map((item) => _policyRow(l10n, item))
                .toList(),
            l10n,
          ),
          const SizedBox(height: DS.spacing24),
          _sectionTitle(l10n.personaL2Title),
          _subSectionList(
            l10n.personaTags,
            tags
                .map(
                  (item) => _suggestableRow(
                    ref,
                    context,
                    l10n: l10n,
                    label: item['value']?.toString() ?? '',
                    metadata: item['metadata'] as Map<String, dynamic>? ?? {},
                    targetType: 'persona_tag',
                  ),
                )
                .toList(),
            l10n,
          ),
          _subSectionList(
            l10n.personaCapabilities,
            capabilities
                .map(
                  (item) => _suggestableRow(
                    ref,
                    context,
                    l10n: l10n,
                    label: '${item['key']}: ${item['value']}',
                    metadata: item['metadata'] as Map<String, dynamic>? ?? {},
                    targetType: 'persona_capability',
                    fieldName: item['key']?.toString(),
                  ),
                )
                .toList(),
            l10n,
          ),
          const SizedBox(height: DS.spacing24),
          _sectionTitle(l10n.personaL3Title),
          Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing8),
            child: Text(
              l10n.personaL3Hint,
              style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeSm),
            ),
          ),
          _subSectionList(
            l10n.personaPatterns,
            patterns.map((item) => _readonlyRow(l10n, item)).toList(),
            l10n,
          ),
          _subSectionList(
            l10n.personaFragments,
            fragments.map((item) => _readonlyRow(l10n, item)).toList(),
            l10n,
          ),
        ],
      ),
    );
  }

  Widget _inferredPreferenceRow(
    WidgetRef ref,
    BuildContext context,
    AppLocalizations l10n,
    Map<String, dynamic> item,
  ) {
    final key = item['key']?.toString() ?? 'unknown';
    final value = item['value'];
    final explanation = item['explanation']?.toString() ?? '';
    final source = item['source']?.toString() ?? 'system';
    final adjustable = item['adjustable'] == true;
    final overridden = item['overridden'] == true;
    final metadata = <String, dynamic>{
      'level': adjustable ? 'editable' : 'readonly',
      'reason': explanation.isNotEmpty ? explanation : 'Inferred from recent behavior.',
      'confidence': null,
    };
    return KeyedSubtree(
      key: _itemKeyFor(key),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: _metadataRow(
              l10n,
              '$key: ${_formatValue(value)} (${overridden ? 'override' : source})',
              metadata,
            ),
          ),
          const SizedBox(width: DS.spacing8),
          SizedBox(
            width: 88,
            child: Wrap(
              alignment: WrapAlignment.end,
              runSpacing: DS.spacing8,
              children: [
                SparkleButton.ghost(
                  onPressed: () => context.push(
                    MemoryRoutes.detail,
                    extra: MemoryDetailArgs.preferenceKey(key),
                  ),
                  label: 'History',
                ),
                if (adjustable)
                  SparkleButton.ghost(
                    onPressed: () => _openOverrideInferredDialog(
                      ref,
                      context,
                      key,
                      value,
                    ),
                    label: overridden ? 'Update' : 'Adjust',
                  ),
                if (overridden)
                  SparkleButton.ghost(
                    onPressed: () => _resetOverride(ref, context, key),
                    label: 'Reset',
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  GlobalKey _itemKeyFor(String key) =>
      _inferredItemKeys.putIfAbsent(key, GlobalKey.new);

  void _maybeHandleInitialOverride(
    BuildContext context,
    WidgetRef ref,
    List<Map<String, dynamic>> inferredItems,
  ) {
    final key = widget.initialOverrideKey;
    if (key == null || key.isEmpty || _handledInitialOverrideKey == key) {
      return;
    }
    Map<String, dynamic>? match;
    for (final item in inferredItems) {
      if (item['key']?.toString() == key) {
        match = item;
        break;
      }
    }
    if (match == null) {
      return;
    }
    _handledInitialOverrideKey = key;
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final targetContext = _itemKeyFor(key).currentContext;
      if (targetContext != null) {
        await Scrollable.ensureVisible(
          targetContext,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOutCubic,
        );
      }
      if (!mounted) {
        return;
      }
      final matchedItem = match;
      if (matchedItem == null) {
        return;
      }
      await _openOverrideInferredDialog(ref, context, key, matchedItem['value']);
    });
  }

  Widget _policyRow(AppLocalizations l10n, Map<String, dynamic> item) {
    final signal = item['signal']?.toString() ?? 'policy';
    final effect = item['effect']?.toString() ?? '';
    final sourcePattern = item['source_pattern']?.toString() ?? '';
    return _metadataRow(
      l10n,
      '$signal: $effect',
      <String, dynamic>{
        'level': 'readonly',
        'reason': sourcePattern.isNotEmpty
            ? 'Source pattern: $sourcePattern'
            : 'Currently active strategy.',
        'confidence': null,
      },
    );
  }

  Widget _buildOnboardingBanner(BuildContext context, AppLocalizations l10n, bool completed) =>
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
                  completed ? l10n.personaCompleted : l10n.personaIncomplete,
                  style: TextStyle(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              SparkleButton.ghost(
                onPressed: () {
                  unawaited(context.push(UserRoutes.personaOnboarding));
                },
                label: completed ? l10n.personaRefill : l10n.personaStart,
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

  Widget _subSectionList(String title, List<Widget> items, AppLocalizations l10n) => Padding(
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
                  l10n.personaNoData,
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
    AppLocalizations l10n,
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
          child: _metadataRow(l10n, '$key: ${_formatValue(value)}', meta),
        ),
        if (canEdit)
          SparkleButton.ghost(
            onPressed: () =>
                _openEditPreferenceDialog(ref, context, l10n, key, value),
            label: l10n.personaEdit,
          ),
        if (canRollback)
          SparkleButton.ghost(
            onPressed: () => _confirmRollback(ref, context, l10n, key),
            label: l10n.personaRollback,
          ),
      ],
    );
  }

  Widget _goalRow(
    WidgetRef ref,
    BuildContext context,
    AppLocalizations l10n,
    Map<String, dynamic> item,
  ) {
    final title =
        item['title']?.toString() ?? item['value']?.toString() ?? l10n.personaGoals;
    final status = item['status']?.toString() ?? 'unknown';
    final meta = item['metadata'] as Map<String, dynamic>? ?? {};
    final goalId = item['id']?.toString();
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: _metadataRow(l10n, '$title ($status)', meta),
        ),
        if (goalId != null)
          SparkleButton.ghost(
            onPressed: () =>
                _openEditGoalDialog(ref, context, l10n, goalId, title, status),
            label: l10n.personaEdit,
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

  Widget _levelChip(AppLocalizations l10n, String level) {
    String label;
    Color bg;
    Color fg;
    switch (level) {
      case 'editable':
        label = l10n.personaLevelEditable;
        bg = DS.primaryBase.withValues(alpha: 0.12);
        fg = DS.primaryBase;
      case 'warn':
        label = l10n.personaLevelWarn;
        bg = DS.warning.withValues(alpha: 0.12);
        fg = DS.warning;
      default:
        label = l10n.personaLevelReadonly;
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

  Widget _metadataRow(AppLocalizations l10n, String label, Map<String, dynamic> metadata) {
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
              _levelChip(l10n, level),
            ],
          ),
          if (confidenceLabel != null && confidenceLabel.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: DS.spacing16, top: 2),
              child: Text(
                l10n.personaConfidence(confidenceLabel),
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

  Widget _readonlyRow(AppLocalizations l10n, Map<String, dynamic> item) {
    final label = item['name']?.toString() ??
        item['content']?.toString() ??
        item['value']?.toString() ??
        l10n.personaNoData;
    final meta = item['metadata'] as Map<String, dynamic>? ?? {};
    return _metadataRow(l10n, label, meta);
  }

  Widget _suggestableRow(
    WidgetRef ref,
    BuildContext context, {
    required AppLocalizations l10n,
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
            child: _metadataRow(l10n, label, metadata),
          ),
          if (canSuggest)
            SparkleButton.ghost(
              onPressed: () => _openSuggestionDialog(
                ref,
                context,
                l10n: l10n,
                targetType: targetType,
                fieldName: fieldName,
                label: label,
              ),
              label: l10n.personaSuggestCorrection,
            ),
        ],
      ),
    );
  }

  Future<void> _openSuggestionDialog(
    WidgetRef ref,
    BuildContext context, {
    required AppLocalizations l10n,
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
        title: Text(l10n.personaCorrectionDialogTitle),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(label),
            const SizedBox(height: DS.spacing8),
            Text(
              l10n.personaCorrectionHint,
              style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeSm),
            ),
            const SizedBox(height: DS.spacing12),
            TextField(
              controller: controller,
              decoration: InputDecoration(
                labelText: l10n.personaCorrectionValue,
              ),
            ),
            const SizedBox(height: DS.spacing12),
            TextField(
              controller: reasonController,
              decoration: InputDecoration(
                labelText: l10n.personaCorrectionReason,
              ),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(),
            label: l10n.cancel,
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
                AppFeedback.success(context, l10n.personaCorrectionSubmitted);
              }
              if (context.mounted) {
                Navigator.of(context).pop();
              }
            },
            label: l10n.confirm,
          ),
        ],
      ),
    );
  }

  Future<void> _openEditPreferenceDialog(
    WidgetRef ref,
    BuildContext context,
    AppLocalizations l10n,
    String prefKey,
    dynamic currentValue,
  ) async {
    final controller = TextEditingController(text: _formatValue(currentValue));
    final repo = ref.read(userRepositoryProvider);
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.personaEditPreference),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(prefKey),
            const SizedBox(height: DS.spacing12),
            TextField(
              controller: controller,
              decoration: InputDecoration(labelText: l10n.personaNewPreferenceValue),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(),
            label: l10n.cancel,
          ),
          SparkleButton(
            onPressed: () async {
              final nextValue = controller.text.trim();
              if (nextValue.isEmpty) {
                if (context.mounted) {
                  AppFeedback.info(context, l10n.personaPleaseEnterValue);
                }
                return;
              }
              await repo.updateTransparentPreference(
                prefKey: prefKey,
                value: nextValue,
              );
              ref.invalidate(transparentProfileProvider);
              ref.invalidate(profileContextProvider);
              ref.invalidate(inferredPreferencesProvider);
              ref.invalidate(activePoliciesProvider);
              if (context.mounted) {
                Navigator.of(context).pop();
              }
            },
            label: l10n.confirm,
          ),
        ],
      ),
    );
  }

  Future<void> _confirmRollback(
    WidgetRef ref,
    BuildContext context,
    AppLocalizations l10n,
    String prefKey,
  ) async {
    final repo = ref.read(userRepositoryProvider);
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.personaRollbackTitle),
        content: Text(l10n.personaRollbackConfirm),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(false),
            label: l10n.cancel,
          ),
          SparkleButton.destructive(
            onPressed: () => Navigator.of(context).pop(true),
            label: l10n.personaConfirmRollback,
          ),
        ],
      ),
    );
    if (result ?? false) {
      await repo.rollbackTransparentPreference(prefKey);
      ref.invalidate(transparentProfileProvider);
      ref.invalidate(profileContextProvider);
      ref.invalidate(inferredPreferencesProvider);
      ref.invalidate(activePoliciesProvider);
    }
  }

  Future<void> _openEditGoalDialog(
    WidgetRef ref,
    BuildContext context,
    AppLocalizations l10n,
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
          title: Text(l10n.personaEditGoal),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: controller,
                decoration: InputDecoration(labelText: l10n.personaGoalContent),
              ),
              const SizedBox(height: DS.spacing12),
              DropdownButtonFormField<String>(
                initialValue: nextStatus,
                decoration: InputDecoration(labelText: l10n.personaGoalStatus),
                items: [
                  DropdownMenuItem(value: 'active', child: Text(l10n.personaStatusActive)),
                  DropdownMenuItem(value: 'completed', child: Text(l10n.personaStatusCompleted)),
                  DropdownMenuItem(value: 'paused', child: Text(l10n.personaStatusPaused)),
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
              label: l10n.cancel,
            ),
            SparkleButton(
              onPressed: () async {
                final nextTitle = controller.text.trim();
                if (nextTitle.isEmpty) {
                  if (context.mounted) {
                    AppFeedback.info(context, l10n.personaPleaseEnterGoal);
                  }
                  return;
                }
                await repo.updateGoal(
                  goalId: goalId,
                  title: nextTitle,
                  status: nextStatus,
                );
                ref.invalidate(transparentProfileProvider);
                ref.invalidate(profileContextProvider);
                ref.invalidate(activePoliciesProvider);
                if (context.mounted) {
                  Navigator.of(context).pop();
                }
              },
              label: l10n.confirm,
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

  Future<void> _openOverrideInferredDialog(
    WidgetRef ref,
    BuildContext context,
    String key,
    dynamic currentValue,
  ) async {
    final controller = TextEditingController(text: _formatValue(currentValue));
    final repo = ref.read(userRepositoryProvider);
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Adjust inferred preference'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(key),
            const SizedBox(height: DS.spacing12),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'New value',
              ),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.of(context).pop(),
            label: context.l10n.cancel,
          ),
          SparkleButton(
            onPressed: () async {
              final nextValue = controller.text.trim();
              if (nextValue.isEmpty) {
                if (context.mounted) {
                  AppFeedback.info(context, 'Please enter a value');
                }
                return;
              }
              await repo.overrideInferredPreference(
                key: key,
                value: nextValue,
              );
              ref.invalidate(transparentProfileProvider);
              ref.invalidate(profileContextProvider);
              ref.invalidate(inferredPreferencesProvider);
              ref.invalidate(activePoliciesProvider);
              if (context.mounted) {
                Navigator.of(context).pop();
              }
            },
            label: context.l10n.confirm,
          ),
        ],
      ),
    );
  }

  Future<void> _resetOverride(
    WidgetRef ref,
    BuildContext context,
    String key,
  ) async {
    final repo = ref.read(userRepositoryProvider);
    await repo.resetInferredOverride(key);
    ref.invalidate(transparentProfileProvider);
    ref.invalidate(profileContextProvider);
    ref.invalidate(inferredPreferencesProvider);
    ref.invalidate(activePoliciesProvider);
  }
}
