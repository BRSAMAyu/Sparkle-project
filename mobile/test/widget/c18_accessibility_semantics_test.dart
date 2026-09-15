import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/contextual_correction_bar.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/community/presentation/widgets/feed_post_card.dart';
import 'package:sparkle/features/home/presentation/providers/spine_status_band_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/aurora_status_band.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_status_indicator.dart';

import '../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('correction chips expose button semantics and 44dp targets',
      (tester) async {
    await _withSemantics(tester, () async {
      var tapped = false;
      await tester.pumpWidget(
        testMaterialApp(
          theme: AppThemes.lightTheme,
          home: Scaffold(
            body: ContextualCorrectionBar(
              onNotRightDirection: () => tapped = true,
              onRecalibrate: () {},
            ),
          ),
        ),
      );

      final chip = find.bySemanticsLabel('不是这个方向');
      expect(chip, findsOneWidget);
      expect(tester.getSize(chip).height, greaterThanOrEqualTo(44));

      await tester.tap(chip);
      expect(tapped, isTrue);
    });
  });

  testWidgets('Aurora status band exposes expandable status semantics',
      (tester) async {
    await _withSemantics(tester, () async {
      CorrectionOption? selected;
      await tester.pumpWidget(
        testMaterialApp(
          theme: AppThemes.lightTheme,
          home: Scaffold(
            body: AuroraStatusBand(
              state: AuroraBandState.calibrated,
              label: '已参考当前任务资料',
              correctionOptions: const [
                CorrectionOption(
                  label: '不是这个方向',
                  semanticValue: 'not_right_direction',
                  isFreeform: false,
                  isDisconfirming: true,
                ),
              ],
              onCorrectionTap: (option) => selected = option,
            ),
          ),
        ),
      );

      final band = find.bySemanticsLabel(RegExp('Aurora · 已校准'));
      expect(band, findsWidgets);
      expect(
        tester.getSize(find.byType(AuroraStatusBand)).height,
        greaterThanOrEqualTo(48),
      );

      await tester.tap(band.first);
      await tester.pumpAndSettle();

      final correction = find.bySemanticsLabel('不是这个方向');
      expect(correction, findsWidgets);

      await tester.tap(correction.first);
      expect(selected?.semanticValue, 'not_right_direction');
    });
  });

  testWidgets('task execution status is announced as a status node',
      (tester) async {
    await _withSemantics(tester, () async {
      await tester.pumpWidget(
        testMaterialApp(
          theme: AppThemes.lightTheme,
          home: const Scaffold(
            body: ExecutionStatusIndicator(
              status: ExecutionIntentStatus.running,
            ),
          ),
        ),
      );

      expect(find.bySemanticsLabel('执行状态: 执行中'), findsOneWidget);
    });
  });

  testWidgets('community feed card has post and action semantics',
      (tester) async {
    await _withSemantics(tester, () async {
      var liked = false;
      await tester.pumpWidget(
        testMaterialApp(
          theme: AppThemes.lightTheme,
          home: Scaffold(
            body: FeedPostCard(
              post: Post(
                id: 'post-1',
                userId: 'user-1',
                content: '今天完成了概率复习。',
                createdAt: DateTime(2026, 5),
                user: const PostUser(id: 'user-1', username: '小星'),
                topic: '数学',
                likeCount: 3,
              ),
              onLike: () => liked = true,
            ),
          ),
        ),
      );

      expect(find.bySemanticsLabel('小星. 今天完成了概率复习。'), findsOneWidget);
      final likeButton = find.bySemanticsLabel('3 点赞');
      expect(likeButton, findsOneWidget);
      expect(tester.getSize(likeButton).height, greaterThanOrEqualTo(44));
      expect(find.bySemanticsLabel('#数学'), findsOneWidget);

      await tester.tap(likeButton);
      expect(liked, isTrue);
    });
  });
}

Future<void> _withSemantics(
  WidgetTester tester,
  Future<void> Function() body,
) async {
  final semantics = tester.ensureSemantics();
  try {
    await body();
  } finally {
    semantics.dispose();
  }
}
