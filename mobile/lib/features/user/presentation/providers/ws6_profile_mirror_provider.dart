import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/client_observability_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/user/presentation/models/ws6_profile_mirror_models.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/ws6_flags.dart';

typedef Ws6BindingTelemetryRecorder = Future<void> Function({
  required String outcome,
  Map<String, dynamic>? metadata,
});

final ws6ProfileMirrorAdapterProvider = Provider<Ws6ProfileMirrorAdapter>(
  (ref) => const Ws6ProfileMirrorAdapter(),
);

final ws6BindingTelemetryRecorderProvider =
    Provider<Ws6BindingTelemetryRecorder>((ref) {
  return ({required String outcome, Map<String, dynamic>? metadata}) {
    return ClientObservabilityService.instance.recordEvent(
      eventType: 'profile_transparency_binding',
      category: 'profile_surface',
      route: '/user/profile/transparent',
      status: outcome == 'binding_failure' ? 'error' : 'ok',
      severity: outcome == 'binding_failure' ? 'warning' : 'info',
      metadata: <String, dynamic>{
        'outcome': outcome,
        ...?metadata,
      },
    );
  };
});

final ws6TransparentProfileViewProvider =
    FutureProvider<Ws6TransparentProfileViewModel>((ref) async {
  final recordBinding = ref.read(ws6BindingTelemetryRecorderProvider);
  if (!kWs6ProfileSurfaceEnabled) {
    unawaited(
      recordBinding(
        outcome: 'gated',
        metadata: const <String, dynamic>{
          'source': 'flag_disabled',
        },
      ),
    );
    return Ws6TransparentProfileViewModel.inert(
      bindingNotes: const <String>[
        'canonical transparency surface gated',
        'provisional binding: profileContextProvider',
      ],
    );
  }

  try {
    final profileContext = await ref.watch(profileContextProvider.future);
    final embeddedTransparency = _asMap(
      profileContext['user_insight_transparency'],
    );
    final transparentProfile = embeddedTransparency.isNotEmpty
        ? embeddedTransparency
        : await ref.watch(profileInsightsProvider.future);
    final source = embeddedTransparency.isNotEmpty
        ? 'user_insight_transparency'
        : 'profile_insights';
    final adapter = ref.watch(ws6ProfileMirrorAdapterProvider);
    final view = adapter.build(
      transparentProfile: transparentProfile,
      profileContext: profileContext,
    );
    unawaited(
      recordBinding(
        outcome: embeddedTransparency.isNotEmpty
            ? 'canonical_embedded'
            : 'canonical_fallback',
        metadata: <String, dynamic>{
          'source': source,
          'binding_notes': view.bindingNotes,
        },
      ),
    );
    return view;
  } catch (_) {
    try {
      final transparentProfile =
          await ref.watch(transparentProfileProvider.future);
      final profileContext = await ref.watch(profileContextProvider.future);
      final adapter = ref.watch(ws6ProfileMirrorAdapterProvider);
      unawaited(
        recordBinding(
          outcome: 'deprecated_fallback',
          metadata: const <String, dynamic>{
            'source': 'transparentProfileProvider',
          },
        ),
      );
      return adapter
          .build(
        transparentProfile: transparentProfile,
        profileContext: profileContext,
      )
          .copyWithBindingNotes(
        const <String>[
          'data source: transparentProfileProvider (deprecated fallback)',
          'data source: profileContextProvider',
        ],
      );
    } catch (_) {
      unawaited(
        recordBinding(
          outcome: 'binding_failure',
          metadata: const <String, dynamic>{
            'source': 'canonical_and_legacy_failed',
          },
        ),
      );
      return Ws6TransparentProfileViewModel.inert(
        summary: 'WS6 profile surface could not bind to live data yet.',
        bindingNotes: const <String>[
          'canonical transparency fetch failed',
          'legacy transparentProfileProvider fallback failed',
        ],
      );
    }
  }
});

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }
  if (value is Map) {
    return value.map((key, dynamic item) => MapEntry(key.toString(), item));
  }
  return <String, dynamic>{};
}

class Ws6ProfileMirrorAdapter {
  const Ws6ProfileMirrorAdapter();

  Ws6TransparentProfileViewModel build({
    required Map<String, dynamic> transparentProfile,
    required Map<String, dynamic> profileContext,
    Map<String, dynamic>? relationshipState,
    bool allowSensitiveMediation = false,
  }) {
    final rawItems = _extractClaimLikeItems(transparentProfile);
    final synthesizedItems = rawItems.isEmpty
        ? _synthesizeItemsFromLegacyLayers(transparentProfile)
        : rawItems;
    final computedHiddenCount = _hiddenItemCount(transparentProfile) > 0
        ? _hiddenItemCount(transparentProfile)
        : synthesizedItems
            .where(
              (item) =>
                  _parseVisibility(
                    item['projection_policy']?.toString(),
                    allowSensitiveMediation: allowSensitiveMediation,
                  ) ==
                  Ws6ProfileVisibility.hidden,
            )
            .length;
    final visibleItems = <Ws6TransparentProfileItemModel>[];
    final mediatedItems = <Ws6TransparentProfileItemModel>[];
    final revertActions = <Ws6ProfileRevertActionModel>[];

    for (final item in synthesizedItems) {
      final visibility = _parseVisibility(
        item['projection_policy']?.toString(),
        allowSensitiveMediation: allowSensitiveMediation,
      );
      final mappedItem = _buildProfileItem(item, visibility);
      switch (visibility) {
        case Ws6ProfileVisibility.visible:
          visibleItems.add(mappedItem);
        case Ws6ProfileVisibility.mediated:
          mediatedItems.add(mappedItem);
        case Ws6ProfileVisibility.hidden:
        // Hidden items stay out of the rendered lists by design.
      }

      if (mappedItem.canRevert) {
        revertActions.add(
          Ws6ProfileRevertActionModel(
            key: mappedItem.key,
            label: mappedItem.label,
            currentSummary: mappedItem.summary,
            suggestedSummary:
                item['suggested_summary']?.toString() ?? mappedItem.summary,
            reason: item['revert_reason']?.toString() ??
                'dialogue-mediated revert required',
            projectionPolicy:
                item['projection_policy']?.toString() ?? 'open_discussable',
            requiresDialogue: visibility != Ws6ProfileVisibility.visible,
          ),
        );
      }
    }

    final mirrorBar = _buildMirrorBar(
      transparentProfile: transparentProfile,
      profileContext: profileContext,
      relationshipState: relationshipState,
      allowSensitiveMediation: allowSensitiveMediation,
    );
    final summary = _buildSummary(
      transparentProfile: transparentProfile,
      visibleItems: visibleItems,
      mediatedItems: mediatedItems,
      hiddenItemCount: computedHiddenCount,
      relationshipState: relationshipState,
    );

    return Ws6TransparentProfileViewModel(
      enabled: true,
      summary: summary,
      mirrorBar: mirrorBar,
      visibleItems: visibleItems,
      mediatedItems: mediatedItems,
      hiddenItemCount: computedHiddenCount,
      revertActions: revertActions,
      recentCorrections: _buildRecentCorrections(profileContext),
      calibrationPosture:
          _asMap(transparentProfile['calibration'])['calibration_posture']
                  ?.toString() ??
              '',
      unknowns: [
        for (final item in _asList(transparentProfile['unknowns']))
          _asMap(item)['description']?.toString() ?? '',
      ].where((item) => item.isNotEmpty).toList(growable: false),
      bindingNotes: List<String>.unmodifiable([
        if (transparentProfile.containsKey('claims'))
          'data source: user_insight_transparency / profileInsightsProvider',
        if (!transparentProfile.containsKey('claims'))
          'data source: transparentProfileProvider (deprecated fallback)',
        'data source: profileContextProvider',
        if (relationshipState != null)
          'data source: relationship_state adapter',
      ]),
    );
  }

  List<Ws6ProfileCorrectionHistoryItemModel> _buildRecentCorrections(
    Map<String, dynamic> profileContext,
  ) {
    return [
      for (final raw in _asList(profileContext['recent_corrections']))
        if (_asMap(raw).isNotEmpty) _buildCorrectionHistoryItem(_asMap(raw)),
    ];
  }

  Ws6ProfileCorrectionHistoryItemModel _buildCorrectionHistoryItem(
    Map<String, dynamic> item,
  ) {
    final targetId = item['target_id']?.toString() ?? '';
    final fieldName = item['field_name']?.toString() ?? targetId;
    final action = item['action']?.toString() ?? '';
    final summary = item['summary']?.toString() ?? action;
    final createdAt = item['created_at']?.toString() ?? '';
    return Ws6ProfileCorrectionHistoryItemModel(
      id: item['id']?.toString() ?? targetId,
      targetId: targetId,
      fieldName: fieldName.isEmpty ? targetId : fieldName,
      action: action,
      summary: summary,
      createdAtLabel: createdAt.split('T').first,
      canUndo: item['can_undo'] == true && targetId.isNotEmpty,
    );
  }

  Ws6MirrorBarModel _buildMirrorBar({
    required Map<String, dynamic> transparentProfile,
    required Map<String, dynamic> profileContext,
    required bool allowSensitiveMediation,
    Map<String, dynamic>? relationshipState,
  }) {
    final currentProfile = _asMap(transparentProfile['current_profile']);
    final layer1 = _asMap(transparentProfile['layer_1']);
    final layer2 = _asMap(transparentProfile['layer_2']);
    final layer3 = _asMap(transparentProfile['layer_3']);
    final canonicalState = _asMap(profileContext['user_insight_state']);
    final currentState = _asMap(profileContext['current_state']).isNotEmpty
        ? _asMap(profileContext['current_state'])
        : _asMap(currentProfile['current_state']).isNotEmpty
            ? _asMap(currentProfile['current_state'])
            : _asMap(canonicalState['current_state']);
    final readiness = _asMap(profileContext['readiness']).isNotEmpty
        ? _asMap(profileContext['readiness'])
        : _asMap(canonicalState['readiness']);
    final knowledgeSummary = _asMap(profileContext['knowledge_summary']);
    final cognitiveSummary = _asMap(profileContext['cognitive_summary']);
    final relationship = relationshipState ?? const <String, dynamic>{};

    final focusValue = _dimensionValue(
      [currentState['focus'], currentState['active_goal'], layer1['goals']],
      fallback: _dimensionValue(layer1['goals'], fallback: 0.4),
    );
    final energyValue = _dimensionValue(
      [
        currentState['energy'],
        readiness['energy'],
        if (_asMap(layer2['persona']).isNotEmpty)
          _asMap(layer2['persona'])['capabilities'],
      ],
      fallback: _dimensionValue([readiness['energy']], fallback: 0.45),
    );
    final commitmentValue = _dimensionValue(
      [
        currentState['commitment'],
        knowledgeSummary['active_learning_subjects'],
        layer1['preferences']
      ],
      fallback: _dimensionValue(knowledgeSummary['active_learning_subjects'],
          fallback: 0.35),
    );
    final memoryValue = _dimensionValue(
      [
        knowledgeSummary['overall_mastery'],
        cognitiveSummary['active_patterns'],
        layer3['patterns']
      ],
      fallback: _dimensionValue(layer3['patterns'], fallback: 0.3),
    );

    final presenceFromRelationship =
        _numericFrom(relationship['relationship_maturity']);
    final presenceFallback = _clamp01(
        (focusValue + energyValue + commitmentValue + memoryValue) / 4);
    final presenceValue = presenceFromRelationship ?? presenceFallback;
    final presenceLabel = _presenceLabel(presenceValue);
    final zh = I18nService.instance.isChinese;

    return Ws6MirrorBarModel(
      enabled: true,
      presenceLabel: presenceLabel,
      presenceValue: presenceValue,
      dimensions: [
        Ws6MirrorDimensionModel(
          key: 'focus',
          label: 'Focus',
          value: focusValue,
          subtitle: _dimensionSubtitle(
            currentState['focus'],
            layer1['goals'],
            fallback: zh ? '当前关注点和目标聚焦' : 'Current focus and goal alignment',
          ),
          sourceLabel: _sourceLabel(
            [
              'profileContext.current_state.focus',
              'transparentProfile.layer_1.goals'
            ],
          ),
          visibility: Ws6ProfileVisibility.visible,
          canEditDirectly: _looksEditable(layer1['goals']),
          canRevert: true,
        ),
        Ws6MirrorDimensionModel(
          key: 'energy',
          label: 'Energy',
          value: energyValue,
          subtitle: _dimensionSubtitle(
            currentState['energy'],
            readiness['energy'],
            fallback: zh
                ? '系统对当前能量状态的保守估计'
                : 'Conservative estimate of current energy',
          ),
          sourceLabel: _sourceLabel(
            [
              'profileContext.current_state.energy',
              'profileContext.readiness.energy'
            ],
          ),
          visibility: allowSensitiveMediation
              ? Ws6ProfileVisibility.visible
              : Ws6ProfileVisibility.mediated,
          canEditDirectly: false,
          canRevert: true,
        ),
        Ws6MirrorDimensionModel(
          key: 'commitment',
          label: 'Commitment',
          value: commitmentValue,
          subtitle: _dimensionSubtitle(
            currentState['commitment'],
            knowledgeSummary['active_learning_subjects'],
            fallback: zh
                ? '当前承诺与任务执行节奏'
                : 'Current commitments and task execution rhythm',
          ),
          sourceLabel: _sourceLabel(
            [
              'profileContext.knowledge_summary.active_learning_subjects',
              'transparentProfile.layer_1.preferences'
            ],
          ),
          visibility: Ws6ProfileVisibility.visible,
          canEditDirectly: _looksEditable(layer1['preferences']),
          canRevert: true,
        ),
        Ws6MirrorDimensionModel(
          key: 'memory',
          label: 'Memory',
          value: memoryValue,
          subtitle: _dimensionSubtitle(
            knowledgeSummary['overall_mastery'],
            cognitiveSummary['active_patterns'],
            fallback: zh
                ? '最近记忆与模式的保守投影'
                : 'Conservative projection from recent memory and patterns',
          ),
          sourceLabel: _sourceLabel(
            [
              'profileContext.knowledge_summary.overall_mastery',
              'profileContext.cognitive_summary.active_patterns'
            ],
          ),
          visibility: Ws6ProfileVisibility.visible,
          canEditDirectly: false,
          canRevert: false,
        ),
      ],
      bindingNotes: [
        if (transparentProfile.containsKey('claims'))
          'Focus: transparency claims + profileContext.current_state',
        if (!transparentProfile.containsKey('claims'))
          'Focus: transparentProfile.layer_1 + profileContext.current_state',
        'Energy: profileContext.readiness + current_state',
        'Commitment: profileContext.knowledge_summary + layer_1',
        'Memory: profileContext.knowledge_summary + cognitive_summary',
      ],
    );
  }

  List<Map<String, dynamic>> _extractClaimLikeItems(
      Map<String, dynamic> transparentProfile) {
    final items = <Map<String, dynamic>>[];
    final rawItems =
        transparentProfile['items'] ?? transparentProfile['claims'];
    if (rawItems is List) {
      for (final item in rawItems) {
        final map = _asMap(item);
        if (map.isNotEmpty) {
          items.add(_normalizeClaimLikeItem(map));
        }
      }
    }
    return items;
  }

  Map<String, dynamic> _normalizeClaimLikeItem(Map<String, dynamic> item) {
    final controls = _asList(item['controls'])
        .map((dynamic value) => value.toString())
        .toList(growable: false);
    final hasClaimShape = item.containsKey('id') && item.containsKey('value');
    if (!hasClaimShape) {
      return item;
    }
    return {
      'key': item['id']?.toString() ?? item['label']?.toString() ?? 'claim',
      'label': item['label']?.toString() ?? item['id']?.toString() ?? 'Claim',
      'summary': _stringifyValue(item['value']),
      'projection_policy': controls.contains('exam_mode_only')
          ? 'open_editable'
          : 'open_discussable',
      'visibility': 'visible',
      'can_edit_directly': controls.contains('exam_mode_only'),
      'can_revert':
          controls.contains('wrong') || controls.contains('used_to_be_true'),
      'supports_exam_mode_only': controls.contains('exam_mode_only'),
      'evidence_summary':
          '${item['family'] ?? 'signal'} · freshness ${item['freshness'] ?? 'unknown'} · confidence ${item['confidence'] ?? 'n/a'}',
      'revert_reason':
          item['explanation']?.toString() ?? 'user-reported correction lane',
      'suggested_summary': _stringifyValue(item['value']),
    };
  }

  List<Map<String, dynamic>> _synthesizeItemsFromLegacyLayers(
      Map<String, dynamic> transparentProfile) {
    final layer1 = _asMap(transparentProfile['layer_1']);
    final layer2 = _asMap(transparentProfile['layer_2']);
    final layer3 = _asMap(transparentProfile['layer_3']);
    final items = <Map<String, dynamic>>[];

    void addLegacyItem({
      required String key,
      required String label,
      required dynamic value,
      required String projectionPolicy,
      required String visibility,
      required bool canEditDirectly,
      required bool canRevert,
      String? summary,
      String? suggestedSummary,
      String? revertReason,
    }) {
      items.add({
        'key': key,
        'label': label,
        'summary': summary ?? _stringifyValue(value),
        'projection_policy': projectionPolicy,
        'visibility': visibility,
        'can_edit_directly': canEditDirectly,
        'can_revert': canRevert,
        if (suggestedSummary != null) 'suggested_summary': suggestedSummary,
        if (revertReason != null) 'revert_reason': revertReason,
      });
    }

    for (final goal in _asList(layer1['goals'])) {
      addLegacyItem(
        key: 'goal:${goal.hashCode}',
        label: _displayLabel(goal, fallback: 'Goal'),
        value: goal,
        projectionPolicy: 'open_editable',
        visibility: 'visible',
        canEditDirectly: true,
        canRevert: true,
      );
    }
    for (final preference in _asList(layer1['preferences'])) {
      addLegacyItem(
        key: 'preference:${preference.hashCode}',
        label: _displayLabel(preference, fallback: 'Preference'),
        value: preference,
        projectionPolicy: 'open_discussable',
        visibility: 'visible',
        canEditDirectly: true,
        canRevert: true,
      );
    }
    final persona = _asMap(layer2['persona']);
    final capabilities = _asMap(persona['capabilities']);
    for (final entry in capabilities.entries) {
      addLegacyItem(
        key: 'capability:${entry.key}',
        label: entry.key,
        value: entry.value,
        projectionPolicy: 'sensitive_mediated',
        visibility: 'mediated',
        canEditDirectly: false,
        canRevert: true,
      );
    }
    for (final pattern in _asList(layer3['patterns'])) {
      addLegacyItem(
        key: 'pattern:${pattern.hashCode}',
        label: _displayLabel(pattern, fallback: 'Pattern'),
        value: pattern,
        projectionPolicy: 'open_discussable',
        visibility: 'visible',
        canEditDirectly: false,
        canRevert: false,
      );
    }
    for (final fragment in _asList(layer3['fragments'])) {
      addLegacyItem(
        key: 'fragment:${fragment.hashCode}',
        label: _displayLabel(fragment, fallback: 'Fragment'),
        value: fragment,
        projectionPolicy: 'internal',
        visibility: 'hidden',
        canEditDirectly: false,
        canRevert: false,
      );
    }
    return items;
  }

  Ws6TransparentProfileItemModel _buildProfileItem(
    Map<String, dynamic> item,
    Ws6ProfileVisibility visibility,
  ) {
    final policy = item['projection_policy']?.toString() ?? 'open_discussable';
    final label =
        item['label']?.toString() ?? item['key']?.toString() ?? 'Profile item';
    final summary =
        item['summary']?.toString() ?? item['content']?.toString() ?? label;
    final canEditDirectly = item['can_edit_directly'] == true;
    final canRevert = item['can_revert'] != false &&
        visibility != Ws6ProfileVisibility.hidden;
    final evidenceSummary = item['evidence_summary']?.toString() ??
        item['evidence_refs']?.toString() ??
        'provisional binding';

    return Ws6TransparentProfileItemModel(
      key: item['key']?.toString() ?? label,
      label: label,
      summary: summary,
      projectionPolicy: policy,
      visibility: visibility,
      canEditDirectly: canEditDirectly,
      canRevert: canRevert,
      evidenceSummary: evidenceSummary,
      supportsExamModeOnly: item['supports_exam_mode_only'] == true,
    );
  }

  Ws6ProfileVisibility _parseVisibility(
    String? projectionPolicy, {
    required bool allowSensitiveMediation,
  }) {
    switch ((projectionPolicy ?? '').toLowerCase()) {
      case 'internal':
        return Ws6ProfileVisibility.hidden;
      case 'sensitive_mediated':
        return allowSensitiveMediation
            ? Ws6ProfileVisibility.visible
            : Ws6ProfileVisibility.mediated;
      case 'open_editable':
      case 'open_discussable':
      default:
        return Ws6ProfileVisibility.visible;
    }
  }

  String _buildSummary({
    required Map<String, dynamic> transparentProfile,
    required List<Ws6TransparentProfileItemModel> visibleItems,
    required List<Ws6TransparentProfileItemModel> mediatedItems,
    required int hiddenItemCount,
    Map<String, dynamic>? relationshipState,
  }) {
    final explicitSummary = transparentProfile['summary']?.toString().trim();
    if (explicitSummary != null && explicitSummary.isNotEmpty) {
      return explicitSummary;
    }
    final zh = I18nService.instance.isChinese;
    final lead = visibleItems.isNotEmpty
        ? visibleItems.first.label
        : (zh ? '你的画像' : 'your profile');
    final mediatedCount = mediatedItems.length;
    final relationshipPart = relationshipState != null
        ? (zh
            ? '协作成熟度约 ${_clamp01(_numericFrom(relationshipState['relationship_maturity']) ?? 0.0) * 100}%'
            : 'collaboration maturity about ${_clamp01(_numericFrom(relationshipState['relationship_maturity']) ?? 0.0) * 100}%')
        : (zh ? '协作成熟度暂未接入' : 'collaboration maturity is not connected yet');
    return zh
        ? '当前透明画像以「$lead」为主，'
            '可见条目 ${visibleItems.length} 条，中介条目 $mediatedCount 条，'
            '隐藏条目 $hiddenItemCount 条。$relationshipPart。'
        : 'Your transparent profile is currently led by "$lead", '
            'with ${visibleItems.length} visible items, $mediatedCount mediated items, '
            'and $hiddenItemCount hidden items. $relationshipPart.';
  }

  List<dynamic> _asList(dynamic value) {
    if (value is List) {
      return value;
    }
    return const <dynamic>[];
  }

  int _hiddenItemCount(Map<String, dynamic> transparentProfile) {
    final value = transparentProfile['hidden_item_count'] ??
        transparentProfile['hidden_count'];
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    return 0;
  }

  double _dimensionValue(dynamic sources, {double fallback = 0.0}) {
    final normalizedSources = sources is List ? sources : <dynamic>[sources];
    for (final source in normalizedSources) {
      final value = _numericFrom(source);
      if (value != null) {
        return value;
      }
      if (source is Iterable) {
        return _clamp01(source.length / 5.0);
      }
      if (source is Map) {
        return _clamp01(source.length / 6.0);
      }
    }
    return _clamp01(fallback);
  }

  double? _numericFrom(dynamic value) {
    if (value is num) {
      final raw = value.toDouble();
      if (raw <= 1.0) {
        return _clamp01(raw);
      }
      return _clamp01(raw / 100.0);
    }
    if (value is bool) {
      return value ? 1.0 : 0.0;
    }
    if (value is String) {
      final parsed = double.tryParse(value);
      if (parsed != null) {
        return parsed <= 1.0 ? _clamp01(parsed) : _clamp01(parsed / 100.0);
      }
    }
    if (value is Iterable) {
      return _clamp01(value.length / 5.0);
    }
    if (value is Map) {
      return _clamp01(value.length / 6.0);
    }
    return null;
  }

  double _clamp01(double value) => value.clamp(0.0, 1.0);

  String _dimensionSubtitle(dynamic primary, dynamic secondary,
      {required String fallback}) {
    final primaryText = _stringifyValue(primary);
    final secondaryText = _stringifyValue(secondary);
    if (primaryText.isNotEmpty) {
      return primaryText;
    }
    if (secondaryText.isNotEmpty) {
      return secondaryText;
    }
    return fallback;
  }

  String _stringifyValue(dynamic value) {
    if (value == null) {
      return '';
    }
    if (value is String) {
      return value.trim();
    }
    if (value is num || value is bool) {
      return value.toString();
    }
    if (value is Iterable) {
      return value
          .map(_stringifyValue)
          .where((item) => item.isNotEmpty)
          .join(' · ');
    }
    if (value is Map) {
      final text = value.values
          .map(_stringifyValue)
          .where((item) => item.isNotEmpty)
          .join(' · ');
      return text.isNotEmpty ? text : value.keys.join(' · ');
    }
    return value.toString();
  }

  bool _looksEditable(dynamic value) {
    if (value is Map) {
      return value.isNotEmpty;
    }
    if (value is Iterable) {
      return value.isNotEmpty;
    }
    return value != null && value.toString().trim().isNotEmpty;
  }

  String _sourceLabel(List<String> sources) => sources.join(' · ');

  String _presenceLabel(double value) {
    if (value >= 0.7) {
      return 'active';
    }
    if (value >= 0.35) {
      return 'ambient';
    }
    return 'meta_surface';
  }

  String _displayLabel(dynamic value, {required String fallback}) {
    if (value is Map) {
      final label = value['label'] ?? value['title'] ?? value['name'];
      if (label is String && label.trim().isNotEmpty) {
        return label.trim();
      }
    }
    final text = _stringifyValue(value);
    return text.isNotEmpty ? text : fallback;
  }
}
