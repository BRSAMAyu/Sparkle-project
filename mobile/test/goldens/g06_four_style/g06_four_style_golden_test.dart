// V4-G06 · 小队/自我锚/光子/成就 家族关键面四风格确定性 golden 钉
// （CI 可失败）+ 语义钉（同源泵制）。
//
// 面 = 真实组件 + 确定性 seed（F05 判例 / G01 四风格 golden 同款）：
//   · familyFaces：RarityBadge×4（成就身份资产面）+ BonfireWidget
//     （小队火堆装饰面，reduce-motion 静帧等价）+ StreakIndicator
//     （自我锚连续面，账本数字直出）——self-anchor 非排行 / 火堆非权益
//     信号由语义钉同场断言。
//   · unlockDialogLegendary：成就解锁庆祝弹窗（固定美术底 + 实算墨，
//     L19「庆祝可关」语义：关闭按钮可达、彩带随 reduce-motion 不发射）。
// 比较 = B04 容差比较器（0.5% 分数口径带界，V3-FIX-383 钉死单位；
// 真实回归 ≥0.6% 硬失败——「CI 可失败」由常态比对路径保证，无 skip 门）。
// 基线签发：`flutter test --update-goldens test/goldens/g06_four_style/`
// （仅基线机执行；golden 基线变更需独立签理由，EVALUATION_PROTOCOL）。
library;

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/providers/release_flags_provider.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_unlock_dialog.dart';
import 'package:sparkle/features/achievement/presentation/widgets/rarity_badge.dart';
import 'package:sparkle/features/achievement/presentation/widgets/streak_indicator.dart';
import 'package:sparkle/features/community/presentation/widgets/bonfire_widget.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

import '../../core/design/style_preview/style_preview_test_harness.dart';
import '../../shared/i18n_test_helper.dart';
import '../b04_visual_baseline/b04_harness.dart'
    show b04InstallTolerantComparator;
import '../q03_visual_qa/q03_harness.dart' show q03MockPlatformChannels;

const List<PixelPreviewProfile> _kProfiles = <PixelPreviewProfile>[
  PixelPreviewProfile.classic,
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

/// V3-FIX-190：/release-flags 拉取面在测试内快速失败（无网络），旗值
/// 钉默认（fail-closed 与既有 dialog 测试同口径）。
class _ThrowingApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('no network in g06 golden test');
}

List<Override> _flagOverrides() => [
      apiClientProvider.overrideWithValue(_ThrowingApiClient()),
      releaseFlagsProvider.overrideWith(
        (ref) => ReleaseFlagsNotifier(_ThrowingApiClient())
          ..seed(const ReleaseFlags()),
      ),
    ];

AchievementUnlockEvent _legendaryEvent() => AchievementUnlockEvent(
      achievementId: 'g06_golden_legendary',
      name: '百日连续学习者',
      rarity: AchievementRarity.legendary,
      unlockedAt: DateTime(2026, 9, 17, 9),
      isFirst: true,
      rewardPreview: const <String>['限定学习徽章'],
      gloryLines: const <String>['一百天，没有一天缺席。'],
      surfacePreview: const <String>['火堆金边'],
    );

StreakStats _goldenStreakStats() => StreakStats(
      currentStreak: 12,
      maxStreak: 30,
      longestStreak: 30,
      freezeCharges: 2,
      maxFreezeCharges: 3,
      totalCheckinDays: 128,
      lastActivityDate: DateTime(2026, 9, 17),
    );

/// 真实主题管道宿主（style_preview_test_harness 同机制）+ 测试封闭覆盖。
Widget _host({
  required Widget child,
  List<Override> overrides = const <Override>[],
}) =>
    AnimatedBuilder(
      animation: ThemeManager(),
      builder: (context, _) => ProviderScope(
        overrides: overrides,
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: AppThemes.lightTheme,
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(body: Center(child: child)),
        ),
      ),
    );

Future<void> _pumpProfiled(
  WidgetTester tester,
  PixelPreviewProfile profile,
  Widget child, {
  List<Override> overrides = const <Override>[],
}) async {
  // BGM/音效 pref 门关断（golden 只钉视觉面）：q03 平台桩会让 BGM
  // init 成功并留下永不归零的周期计时器（testWidgets 结束 pending
  // timer 硬失败）——从源头关断而不是事后排空。
  SharedPreferences.setMockInitialValues(const <String, Object>{
    'bgm.enabled': false,
    'sensory_feedback.sound_enabled': false,
    'sensory_feedback.haptic_enabled': false,
    'sensory_feedback.ambient_enabled': false,
  });
  final manager = await freshThemeManager();
  if (profile != PixelPreviewProfile.classic) {
    await manager.setPixelPreviewProfile(profile);
  }
  await tester.pumpWidget(
    KeyedSubtree(
      key: ValueKey('g06-golden-${profile.name}'),
      // 契约：MediaQuery.disableAnimations=true → 火堆静帧/彩带不发射/
      // 徽章停表——golden 同时钉住 reduce-motion 等价形态。
      child: MediaQuery(
        data: const MediaQueryData(disableAnimations: true),
        child: _host(child: child, overrides: overrides),
      ),
    ),
  );
  // 等异步初始化落定；不用 pumpAndSettle（BgmService 等周期计时器）。
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  setUpAll(() async {
    b04InstallTolerantComparator();
    // mock flutter_tester 缺平台实现的原生通道（q03 同款）：audioplayers
    // 走静音假体、secure_storage/path_provider/连通性返回空——截图等待
    // endOfFrame 会冲刷未决平台调用，无桩即 MissingPluginException 假失败。
    q03MockPlatformChannels();
    // BGM shutdown 门（服务自带）：_refreshPlayback 对 _shutdownRequested
    // 短路——弹窗 BgmScope 的 activate 不再触发 AudioPlayer 创建与
    // 播放路径的周期计时器（golden 只钉视觉面；pref 门不够，服务静态
    // 缓存会跨用例携带先前用例的 mock prefs）。
    await BgmService.dispose();
  });
  setUp(setUpI18nForTesting);

  testWidgets('家族合成面（徽章/火堆/自我锚）× 四风格 golden + 语义钉',
      (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(800, 1200);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    Widget buildFaces() => SingleChildScrollView(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              // 成就身份资产面：四稀有度徽章同一行（L19：像素网格同一）。
              const Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  RarityBadge(rarity: AchievementRarity.common),
                  RarityBadge(rarity: AchievementRarity.rare),
                  RarityBadge(rarity: AchievementRarity.epic),
                  RarityBadge(rarity: AchievementRarity.legendary),
                ],
              ),
              const SizedBox(height: 24),
              // 小队火堆装饰面（D-COMM：装饰非权益信号）。
              const BonfireWidget(level: 3, size: 80),
              const SizedBox(height: 24),
              // 自我锚连续面（真实账本数字，非排行）。
              const StreakIndicator(style: StreakIndicatorStyle.standard),
            ],
          ),
        );

    for (final profile in _kProfiles) {
      await _pumpProfiled(
        tester,
        profile,
        buildFaces(),
        overrides: [
          streakStatsProvider.overrideWithValue(_goldenStreakStats()),
        ],
      );
      expect(tester.takeException(), isNull, reason: '$profile 渲染异常');

      // 语义钉（与 golden 同源泵制）：身份/装饰/账本三面语义在四档下
      // 同在——「任一风格可作发布默认」的语义下界。
      expect(find.byType(RarityBadge), findsNWidgets(4),
          reason: '$profile 稀有度徽章语义面');
      expect(find.byKey(const ValueKey('bonfire-level-badge')), findsOneWidget,
          reason: '$profile 火堆等级徽标');
      expect(
        find.byWidgetPredicate(
          (w) => w is Text && (w.data ?? '').contains('12'),
        ),
        findsWidgets,
        reason: '$profile 自我锚连续账本数字直出',
      );
      final badgeSemantics = tester.getSemantics(
        find.byType(RarityBadge).first,
      );
      expect(badgeSemantics.label, isNotEmpty,
          reason: '$profile 徽章读屏标签非空（PixelFrame 语义由 child 承载）');

      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/g06_family_faces_${profile.name}.png'),
      );
    }
  });

  testWidgets('成就解锁庆祝弹窗（legendary）× 四风格 golden + 可关语义钉',
      (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(800, 1200);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    for (final profile in _kProfiles) {
      await _pumpProfiled(tester, profile, const SizedBox.shrink(),
          overrides: _flagOverrides(),);
      // 弹窗经真实 showDialog 打开（最上层实际画面，非栈底复用）。
      final context = tester.state(find.byType(Scaffold)).context;
      // ignore: unawaited_futures
      showDialog<void>(
        context: context,
        builder: (_) => AchievementUnlockDialog(event: _legendaryEvent()),
      );
      for (var i = 0; i < 8; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      expect(tester.takeException(), isNull, reason: '$profile 弹窗渲染异常');

      // 庆祝可关语义（L19）：成就名直出 + 关闭按钮语义可达。
      expect(find.textContaining('百日连续学习者'), findsWidgets,
          reason: '$profile 庆祝内容直出');
      expect(
        find.byWidgetPredicate(
          (w) => w is Semantics && w.properties.button == true,
        ),
        findsWidgets,
        reason: '$profile 关闭/操作按钮语义可达（庆祝可关）',
      );

      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/g06_unlock_legendary_${profile.name}.png'),
      );

      // 关闭弹窗，避免跨档残留（KeyedSubtree 已隔离，防御性收尾）。
      final navigator = Navigator.of(context);
      navigator.pop();
      // 排空感官序列/BGM 淡入的 Future.delayed 挂起计时器。
      for (var i = 0; i < 10; i++) {
        await tester.pump(const Duration(milliseconds: 500));
      }
    }

    // 拆卸窗口期静音既有 known issue（q03 harness / chat_area_budget_test
    // 同配方，窄口径：只吞 Timer/animation 残留，不吞其余框架错误）——
    // 解锁弹窗的感官序列与庆祝动效计时器在 dispose 后仍有残留步进。
    final originalOnError = FlutterError.onError;
    FlutterError.onError = (details) {
      final msg = details.exceptionAsString();
      if (msg.contains('A Timer is still pending') ||
          msg.contains('An animation is still running even after')) {
        return;
      }
      originalOnError?.call(details);
    };
    try {
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      await tester.pump(const Duration(seconds: 30));
    } finally {
      FlutterError.onError = originalOnError;
    }
  });
}
