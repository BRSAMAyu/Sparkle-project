import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/models/ws6_profile_mirror_models.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/providers/ws6_profile_mirror_provider.dart';
import 'package:sparkle/features/user/presentation/widgets/mirror_bar.dart';

void main() {
  testWidgets('mirror bar renders four dimensions and presence label',
      (tester) async {
    const model = Ws6MirrorBarModel(
      enabled: true,
      presenceLabel: 'active',
      presenceValue: 0.86,
      bindingNotes: <String>['Focus binding ready'],
      dimensions: <Ws6MirrorDimensionModel>[
        Ws6MirrorDimensionModel(
          key: 'focus',
          label: 'Focus',
          value: 0.9,
          subtitle: '稳定推进',
          sourceLabel: 'profileContext.current_state.focus',
          visibility: Ws6ProfileVisibility.visible,
          canEditDirectly: true,
          canRevert: true,
        ),
        Ws6MirrorDimensionModel(
          key: 'energy',
          label: 'Energy',
          value: 0.7,
          subtitle: '能量波动',
          sourceLabel: 'profileContext.readiness.energy',
          visibility: Ws6ProfileVisibility.mediated,
          canEditDirectly: false,
          canRevert: true,
        ),
        Ws6MirrorDimensionModel(
          key: 'commitment',
          label: 'Commitment',
          value: 0.8,
          subtitle: '执行承诺',
          sourceLabel:
              'profileContext.knowledge_summary.active_learning_subjects',
          visibility: Ws6ProfileVisibility.visible,
          canEditDirectly: true,
          canRevert: true,
        ),
        Ws6MirrorDimensionModel(
          key: 'memory',
          label: 'Memory',
          value: 0.6,
          subtitle: '记忆回声',
          sourceLabel: 'profileContext.knowledge_summary.overall_mastery',
          visibility: Ws6ProfileVisibility.visible,
          canEditDirectly: false,
          canRevert: false,
        ),
      ],
    );

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: MirrorBar(model: model),
        ),
      ),
    );

    expect(find.textContaining('Aurora Presence'), findsOneWidget);
    expect(find.text('Focus'), findsOneWidget);
    expect(find.text('Energy'), findsOneWidget);
    expect(find.text('Commitment'), findsOneWidget);
    expect(find.text('Memory'), findsOneWidget);
    expect(find.text('Focus binding ready'), findsOneWidget);
  });

  test('adapter builds mirror bar and transparent profile from legacy maps',
      () {
    final adapter = Ws6ProfileMirrorAdapter();
    final result = adapter.build(
      transparentProfile: {
        'layer_1': {
          'goals': ['连续完成计划'],
          'preferences': ['更早开始'],
        },
        'layer_2': {
          'persona': {
            'capabilities': {
              'energy': 0.62,
            },
          },
        },
        'layer_3': {
          'patterns': ['review before sleep'],
          'fragments': ['internal-only fragment'],
        },
      },
      profileContext: {
        'current_state': {
          'focus': '学习推进',
          'energy': 74,
        },
        'readiness': {
          'energy': 68,
        },
        'knowledge_summary': {
          'active_learning_subjects': ['math', 'physics'],
          'overall_mastery': 0.55,
        },
        'cognitive_summary': {
          'active_patterns': ['structured'],
        },
      },
      allowSensitiveMediation: false,
    );

    expect(result.summary, contains('透明画像'));
    expect(result.mirrorBar.dimensions, hasLength(4));
    expect(result.mirrorBar.presenceLabel, isNotEmpty);
    expect(result.visibleItems, isNotEmpty);
    expect(result.mediatedItems, isNotEmpty);
    expect(result.hiddenItemCount, 1);
    expect(result.revertActions, isNotEmpty);
  });

  test('adapter builds transparent profile from canonical transparency payload',
      () {
    final adapter = Ws6ProfileMirrorAdapter();
    final result = adapter.build(
      transparentProfile: {
        'claims': [
          {
            'id': 'achievement_motivation_response',
            'label': 'Achievement motivation response',
            'value': 'progress_praise',
            'family': 'achievement',
            'freshness': 'medium',
            'confidence': 0.82,
            'controls': ['wrong', 'exam_mode_only'],
            'explanation': 'Derived from recent reward response.',
          },
        ],
        'unknowns': [
          {
            'id': 'capacity_hours',
            'description': 'Reliable time-capacity data is still missing.'
          },
        ],
        'calibration': {
          'calibration_posture': 'stable',
        },
        'current_profile': {
          'current_state': {
            'focus': 'exam prep',
          },
        },
      },
      profileContext: {
        'knowledge_summary': {
          'active_learning_subjects': ['physics'],
          'overall_mastery': 0.55,
        },
        'cognitive_summary': {
          'active_patterns': ['structured'],
        },
        'user_insight_state': {
          'current_state': {'focus': 'exam prep'},
          'readiness': {'energy': 0.6},
        },
      },
    );

    expect(result.visibleItems, isNotEmpty);
    expect(result.visibleItems.first.key, 'achievement_motivation_response');
    expect(result.visibleItems.first.supportsExamModeOnly, isTrue);
    expect(result.calibrationPosture, 'stable');
    expect(result.unknowns,
        contains('Reliable time-capacity data is still missing.'));
  });

  test('provider records canonical binding telemetry', () async {
    final events = <Map<String, dynamic>>[];
    final container = ProviderContainer(
      overrides: [
        profileContextProvider.overrideWith(
          (ref) async => {
            'knowledge_summary': {
              'active_learning_subjects': ['physics'],
              'overall_mastery': 0.55,
            },
            'cognitive_summary': {
              'active_patterns': ['structured'],
            },
            'user_insight_state': {
              'current_state': {'focus': 'exam prep'},
              'readiness': {'energy': 0.6},
            },
            'user_insight_transparency': {
              'claims': [
                {
                  'id': 'claim_1',
                  'label': 'Claim 1',
                  'value': 'steady',
                  'controls': ['wrong'],
                },
              ],
            },
          },
        ),
        ws6BindingTelemetryRecorderProvider.overrideWith(
          (ref) => (
              {required String outcome, Map<String, dynamic>? metadata}) async {
            events.add({
              'outcome': outcome,
              'metadata': metadata ?? <String, dynamic>{},
            });
          },
        ),
      ],
    );
    addTearDown(container.dispose);

    await container.read(ws6TransparentProfileViewProvider.future);

    expect(events, hasLength(1));
    expect(events.single['outcome'], 'canonical_embedded');
    expect((events.single['metadata'] as Map<String, dynamic>)['source'],
        'user_insight_transparency');
  });

  test('provider records deprecated fallback telemetry', () async {
    final events = <Map<String, dynamic>>[];
    final container = ProviderContainer(
      overrides: [
        profileContextProvider.overrideWith(
          (ref) async => {
            'knowledge_summary': {
              'active_learning_subjects': ['physics'],
              'overall_mastery': 0.55,
            },
            'cognitive_summary': {
              'active_patterns': ['structured'],
            },
            'user_insight_state': {
              'current_state': {'focus': 'exam prep'},
              'readiness': {'energy': 0.6},
            },
          },
        ),
        profileInsightsProvider.overrideWith(
          (ref) async => throw Exception('profile insights unavailable'),
        ),
        transparentProfileProvider.overrideWith(
          (ref) async => {
            'layer_1': {
              'goals': ['连续完成计划'],
            },
            'layer_2': {
              'persona': {
                'capabilities': {'energy': 0.62},
              },
            },
            'layer_3': {
              'patterns': ['review before sleep'],
            },
          },
        ),
        ws6BindingTelemetryRecorderProvider.overrideWith(
          (ref) => (
              {required String outcome, Map<String, dynamic>? metadata}) async {
            events.add({
              'outcome': outcome,
              'metadata': metadata ?? <String, dynamic>{},
            });
          },
        ),
      ],
    );
    addTearDown(container.dispose);

    await container.read(ws6TransparentProfileViewProvider.future);

    expect(events, hasLength(1));
    expect(events.single['outcome'], 'deprecated_fallback');
    expect((events.single['metadata'] as Map<String, dynamic>)['source'],
        'transparentProfileProvider');
  });

  test('provider records binding failure telemetry', () async {
    final events = <Map<String, dynamic>>[];
    final container = ProviderContainer(
      overrides: [
        profileContextProvider.overrideWith(
          (ref) async => throw Exception('profile context unavailable'),
        ),
        transparentProfileProvider.overrideWith(
          (ref) async =>
              throw Exception('legacy transparent profile unavailable'),
        ),
        ws6BindingTelemetryRecorderProvider.overrideWith(
          (ref) => (
              {required String outcome, Map<String, dynamic>? metadata}) async {
            events.add({
              'outcome': outcome,
              'metadata': metadata ?? <String, dynamic>{},
            });
          },
        ),
      ],
    );
    addTearDown(container.dispose);

    final result =
        await container.read(ws6TransparentProfileViewProvider.future);

    expect(result.enabled, isFalse);
    expect(events, hasLength(1));
    expect(events.single['outcome'], 'binding_failure');
    expect((events.single['metadata'] as Map<String, dynamic>)['source'],
        'canonical_and_legacy_failed');
  });
}
