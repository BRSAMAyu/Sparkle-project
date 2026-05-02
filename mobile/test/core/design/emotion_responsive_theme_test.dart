import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/features/aurora/presentation/providers/emotion_state_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('emotion signals resolve low-stimulus config in auto mode', () {
    final state = EmotionState.fromAuroraStateBandJson({
      'type': 'aurora_state_band',
      'payload': {
        'emotion': 'focused',
        'fatigue_level': 0.7,
        'cognitive_load': 0.4,
        'stress_signal': 0.2,
      },
    });

    expect(state.responsiveConfig.fontSizeDelta, 1);
    expect(state.responsiveConfig.reduceMotion, true);
    expect(state.responsiveConfig.hideChallengeBadges, true);
  });

  test('manual normal override suppresses low-stimulus signals', () {
    final state = EmotionState.fromAuroraStateBandJson(
      {
        'payload': {
          'emotion': 'overwhelmed',
          'fatigue_level': 0.9,
          'cognitive_load': 0.9,
          'stress_signal': 0.9,
        },
      },
      mode: EmotionAdaptiveMode.alwaysNormal,
    );

    expect(state.responsiveConfig.isLowStimulus, false);
  });

  testWidgets('wrapper raises text and disables motion for low-stimulus mode',
      (tester) async {
    late ThemeData themed;
    late MediaQueryData media;
    late EmotionResponsiveConfig config;

    await tester.pumpWidget(
      const MaterialApp(
        home: EmotionResponsiveAppWrapper(
          config: EmotionResponsiveConfig.lowStimulus(),
          child: Builder(
            builder: _Probe.create,
          ),
        ),
      ),
    );

    final probe = tester.widget<_Probe>(find.byType(_Probe));
    themed = probe.theme;
    media = probe.media;
    config = probe.config;

    expect(config.isLowStimulus, true);
    expect(media.disableAnimations, true);
    expect(media.accessibleNavigation, true);
    expect(themed.textTheme.bodyMedium!.fontSize, 15);
  });

  testWidgets('style changes when adaptive state changes', (tester) async {
    Future<double> pumpWith(EmotionResponsiveConfig config) async {
      await tester.pumpWidget(
        MaterialApp(
          home: EmotionResponsiveAppWrapper(
            config: config,
            child: Builder(
              builder: (context) => Text(
                'sample',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      return tester.widget<Text>(find.text('sample')).style!.fontSize!;
    }

    final normalSize = await pumpWith(const EmotionResponsiveConfig.normal());
    final lowStimulusSize =
        await pumpWith(const EmotionResponsiveConfig.lowStimulus());

    expect(lowStimulusSize, normalSize + 1);
  });
}

class _Probe extends StatelessWidget {
  const _Probe({
    required this.theme,
    required this.media,
    required this.config,
  });

  final ThemeData theme;
  final MediaQueryData media;
  final EmotionResponsiveConfig config;

  static Widget create(BuildContext context) => _Probe(
        theme: Theme.of(context),
        media: MediaQuery.of(context),
        config: EmotionResponsiveTheme.of(context),
      );

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
