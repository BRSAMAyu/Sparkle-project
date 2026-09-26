import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/release_flags_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_unlock_dialog.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';
import '../shared/i18n_test_helper.dart';

AchievementUnlockEvent _buildEvent() => AchievementUnlockEvent(
      achievementId: 'mirofish_first_simulation',
      name: '仿真开场',
      rarity: AchievementRarity.common,
      unlockedAt: DateTime(2026, 3, 28, 12),
      rewardPreview: const <String>['解锁高光样式'],
      gloryLines: const <String>['你第一次把知识点拉进了真实讨论现场。'],
      surfacePreview: const <String>['学习场景模拟'],
    );

/// V3-FIX-190：带视觉元素奖励的成就事件
AchievementUnlockEvent _buildVisualElementEvent() => AchievementUnlockEvent(
      achievementId: 've_reward_achievement',
      name: '视觉元素成就',
      rarity: AchievementRarity.common,
      unlockedAt: DateTime(2026, 3, 28, 12),
      rewards: const <Map<String, dynamic>>[
        <String, dynamic>{'type': 'visual_element', 'name': '星火粒子'},
      ],
    );

/// V3-FIX-190：/release-flags 拉取面在测试内快速失败（无网络）
class _ThrowingApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('no network in release flags test');
}

/// V3-FIX-190：钉住旗值的 provider 覆盖（测试封闭，无网络）
List<Override> _flagOverrides({required bool visualElements}) => [
      apiClientProvider.overrideWithValue(_ThrowingApiClient()),
      releaseFlagsProvider.overrideWith(
        (ref) => ReleaseFlagsNotifier(_ThrowingApiClient())
          ..seed(ReleaseFlags(visualElements: visualElements)),
      ),
    ];

Widget _dialogHost(
  WidgetBuilder builder, {
  required bool visualElements,
}) =>
    ProviderScope(
      overrides: _flagOverrides(visualElements: visualElements),
      child: testMaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: FilledButton(
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: builder,
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );

void main() {
  setUp(setUpI18nForTesting);
  testWidgets('achievement unlock dialog closes before share callback',
      (tester) async {
    var shared = 0;

    await tester.pumpWidget(
      _dialogHost(
        (_) => AchievementUnlockDialog(
          event: _buildEvent(),
          onShare: () {
            shared += 1;
          },
        ),
        visualElements: false,
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
    expect(find.text('仿真开场'), findsOneWidget);

    await tester.ensureVisible(find.text('分享'));
    await tester.tap(find.text('分享'));
    await tester.pumpAndSettle();

    expect(shared, 1);
    expect(find.text('仿真开场'), findsNothing);
  });

  testWidgets('achievement unlock dialog closes from close action',
      (tester) async {
    await tester.pumpWidget(
      _dialogHost(
        (_) => AchievementUnlockDialog(event: _buildEvent()),
        visualElements: false,
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();
    expect(find.text('仿真开场'), findsOneWidget);

    await tester.ensureVisible(find.text('关闭'));
    await tester.tap(find.text('关闭'));
    await tester.pumpAndSettle();

    expect(find.text('仿真开场'), findsNothing);
  });

  testWidgets('achievement unlock dialog compact view rewards closes once',
      (tester) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await tester.binding.setSurfaceSize(const Size(280, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    var viewed = 0;

    await tester.pumpWidget(
      _dialogHost(
        (_) => AchievementUnlockDialog(
          event: _buildEvent(),
          onViewRewards: () {
            viewed += 1;
          },
        ),
        visualElements: false,
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    final rewardsFinder = find.text('查看奖励');
    await tester.ensureVisible(rewardsFinder);
    await tester.tap(rewardsFinder, warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(viewed, 1);
    expect(find.text('仿真开场'), findsNothing);
  });

  // V3-FIX-190 红→绿：release flag off/unavailable（fail-closed）期，成就弹窗
  // 必须裁剪「解锁视觉元素」奖励叙事——旗关时元素不可用，展示即空头支票。
  // base 上无旗判定 → 叙事无条件渲染 → 红（findsNothing 失败实录在案）。
  testWidgets(
      'flags unavailable fail-closed trims visual element reward narrative',
      (tester) async {
    await tester.pumpWidget(
      _dialogHost(
        (_) => AchievementUnlockDialog(event: _buildVisualElementEvent()),
        visualElements: false,
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(
      find.text('视觉元素'),
      findsNothing,
      reason: 'flag visual_elements off/unavailable 时不得展示元素奖励叙事',
    );
    expect(find.text('星火粒子'), findsNothing);
  });

  // V3-FIX-190 邻域守卫：旗开时叙事必须照常展示——裁剪只许关闸旗 off 期，
  // 不许误伤 rollout 后的奖励正反馈。
  testWidgets('flags on keeps visual element reward narrative', (tester) async {
    await tester.pumpWidget(
      _dialogHost(
        (_) => AchievementUnlockDialog(event: _buildVisualElementEvent()),
        visualElements: true,
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(find.text('视觉元素'), findsOneWidget);
    expect(find.text('星火粒子'), findsOneWidget);
  });
}
