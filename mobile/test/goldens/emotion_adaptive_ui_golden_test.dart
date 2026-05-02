import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:golden_toolkit/golden_toolkit.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';

const bool _enableEmotionGoldens = bool.fromEnvironment(
  'ENABLE_EMOTION_GOLDEN',
);

void main() {
  group('Emotion Adaptive UI Goldens', () {
    testGoldens(
      'normal',
      (tester) async {
        await tester.pumpWidget(
          const _EmotionGoldenHarness(
            config: EmotionResponsiveConfig.normal(),
          ),
        );
        await screenMatchesGolden(tester, 'emotion_adaptive_normal');
      },
      skip: !_enableEmotionGoldens,
    );

    testGoldens(
      'low stimulus',
      (tester) async {
        await tester.pumpWidget(
          const _EmotionGoldenHarness(
            config: EmotionResponsiveConfig.lowStimulus(),
          ),
        );
        await screenMatchesGolden(tester, 'emotion_adaptive_low_stimulus');
      },
      skip: !_enableEmotionGoldens,
    );

    testGoldens(
      'manual normal override',
      (tester) async {
        await tester.pumpWidget(
          const _EmotionGoldenHarness(
            config: EmotionResponsiveConfig.normal(),
          ),
        );
        await screenMatchesGolden(tester, 'emotion_adaptive_manual_normal');
      },
      skip: !_enableEmotionGoldens,
    );
  });
}

class _EmotionGoldenHarness extends StatelessWidget {
  const _EmotionGoldenHarness({required this.config});

  final EmotionResponsiveConfig config;

  @override
  Widget build(BuildContext context) => MaterialApp(
        home: EmotionResponsiveAppWrapper(
          config: config,
          child: Scaffold(
            body: Center(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text('Focus plan'),
                      const SizedBox(height: 12),
                      const Chip(label: Text('Challenge badge')),
                      const SizedBox(height: 12),
                      FilledButton(
                        onPressed: () {},
                        child: const Text('Start'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      );
}
