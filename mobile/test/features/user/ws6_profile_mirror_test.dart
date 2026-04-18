import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/models/ws6_profile_mirror_models.dart';
import 'package:sparkle/features/user/presentation/providers/ws6_profile_mirror_provider.dart';
import 'package:sparkle/features/user/presentation/widgets/mirror_bar.dart';

void main() {
  testWidgets('mirror bar renders four dimensions and presence label', (tester) async {
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
          sourceLabel: 'profileContext.knowledge_summary.active_learning_subjects',
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

  test('adapter builds mirror bar and transparent profile from legacy maps', () {
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
}
