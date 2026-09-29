// V4-G06R1 · F-2 实现级钉：地图详情面板状态 chip 的 classic-light 可见性
// （CI 可失败，mutation 敏感）。
//
// 背景（review_r1.md F-2）：B1 修复（状态 chip 墨 Colors.white70 →
// DS.textSecondary）在 R1 的 M-B mutation（回退 white70）下全绿存活——
// 配对层守卫是 token 数学复算不泵产品屏，地图屏也不在 golden 集。
// 本钉补上实现层：泵真实 AchievementMapScreen → 画布节点点按 →
// _showNodePreview → _AchievementNodeBottomSheet → _MetaChip（map 屏
// :204 状态 chip 接线），对渲染产物断言：
//   ① 墨色 == DS.textSecondary（token 接线契约，M-B 回退必红）；
//   ② 该墨对 deepSpace 详情面板（classic-light 模型，与配对层守卫同式）
//      ≥4.5:1（可见性语义，任何非校准色回退必红）。
// 配对层（v4_g06_family_contrast_guard_test.dart）与实现层（本文件）
// 两层口径不可互替（头注同款声明）。
//
// 判定环境：classic-light（AppThemes.lightTheme + ThemeManager 默认档）、
// MediaQuery.disableAnimations=true（reduce-motion 等价形态：画布循环
// 停表、节点无入场缩放——同时钉住 reduce-motion 下路径可达）。
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/screens/achievement_map_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

import '../../../../shared/i18n_test_helper.dart';

/// deepSpace 详情面板 classic-light 模型（与配对层守卫同式：亮档=
/// #FAFAFA 混 brandSecondary 12%）。
Color _deepSpacePanelModel() {
  final c = SparkleColors.light();
  return Color.lerp(const Color(0xFFFAFAFA), c.brandSecondary, 0.12)!;
}

double _contrastRatio(Color a, Color b) {
  double lum(Color c) =>
      0.2126 * _lin(c.r * 255.0) +
      0.7152 * _lin(c.g * 255.0) +
      0.0722 * _lin(c.b * 255.0);
  final la = lum(a);
  final lb = lum(b);
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

double _lin(double channel) {
  final v = channel / 255.0;
  return v <= 0.04045
      ? v / 12.92
      : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
}

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}

/// 地图种子仓：单节点 blocked 态（状态 chip 的修复靶形态）。
class _SeededMapRepository extends AchievementRepository {
  _SeededMapRepository() : super(_NoopApiClient());

  @override
  Future<AchievementListResponse> getAchievements({
    String? category,
    AchievementRarity? rarity,
    bool includeHidden = false,
    bool includeInactive = false,
  }) async =>
      AchievementListResponse(
        achievements: const <AchievementWithProgress>[],
        totalAchievements: 0,
        totalUnlocked: 0,
        categories: const <String, dynamic>{},
      );

  @override
  Future<AchievementStats> getAchievementStats() async => AchievementStats(
        totalAchievements: 1,
        unlockedCount: 0,
        unlockedPercentage: 0,
        commonCount: 0,
        rareCount: 1,
        epicCount: 0,
        legendaryCount: 0,
        hiddenFound: 0,
        currentStreak: 0,
        totalPhotons: 0,
      );

  @override
  Future<StreakStats> getStreakStats() async => StreakStats(
        currentStreak: 0,
        maxStreak: 0,
        longestStreak: 0,
        freezeCharges: 0,
        maxFreezeCharges: 3,
        totalCheckinDays: 0,
      );

  @override
  Future<GalaxySkinListResponse> getGalaxySkins() async =>
      GalaxySkinListResponse(skins: const <GalaxySkin>[]);

  @override
  Future<List<UserTitle>> getTitles() async => const <UserTitle>[];

  @override
  Future<SparkContract?> getContractStatus() async => null;

  @override
  Future<AchievementMapData> getAchievementMap() async => AchievementMapData(
        nodes: <AchievementMapNode>[
          AchievementMapNode(
            id: 'g06_nail_node',
            name: '返修钉节点',
            rarity: AchievementRarity.rare,
            category: 'streak',
            // 放 (400,700)：视口居中换算后落画布中部空档（避开顶部
            // lane 图例面板 IgnorePointer(false) 与右下缩放钮的命中区）。
            position: const <String, double>{'x': 400, 'y': 700},
            isUnlocked: false,
            lane: 'streak_lane',
            laneLabel: '连续之道',
            // displayState/progressPercentage 走默认（'blocked'/0）——
            // 状态 chip 靶形态=blocked（zh 标签「前置阻塞」）。
          ),
        ],
      );
}

Future<void> _pumpMapAndOpenSheet(WidgetTester tester) async {
  // 感官反馈 pref 关断（音效/触感静默，golden harness 同口径）。
  SharedPreferences.setMockInitialValues(const <String, Object>{
    'bgm.enabled': false,
    'sensory_feedback.sound_enabled': false,
    'sensory_feedback.haptic_enabled': false,
    'sensory_feedback.ambient_enabled': false,
  });
  // 逻辑面 800x1200（dpr=1）：视口居中换算后节点落画布空档。
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(800, 1200);
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    // disableAnimations=true → context.reduceMotion：画布循环停表、节点
    // 无入场缩放（reduce-motion 等价形态下路径可达）。经 MaterialApp
    // builder 注入——外层 MediaQuery 会被 MaterialApp 自建 MediaQuery
    // 覆盖，builder 才是权威注入点。
    ProviderScope(
      overrides: [
        achievementRepositoryProvider.overrideWithValue(
          _SeededMapRepository(),
        ),
      ],
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
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context).copyWith(disableAnimations: true),
          child: child ?? const SizedBox.shrink(),
        ),
        home: const AchievementMapScreen(),
      ),
    ),
  );
  // 地图仓异步落定 + 视口居中 post-frame 回调。
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 100));
  await tester.pump(const Duration(milliseconds: 100));

  // 泵真实节点（_CosmicNodeWidget 私有类，按 runtimeType 定位）并点开
  // 详情面板——实现级：chip 由 map 屏 onNodeTap → _showNodePreview 链路
  // 产出，非测试侧合成。
  final nodeFinder = find.byWidgetPredicate(
    (w) => w.runtimeType.toString() == '_CosmicNodeWidget',
  );
  expect(nodeFinder, findsOneWidget, reason: '地图画布节点已渲染');
  await tester.tap(nodeFinder);
  // bottom sheet 弹入（_sheetDuration=300ms SpringCurve）。
  await tester.pump(const Duration(milliseconds: 100));
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pump(const Duration(milliseconds: 200));
}

void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
    'F-2 实现级钉：地图详情面板状态 chip classic-light 可见'
    '（textSecondary 接线 + ≥4.5:1，M-B 回退必红）',
    (tester) async {
      await _pumpMapAndOpenSheet(tester);
      expect(tester.takeException(), isNull, reason: '详情面板渲染异常');

      // 状态 chip 文案直出（displayState=blocked → zh 标签）。
      const stateLabel = '前置阻塞';
      final chipTextFinder = find.text(stateLabel);
      expect(chipTextFinder, findsOneWidget, reason: '状态 chip 文案直出');

      // ① token 接线契约：渲染 Text 的墨色 == DS.textSecondary。
      //    （B1 修复靶=achievement_map_screen _MetaChip color 入参；
      //    M-B 回退 Colors.white70 在此必红。）
      final chipText = tester.widget<Text>(chipTextFinder);
      final renderedInk = chipText.style?.color;
      expect(
        renderedInk,
        DS.textSecondary,
        reason: '状态 chip 墨必须走 DS.textSecondary 校准令牌'
            '（实到 $renderedInk）',
      );

      // ② classic-light 可见性语义：同一渲染墨对 deepSpace 详情面板
      //    （配对层守卫同式模型）≥4.5:1。white70 形态在此 ~1.1:1 必红。
      final panel = _deepSpacePanelModel();
      final ratio = _contrastRatio(renderedInk!, panel);
      expect(
        ratio,
        greaterThanOrEqualTo(4.5),
        reason: 'classic-light 状态 chip 墨/详情面板=$ratio 应达正文阈值',
      );
    },
  );
}
