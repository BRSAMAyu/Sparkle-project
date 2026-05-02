import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
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
  final Map<String, bool> _expandedSections = <String, bool>{
    'summary': true,
    'l3': true,
    'l1': false,
    'l2': false,
    'inference': false,
    'context': false,
  };
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
    final profileContextAsync = ref.watch(profileContextProvider);
    final inferredAsync = ref.watch(inferredPreferencesProvider);
    final policiesAsync = ref.watch(activePoliciesProvider);
    final onboardingCompleted = ref.watch(onboardingCompletedProvider);
    final inferredItems = inferredAsync.maybeWhen(
      data: (items) => items,
      orElse: () => const <Map<String, dynamic>>[],
    );
    _maybeHandleInitialOverride(context, ref, inferredItems);
    final profileLoadError = profileAsync.maybeWhen(
      error: (error, _) => _friendlyError(error),
      orElse: () => null,
    );
    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: Text(l10n.personaMyProfile),
        actions: [
          IconButton(
            tooltip: l10n.personaRefreshPersona,
            onPressed: () => unawaited(_refreshPersona(ref)),
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      child: profileAsync.when(
        data: (data) => _buildContent(
          context,
          ref,
          l10n,
          data,
          onboardingCompleted,
          profileContextAsync,
          inferredAsync,
          policiesAsync,
          profileLoadError: profileLoadError,
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _buildContent(
          context,
          ref,
          l10n,
          const <String, dynamic>{},
          onboardingCompleted,
          profileContextAsync,
          inferredAsync,
          policiesAsync,
          profileLoadError: profileLoadError,
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
      AsyncValue<Map<String, dynamic>> profileContextAsync,
      AsyncValue<List<Map<String, dynamic>>> inferredPreferencesAsync,
      AsyncValue<List<Map<String, dynamic>>> activePoliciesAsync,
      {String? profileLoadError}) {
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
    final readableSummary = _buildReadableSummary(
      l10n: l10n,
      goals: goals,
      preferences: preferences,
      patterns: patterns,
      fragments: fragments,
    );

    return ContentConstraint(
      child: RefreshIndicator(
        onRefresh: () => _refreshPersona(ref),
        child: ListView(
          controller: _scrollController,
          padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
          children: [
            if (profileLoadError != null) ...[
              SparkleStaggerItem(
                index: 0,
                child: _buildProfileLoadWarning(l10n, profileLoadError, ref),
              ),
              const SizedBox(height: DS.spacing12),
            ],
            SparkleStaggerItem(
              index: profileLoadError != null ? 1 : 0,
              child: _buildOnboardingBanner(context, l10n, completed),
            ),
            SparkleStaggerItem(
              index: profileLoadError != null ? 2 : 1,
              child: _buildQuickAccessCard(context),
            ),
            const SizedBox(height: DS.spacing16),
            SparkleStaggerItem(
              index: profileLoadError != null ? 3 : 2,
              child: _buildCollapsibleSection(
                sectionKey: 'summary',
                title: l10n.personaProfileInterpretation,
                subtitle: l10n.personaProfileInterpretationSubtitle,
                child: _buildReadableSummaryCard(l10n, readableSummary),
              ),
            ),
            _buildCollapsibleSection(
              sectionKey: 'l3',
              title: l10n.personaL3Title,
              subtitle: l10n.personaL3Subtitle,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(bottom: DS.spacing8),
                    child: Text(
                      l10n.personaL3Hint,
                      style: TextStyle(
                        color: DS.neutral500,
                        fontSize: DS.fontSizeSm,
                      ),
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
            ),
            _buildCollapsibleSection(
              sectionKey: 'l1',
              title: l10n.personaL1Title,
              subtitle: l10n.personaL1Subtitle,
              child: Column(
                children: [
                  _subSectionList(
                    l10n.personaGoals,
                    goals
                        .map((item) => _goalRow(ref, context, l10n, item))
                        .toList(),
                    l10n,
                  ),
                  _subSectionList(
                    l10n.personaPreferences,
                    preferences
                        .map((item) => _preferenceRow(ref, context, l10n, item))
                        .toList(),
                    l10n,
                  ),
                ],
              ),
            ),
            _buildCollapsibleSection(
              sectionKey: 'l2',
              title: l10n.personaL2Title,
              subtitle: l10n.personaL2Subtitle,
              child: Column(
                children: [
                  _subSectionList(
                    l10n.personaTags,
                    tags
                        .map(
                          (item) => _suggestableRow(
                            ref,
                            context,
                            l10n: l10n,
                            label: item['value']?.toString() ?? '',
                            metadata:
                                item['metadata'] as Map<String, dynamic>? ?? {},
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
                            metadata:
                                item['metadata'] as Map<String, dynamic>? ?? {},
                            targetType: 'persona_capability',
                            fieldName: item['key']?.toString(),
                          ),
                        )
                        .toList(),
                    l10n,
                  ),
                ],
              ),
            ),
            _buildCollapsibleSection(
              sectionKey: 'inference',
              title: l10n.personaInferenceTitle,
              subtitle: l10n.personaInferenceSubtitle,
              child: Column(
                children: [
                  _buildAsyncSection(
                    ref,
                    context,
                    title: I18nService.instance.isChinese ? '推断偏好' : 'Inferred Preferences',
                    asyncValue: inferredPreferencesAsync,
                    builder: (items) => items
                        .map(
                          (item) =>
                              _inferredPreferenceRow(ref, context, l10n, item),
                        )
                        .toList(),
                    onRetry: () => ref.invalidate(inferredPreferencesProvider),
                  ),
                  _buildAsyncSection(
                    ref,
                    context,
                    title: I18nService.instance.isChinese ? '活跃策略' : 'Active Policies',
                    asyncValue: activePoliciesAsync,
                    builder: (items) =>
                        items.map((item) => _policyRow(l10n, item)).toList(),
                    onRetry: () => ref.invalidate(activePoliciesProvider),
                  ),
                ],
              ),
            ),
            _buildCollapsibleSection(
              sectionKey: 'context',
              title: I18nService.instance.isChinese ? '上下文快照' : 'Context Snapshot',
              subtitle: I18nService.instance.isChinese ? '底层上下文快照，默认收起，必要时再展开' : 'Low-level context snapshot, collapsed by default',
              child: _buildAsyncSection(
                ref,
                context,
                title: I18nService.instance.isChinese ? '上下文快照' : 'Context Snapshot',
                asyncValue: profileContextAsync,
                builder: (data) => _buildContextSummaryRows(l10n, data),
                onRetry: () => ref.invalidate(profileContextProvider),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickAccessCard(BuildContext context) {
    final l10n = context.l10n;
    return GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.panel,
        padding: const EdgeInsets.all(DS.spacing12),
        child: Wrap(
          spacing: DS.spacing8,
          runSpacing: DS.spacing8,
          children: [
            SparkleButton.ghost(
              onPressed: () => context.push(UserRoutes.systemUpdates),
              label: l10n.personaQuickAccessSystemUpdates,
            ),
            if (AppFeatureFlags.enableUserMemoryControls)
              SparkleButton.ghost(
                onPressed: () => context.push(MemoryRoutes.settings),
                label: l10n.personaQuickAccessMemorySettings,
              ),
          ],
        ),
      );
  }

  Widget _buildProfileLoadWarning(
      AppLocalizations l10n, String message, WidgetRef ref) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(DS.spacing12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.error_outline_rounded, color: DS.warning),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    l10n.personaCoreProfileUnavailable,
                    style: TextStyle(
                      fontWeight: DS.fontWeightSemibold,
                      color: DS.textPrimary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              l10n.personaDegradedMode(message),
              style: TextStyle(
                color: DS.textSecondary,
                height: 1.45,
              ),
            ),
            const SizedBox(height: DS.spacing12),
            SparkleButton.ghost(
              onPressed: () => unawaited(_refreshPersona(ref)),
              label: l10n.personaRetryFullProfile,
            ),
          ],
        ),
      );

  Widget _buildCollapsibleSection({
    required String sectionKey,
    required String title,
    required String subtitle,
    required Widget child,
  }) {
    final expanded = _expandedSections[sectionKey] ?? false;
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing16),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(DS.spacing12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            InkWell(
              borderRadius: DS.borderRadius12,
              onTap: () {
                setState(() {
                  _expandedSections[sectionKey] = !expanded;
                });
              },
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: DS.spacing4),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            title,
                            style: TextStyle(
                              fontSize: DS.fontSizeLg,
                              fontWeight: DS.fontWeightBold,
                              color: DS.textPrimary,
                            ),
                          ),
                          const SizedBox(height: DS.spacing4),
                          Text(
                            subtitle,
                            style: TextStyle(
                              fontSize: DS.fontSizeSm,
                              color: DS.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Icon(
                      expanded ? Icons.expand_less : Icons.expand_more,
                      color: DS.textSecondary,
                    ),
                  ],
                ),
              ),
            ),
            if (expanded) ...[
              const SizedBox(height: DS.spacing12),
              child,
            ],
          ],
        ),
      ),
    );
  }

  List<String> _buildReadableSummary({
    required AppLocalizations l10n,
    required List<Map<String, dynamic>> goals,
    required List<Map<String, dynamic>> preferences,
    required List<Map<String, dynamic>> patterns,
    required List<Map<String, dynamic>> fragments,
  }) {
    final lines = <String>[];
    final activeGoal = goals.cast<Map<String, dynamic>?>().firstWhere(
          (item) => item?['status']?.toString() != 'completed',
          orElse: () => goals.isEmpty ? null : goals.first,
        );
    if (activeGoal != null) {
      final goalTitle = activeGoal['title']?.toString() ??
          activeGoal['value']?.toString() ??
          '';
      if (goalTitle.isNotEmpty) {
        lines.add(normalizeRichText(l10n.personaActiveGoal(goalTitle)));
      }
    }

    String? learningStyle;
    String? responseDepth;
    for (final item in preferences) {
      final key = item['key']?.toString();
      if (key == 'learning_style') {
        learningStyle = item['value']?.toString();
      }
      if (key == 'depth_preference') {
        responseDepth = item['value']?.toString();
      }
    }
    if (learningStyle != null || responseDepth != null) {
      lines.add(
        normalizeRichText(
          l10n.personaLearningPreference(
            learningStyle ?? 'unspecified',
            responseDepth ?? 'adaptive',
          ),
        ),
      );
    }

    final firstPattern = patterns.isNotEmpty
        ? (patterns.first['name']?.toString() ??
            patterns.first['value']?.toString() ??
            patterns.first['content']?.toString())
        : null;
    if (firstPattern != null && firstPattern.isNotEmpty) {
      lines.add(normalizeRichText(l10n.personaObservedPattern(firstPattern)));
    }

    if (fragments.isNotEmpty) {
      lines.add(
        normalizeRichText(l10n.personaCognitiveClueCount(fragments.length)),
      );
    }

    if (lines.isEmpty) {
      lines.add(
        normalizeRichText(l10n.personaProfileSparse),
      );
    }
    return lines;
  }

  Widget _buildReadableSummaryCard(
      AppLocalizations l10n, List<String> summaryLines) {
    final summaryMarkdown = summaryLines
        .map((line) => '- ${normalizeRichText(line).trim()}')
        .join('\n');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
           l10n.personaSimplifiedUnderstanding,
          style: TextStyle(
            fontWeight: DS.fontWeightSemibold,
            color: DS.textPrimary,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        SparkleMarkdown(
          content: summaryMarkdown,
          textColor: DS.textSecondary,
          codeBackgroundColor: DS.surfaceSecondary,
          linkColor: DS.brandPrimary,
          fontSize: DS.fontSizeBase,
          contentRole: SparkleMarkdownRole.knowledgeSummary,
        ),
      ],
    );
  }

  Widget _buildAsyncSection<T>(
    WidgetRef ref,
    BuildContext context, {
    required String title,
    required AsyncValue<T> asyncValue,
    required List<Widget> Function(T data) builder,
    required VoidCallback onRetry,
  }) {
    final l10n = context.l10n;
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing16),
      child: GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        padding: const EdgeInsets.all(DS.spacing12),
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
                      color: DS.textSecondary,
                    ),
                  ),
                ),
                IconButton(
                  tooltip: l10n.personaSectionRefresh,
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh_rounded, size: 18),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),
            ...asyncValue.when(
              data: (data) {
                final rows = builder(data);
                if (rows.isEmpty) {
                  return [
                    Text(
                      l10n.personaNoData,
                      style: TextStyle(color: DS.neutral500),
                    ),
                  ];
                }
                return rows;
              },
              loading: () => [
                Row(
                  children: [
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                    const SizedBox(width: DS.spacing8),
                     Text(
                       l10n.personaSectionLoading,
                       style: TextStyle(color: DS.neutral500),
                    ),
                  ],
                ),
              ],
              error: (error, stack) => [
                 Text(
                   l10n.personaLoadFailedError(_friendlyError(error)),
                   style: TextStyle(color: DS.error),
                 ),
                 const SizedBox(height: DS.spacing8),
                 SparkleButton.ghost(
                   onPressed: onRetry,
                   label: l10n.retry,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildContextSummaryRows(
    AppLocalizations l10n,
    Map<String, dynamic> contextData,
  ) {
    final preferences =
        contextData['preferences'] as Map<String, dynamic>? ?? {};
    final preferenceVersion = contextData['preference_version'];
    final knowledgeSummary =
        contextData['knowledge_summary'] as Map<String, dynamic>? ?? {};
    final cognitiveSummary =
        contextData['cognitive_summary'] as Map<String, dynamic>? ?? {};

    final rows = <Widget>[
       _metadataRow(
         l10n,
         'Preference Version: ${preferenceVersion ?? 0}',
         <String, dynamic>{
           'level': 'readonly',
           'reason': l10n.personaPreferenceVersionReason,
         },
       ),
    ];

    if (preferences.isNotEmpty) {
      rows.add(
        _metadataRow(
          l10n,
          'Active Preferences: ${preferences.entries.map((entry) => '${entry.key}=${entry.value}').join(', ')}',
           <String, dynamic>{
             'level': 'readonly',
             'reason': l10n.personaActivePreferencesReason,
           },
        ),
      );
    }

    final overallMastery = knowledgeSummary['overall_mastery'];
    final weakSpots =
        (knowledgeSummary['weak_spots'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .where((item) => item.isNotEmpty)
            .toList();
    final activeSubjects =
        (knowledgeSummary['active_learning_subjects'] as List<dynamic>? ??
                const [])
            .map((item) => item.toString())
            .where((item) => item.isNotEmpty)
            .toList();
    rows.add(
      _metadataRow(
        l10n,
        'Knowledge Summary: mastery=${overallMastery ?? '-'}'
        '${weakSpots.isNotEmpty ? ', weak=${weakSpots.join(' / ')}' : ''}'
        '${activeSubjects.isNotEmpty ? ', active=${activeSubjects.join(' / ')}' : ''}',
        <String, dynamic>{
          'level': 'readonly',
          'reason': l10n.personaKnowledgeSummaryReason,
        },
      ),
    );

    final dominantPattern =
        cognitiveSummary['dominant_pattern_type']?.toString();
    final activePatterns =
        (cognitiveSummary['active_patterns'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .where((item) => item.isNotEmpty)
            .toList();
    final riskSignals =
        (cognitiveSummary['risk_signals'] as List<dynamic>? ?? const [])
            .map((item) => item.toString())
            .where((item) => item.isNotEmpty)
            .toList();
    rows.add(
      _metadataRow(
        l10n,
        'Cognitive Summary: dominant=${dominantPattern ?? '-'}'
        '${activePatterns.isNotEmpty ? ', patterns=${activePatterns.join(' / ')}' : ''}'
        '${riskSignals.isNotEmpty ? ', risks=${riskSignals.join(' / ')}' : ''}',
        <String, dynamic>{
          'level': 'readonly',
          'reason': l10n.personaCognitiveSummaryReason,
        },
      ),
    );

    return rows;
  }

  Widget _inferredPreferenceRow(
    WidgetRef ref,
    BuildContext context,
    AppLocalizations l10n,
    Map<String, dynamic> item,
  ) {
    final key = item['key']?.toString() ?? 'unknown';
    final label = item['label']?.toString() ?? key;
    final value = item['value'];
    final explanation = item['explanation']?.toString() ?? '';
    final source = item['source']?.toString() ?? 'system';
    final sourceLabel = item['source_label']?.toString() ?? source;
    final adjustable = item['adjustable'] == true;
    final overridden = item['overridden'] == true;
    final metadata = <String, dynamic>{
      'level': adjustable ? 'editable' : 'readonly',
      'reason': explanation.isNotEmpty ? explanation : l10n.personaInferredDefaultReason,
      'confidence': null,
    };
    final actions = <Widget>[
      SparkleButton.ghost(
        onPressed: () => context.push(
          MemoryRoutes.detail,
          extra: MemoryDetailArgs.preferenceKey(key),
        ),
         label: l10n.personaViewRecord,
      ),
      if (adjustable)
        SparkleButton.ghost(
          onPressed: () => _openOverrideInferredDialog(
            ref,
            context,
            key,
            value,
          ),
           label: overridden ? l10n.personaUpdate : l10n.personaAdjust,
        ),
      if (overridden)
        SparkleButton.ghost(
          onPressed: () => _resetOverride(ref, context, key),
           label: l10n.commonReset,
        ),
    ];
    return KeyedSubtree(
      key: _itemKeyFor(key),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _metadataRow(
            l10n,
            '$label: ${_formatValue(value)}(${overridden ? l10n.personaManualOverride : sourceLabel})',
            metadata,
          ),
          Padding(
            padding: const EdgeInsets.only(
              left: DS.spacing16,
              bottom: DS.spacing8,
            ),
            child: Align(
              alignment: Alignment.centerRight,
              child: Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                alignment: WrapAlignment.end,
                children: actions,
              ),
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
      await _openOverrideInferredDialog(
        ref,
        context,
        key,
        matchedItem['value'],
      );
    });
  }

  Widget _policyRow(AppLocalizations l10n, Map<String, dynamic> item) {
    final profileLabel = item['profile_label']?.toString() ??
        item['profile']?.toString() ??
        l10n.personaPolicy;
    final signal = item['signal_label']?.toString() ??
        item['signal']?.toString() ??
        'policy';
    final effect = item['effect']?.toString() ?? '';
    final sourcePattern = item['source_pattern_label']?.toString() ??
        item['source_pattern']?.toString() ??
        '';
    return _metadataRow(
      l10n,
      '$profileLabel · $signal: $effect',
      <String, dynamic>{
        'level': 'readonly',
        'reason':
            sourcePattern.isNotEmpty ? l10n.personaSourcePattern(sourcePattern) : l10n.personaActivePolicyReason,
        'confidence': null,
      },
    );
  }

  Widget _buildOnboardingBanner(
    BuildContext context,
    AppLocalizations l10n,
    bool completed,
  ) =>
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

  Widget _subSectionList(
    String title,
    List<Widget> items,
    AppLocalizations l10n,
  ) =>
      Padding(
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
    final actions = <Widget>[
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
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _metadataRow(l10n, '$key: ${_formatValue(value)}', meta),
        if (actions.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(
              left: DS.spacing16,
              bottom: DS.spacing8,
            ),
            child: Align(
              alignment: Alignment.centerRight,
              child: Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                alignment: WrapAlignment.end,
                children: actions,
              ),
            ),
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
    final title = item['title']?.toString() ??
        item['value']?.toString() ??
        l10n.personaGoals;
    final status = item['status']?.toString() ?? 'unknown';
    final meta = item['metadata'] as Map<String, dynamic>? ?? {};
    final goalId = item['id']?.toString();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _metadataRow(l10n, '$title ($status)', meta),
        if (goalId != null)
          Padding(
            padding: const EdgeInsets.only(
              left: DS.spacing16,
              bottom: DS.spacing8,
            ),
            child: Align(
              alignment: Alignment.centerRight,
              child: SparkleButton.ghost(
                onPressed: () => _openEditGoalDialog(
                  ref,
                  context,
                  l10n,
                  goalId,
                  title,
                  status,
                ),
                label: l10n.personaEdit,
              ),
            ),
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

  Widget _metadataRow(
    AppLocalizations l10n,
    String label,
    Map<String, dynamic> metadata,
  ) {
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
              Container(
                width: 5,
                height: 5,
                margin: const EdgeInsets.only(top: 8, right: 8),
                decoration: BoxDecoration(
                  color: DS.textPrimary,
                  shape: BoxShape.circle,
                ),
              ),
              Expanded(
                child: Text(label, style: TextStyle(color: DS.textPrimary)),
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
              try {
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
              } catch (error) {
                if (context.mounted) {
                  AppFeedback.error(context, l10n.personaCorrectionSubmitFailed(_friendlyError(error)));
                }
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
    final helperText = _preferenceInputHint(prefKey);
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
              keyboardType: _preferenceKeyboardType(prefKey),
              decoration: InputDecoration(
                labelText: l10n.personaNewPreferenceValue,
                helperText: helperText,
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
              final nextValue = controller.text.trim();
              if (nextValue.isEmpty) {
                if (context.mounted) {
                  AppFeedback.info(context, l10n.personaPleaseEnterValue);
                }
                return;
              }
              final parsedValue = _parsePreferenceInput(prefKey, nextValue);
              if (parsedValue == null) {
                if (context.mounted) {
                  AppFeedback.info(
                    context,
                    _invalidPreferenceMessage(prefKey),
                  );
                }
                return;
              }
              try {
                await repo.updateTransparentPreference(
                  prefKey: prefKey,
                  value: parsedValue,
                );
                ref.invalidate(transparentProfileProvider);
                ref.invalidate(profileContextProvider);
                ref.invalidate(inferredPreferencesProvider);
                ref.invalidate(activePoliciesProvider);
                if (context.mounted) {
                  AppFeedback.success(context, I18nService.instance.isChinese ? '偏好已更新' : 'Preference updated');
                  Navigator.of(context).pop();
                }
              } catch (error) {
                if (context.mounted) {
                  AppFeedback.error(context, I18nService.instance.isChinese ? '偏好更新失败：${_friendlyError(error)}' : 'Preference update failed: ${_friendlyError(error)}');
                }
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
      try {
        await repo.rollbackTransparentPreference(prefKey);
        ref.invalidate(transparentProfileProvider);
        ref.invalidate(profileContextProvider);
        ref.invalidate(inferredPreferencesProvider);
        ref.invalidate(activePoliciesProvider);
        if (context.mounted) {
          AppFeedback.success(context, I18nService.instance.isChinese ? '已回滚到上一版本' : 'Rolled back to previous version');
        }
      } catch (error) {
        if (context.mounted) {
          AppFeedback.error(context, I18nService.instance.isChinese ? '回滚失败：${_friendlyError(error)}' : 'Rollback failed: ${_friendlyError(error)}');
        }
      }
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
                  DropdownMenuItem(
                    value: 'active',
                    child: Text(l10n.personaStatusActive),
                  ),
                  DropdownMenuItem(
                    value: 'completed',
                    child: Text(l10n.personaStatusCompleted),
                  ),
                  DropdownMenuItem(
                    value: 'paused',
                    child: Text(l10n.personaStatusPaused),
                  ),
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

                // GOAL-009: Confirm high-risk status changes (active → completed,
                // active → cancelled, archived → active). Title-only edits skip
                // confirmation since they're easily reversible.
                final isStatusChange = nextStatus != status;
                final isHighRisk = isStatusChange &&
                    (nextStatus == 'completed' ||
                        nextStatus == 'cancelled' ||
                        nextStatus == 'archived' ||
                        (status == 'archived' && nextStatus == 'active'));

                if (isHighRisk) {
                  final isZh = I18nService.instance.isChinese;
                  final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (dialogCtx) => AlertDialog(
                      title: Text(
                        isZh ? '确认修改目标状态？' : 'Confirm goal status change?',
                      ),
                      content: Text(
                        isZh
                            ? '将"${nextTitle.isNotEmpty ? nextTitle : '此目标'}"的状态从「$status」改为「$nextStatus」。\n\n这会影响相关计划、任务和提醒，且不会自动撤销。'
                            : 'Change status of "${nextTitle.isNotEmpty ? nextTitle : "this goal"}" from "$status" to "$nextStatus".\n\nThis will affect related plans, tasks and reminders, and cannot be auto-reverted.',
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.of(dialogCtx).pop(false),
                          child: Text(isZh ? '取消' : 'Cancel'),
                        ),
                        FilledButton(
                          onPressed: () => Navigator.of(dialogCtx).pop(true),
                          child: Text(isZh ? '确认修改' : 'Confirm change'),
                        ),
                      ],
                    ),
                  );
                  if (confirmed != true) return;
                }

                try {
                  await repo.updateGoal(
                    goalId: goalId,
                    title: nextTitle,
                    status: nextStatus,
                  );
                  ref.invalidate(transparentProfileProvider);
                  ref.invalidate(profileContextProvider);
                  ref.invalidate(activePoliciesProvider);
                  if (context.mounted) {
                    AppFeedback.success(context, I18nService.instance.isChinese ? '目标已更新' : 'Goal updated');
                    Navigator.of(context).pop();
                  }
                } catch (error) {
                  if (context.mounted) {
                    AppFeedback.error(
                      context,
                      I18nService.instance.isChinese ? '目标更新失败：${_friendlyError(error)}' : 'Goal update failed: ${_friendlyError(error)}',
                    );
                  }
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
        title: Text(context.l10n.personaAdjustInferredPreference),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(key),
            const SizedBox(height: DS.spacing12),
            TextField(
              controller: controller,
              decoration: InputDecoration(
                labelText: context.l10n.personaAdjustInferredPreference,
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
                  AppFeedback.info(
                    context,
                    context.l10n.personaPleaseEnterValue,
                  );
                }
                return;
              }
              try {
                await repo.overrideInferredPreference(
                  key: key,
                  value: nextValue,
                );
                ref.invalidate(transparentProfileProvider);
                ref.invalidate(profileContextProvider);
                ref.invalidate(inferredPreferencesProvider);
                ref.invalidate(activePoliciesProvider);
                if (context.mounted) {
                  AppFeedback.success(context, I18nService.instance.isChinese ? '推断偏好已调整' : 'Inferred preference adjusted');
                  Navigator.of(context).pop();
                }
              } catch (error) {
                if (context.mounted) {
                  AppFeedback.error(context, I18nService.instance.isChinese ? '调整失败：${_friendlyError(error)}' : 'Adjustment failed: ${_friendlyError(error)}');
                }
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
    try {
      await repo.resetInferredOverride(key);
      ref.invalidate(transparentProfileProvider);
      ref.invalidate(profileContextProvider);
      ref.invalidate(inferredPreferencesProvider);
      ref.invalidate(activePoliciesProvider);
      if (context.mounted) {
        AppFeedback.success(context, I18nService.instance.isChinese ? '已恢复系统推断值' : 'Restored system inferred value');
      }
    } catch (error) {
      if (context.mounted) {
        AppFeedback.error(context, I18nService.instance.isChinese ? '恢复失败：${_friendlyError(error)}' : 'Restore failed: ${_friendlyError(error)}');
      }
    }
  }

  Future<void> _refreshPersona(WidgetRef ref) async {
    ref.invalidate(transparentProfileProvider);
    ref.invalidate(profileContextProvider);
    ref.invalidate(inferredPreferencesProvider);
    ref.invalidate(activePoliciesProvider);

    for (final future in <Future<dynamic>>[
      ref.read(transparentProfileProvider.future),
      ref.read(profileContextProvider.future),
      ref.read(inferredPreferencesProvider.future),
      ref.read(activePoliciesProvider.future),
    ]) {
      try {
        await future;
      } catch (_) {
        // Let each section render its own error state.
      }
    }
  }

  String _friendlyError(Object error) {
    final message = error.toString().trim();
    if (message.isEmpty) {
      return I18nService.instance.isChinese ? '未知错误' : 'Unknown error';
    }
    return message.replaceFirst('Exception: ', '');
  }

  TextInputType _preferenceKeyboardType(String prefKey) {
    switch (prefKey) {
      case 'depth_preference':
      case 'curiosity_preference':
        return const TextInputType.numberWithOptions(decimal: true);
      case 'study_time_preference':
        return TextInputType.number;
      default:
        return TextInputType.text;
    }
  }

  String? _preferenceInputHint(String prefKey) {
    switch (prefKey) {
      case 'depth_preference':
      case 'curiosity_preference':
        return I18nService.instance.isChinese ? '请输入 0.0 到 1.0 之间的数字' : 'Enter a number between 0.0 and 1.0';
      case 'study_time_preference':
        return I18nService.instance.isChinese ? '请输入学习时长（分钟）' : 'Enter study time (minutes)';
      default:
        return null;
    }
  }

  Object? _parsePreferenceInput(String prefKey, String rawValue) {
    switch (prefKey) {
      case 'depth_preference':
      case 'curiosity_preference':
        final value = double.tryParse(rawValue);
        if (value == null || value < 0 || value > 1) {
          return null;
        }
        return value;
      case 'study_time_preference':
        final minutes = int.tryParse(rawValue);
        if (minutes == null || minutes <= 0) {
          return null;
        }
        return minutes;
      default:
        return rawValue;
    }
  }

  String _invalidPreferenceMessage(String prefKey) {
    switch (prefKey) {
      case 'depth_preference':
      case 'curiosity_preference':
        return I18nService.instance.isChinese ? '请输入 0.0 到 1.0 之间的数字' : 'Enter a number between 0.0 and 1.0';
      case 'study_time_preference':
        return I18nService.instance.isChinese ? '请输入大于 0 的分钟数' : 'Enter minutes greater than 0';
      default:
        return I18nService.instance.isChinese ? '请输入有效的偏好值' : 'Enter a valid preference value';
    }
  }
}
