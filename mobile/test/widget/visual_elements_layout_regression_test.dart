import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/visual_elements/data/repositories/visual_element_repository.dart';
import 'package:sparkle/features/visual_elements/domain/services/visual_recommendation_service.dart';
import 'package:sparkle/features/visual_elements/presentation/providers/visual_recommendation_provider.dart';
import 'package:sparkle/features/visual_elements/presentation/screens/visual_elements_screen.dart';
import 'package:sparkle/features/visual_elements/presentation/widgets/visual_element_preview_dialog.dart';
import 'package:sparkle/features/visual_elements/presentation/widgets/visual_element_unlock_dialog.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  group('visual elements layout regression', () {
    testWidgets('visual elements screen handles long copy on compact width',
        (tester) async {
      await _setCompactSurface(tester);
      final elements = _buildElements();
      final repository = _FakeVisualElementRepository(elements);

      await _pumpApp(
        tester,
        child: const VisualElementsScreen(),
        overrides: [
          visualElementRepositoryProvider.overrideWithValue(repository),
          visualRecommendationProvider.overrideWith(
            (ref) async => [
              VisualRecommendation(
                element: elements.first,
                reason: VisualRecommendationReason.focus,
                score: 96,
              ),
              VisualRecommendation(
                element: elements.last,
                reason: VisualRecommendationReason.night,
                score: 91,
              ),
            ],
          ),
        ],
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 600));
      await tester.pump(const Duration(milliseconds: 600));

      expect(find.textContaining('视觉元素'), findsOneWidget);
      expect(find.textContaining('超长名称'), findsWidgets);
      expect(
        tester.takeException(),
        isNull,
        reason: 'initial recommended tab should not overflow on compact width',
      );

      await tester.ensureVisible(find.text('全部'));
      await tester.tap(find.text('全部'), warnIfMissed: false);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      expect(
        tester.takeException(),
        isNull,
        reason: 'switching to all tab should not overflow on compact width',
      );

      final scrollable = find.byType(Scrollable).first;
      await tester.scrollUntilVisible(
        find.textContaining('当前荣耀套装'),
        240,
        scrollable: scrollable,
      );

      expect(find.textContaining('当前荣耀套装'), findsOneWidget);
      expect(
        tester.takeException(),
        isNull,
        reason: 'all tab should remain overflow-safe on compact width',
      );
    });

    testWidgets('preview dialog keeps actions reachable with long bundle copy',
        (tester) async {
      await _setCompactSurface(tester);
      final elements = _buildElements();
      final bundle = elements.last;

      await _pumpApp(
        tester,
        child: VisualElementPreviewDialog(
          element: bundle,
          availableElements: elements,
          unlockedElementIds: {for (final element in elements) element.id},
          baseConfig: UserVisualConfig(
            equippedBackground: elements[0],
            equippedParticle: elements[1],
            equippedEffect: elements[2],
          ),
          isUnlocked: true,
          onEquip: _noop,
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.textContaining('一键装备套装'), findsOneWidget);
      expect(find.textContaining('套装部件'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('unlock dialog scrolls safely with multiple long names',
        (tester) async {
      await tester.binding.setSurfaceSize(const Size(320, 480));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final elements = _buildElements()
          .map(
            (element) => VisualElementModel(
              id: element.id,
              name: '${element.name} 超长展示文本用于验证解锁弹窗的滚动与换行稳定性',
              description: element.description,
              elementType: element.elementType,
              rarity: element.rarity,
              unlockSource: element.unlockSource,
              isDefault: element.isDefault,
              sortOrder: element.sortOrder,
              previewUrl: element.previewUrl,
              iconUrl: element.iconUrl,
              category: element.category,
              config: element.config,
              unlockRequirement: element.unlockRequirement,
              isUnlocked: true,
              unlockedAt: element.unlockedAt,
              isEquipped: element.isEquipped,
            ),
          )
          .toList();

      await _pumpApp(
        tester,
        child: VisualElementUnlockDialog(
          elements: elements,
          onView: _noop,
          reduceMotion: true,
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.textContaining('解锁视觉元素'), findsOneWidget);
      expect(find.textContaining('查看收藏'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}

Future<void> _pumpApp(
  WidgetTester tester, {
  required Widget child,
  List<Override> overrides = const [],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: testMaterialApp(
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(body: child),
      ),
    ),
  );
}

Future<void> _setCompactSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(320, 640));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

List<VisualElementModel> _buildElements() {
  final background = VisualElementModel(
    id: 'bg-aurora',
    name: '极光长夜专注背景超长名称超长名称',
    description: '用于验证推荐卡、网格卡和预览页在长标题与长描述同时出现时依然保持稳定。',
    elementType: VisualElementType.background,
    rarity: VisualElementRarity.legendary,
    unlockSource: VisualElementUnlockSource.event,
    isDefault: true,
    sortOrder: 1,
    isUnlocked: true,
    config: const {
      'display_slot': 'home_ambience',
      'prestige_label': '极光之冠',
      'set_id': 'aurora-overdrive',
      'visibility_weight': 96,
      'background_id': 'bg-aurora',
    },
    unlockRequirement: const {
      'event_end_at': '2026-04-18T12:00:00Z',
    },
  );

  final particle = VisualElementModel(
    id: 'pt-streak',
    name: '连胜流光粒子轨迹延展版',
    description: '用于验证卡片徽标和状态区在文案变长时不会把布局撑爆。',
    elementType: VisualElementType.particle,
    rarity: VisualElementRarity.epic,
    unlockSource: VisualElementUnlockSource.achievement,
    isDefault: true,
    sortOrder: 2,
    isUnlocked: true,
    config: const {
      'display_slot': 'streak_flame',
      'prestige_label': '连胜流火',
      'set_id': 'aurora-overdrive',
      'visibility_weight': 90,
      'particle_id': 'pt-streak',
    },
  );

  final effect = VisualElementModel(
    id: 'fx-crown',
    name: '荣耀征服特效延展标题版本',
    description: '用于验证推荐理由、稀有度和操作按钮在紧凑宽度下依然能共同存在。',
    elementType: VisualElementType.effect,
    rarity: VisualElementRarity.rare,
    unlockSource: VisualElementUnlockSource.shop,
    isDefault: true,
    sortOrder: 3,
    isUnlocked: true,
    config: const {
      'display_slot': 'star_map_effect',
      'prestige_label': '荣耀余晖',
      'set_id': 'aurora-overdrive',
      'visibility_weight': 88,
      'effect_id': 'fx-crown',
    },
  );

  final eventBanner = VisualElementModel(
    id: 'bg-banner',
    name: '限时活动主页横幅超长名字用于验证滚动卡片',
    description: '这是一条更长的活动文案，用来确认横向滑动卡片在小屏上不会出现纵向截断或 RenderFlex 溢出。',
    elementType: VisualElementType.background,
    rarity: VisualElementRarity.epic,
    unlockSource: VisualElementUnlockSource.event,
    isDefault: false,
    sortOrder: 4,
    isUnlocked: false,
    config: const {
      'display_slot': 'profile_banner',
      'prestige_label': '限时横幅',
      'visibility_weight': 84,
    },
    unlockRequirement: const {
      'event_end_at': '2026-04-05T12:00:00Z',
    },
  );

  final bundle = VisualElementModel(
    id: 'bundle-aurora',
    name: '极光征服荣耀整套装扮超长名称超长名称',
    description: '整套组合需要同时展示套装标签、集齐进度、长名称和长描述，是最容易触发布局问题的场景之一。',
    elementType: VisualElementType.bundle,
    rarity: VisualElementRarity.legendary,
    unlockSource: VisualElementUnlockSource.season,
    isDefault: false,
    sortOrder: 5,
    isUnlocked: true,
    config: const {
      'display_slot': 'bundle',
      'prestige_label': '极光征服者',
      'set_id': 'aurora-overdrive',
      'visibility_weight': 99,
      'background_id': 'bg-aurora',
      'particle_id': 'pt-streak',
      'effect_id': 'fx-crown',
    },
  );

  return [background, particle, effect, eventBanner, bundle];
}

class _FakeVisualElementRepository extends VisualElementRepository {
  _FakeVisualElementRepository(this.elements) : super(_UnusedApiClient());

  final List<VisualElementModel> elements;

  @override
  Future<VisualElementListResponse> getVisualElements({
    VisualElementType? type,
    VisualElementRarity? rarity,
    String? category,
    bool unlockedOnly = false,
  }) async {
    final filtered = elements.where((element) {
      if (type != null && element.elementType != type) return false;
      if (rarity != null && element.rarity != rarity) return false;
      if (category != null && element.category != category) return false;
      if (unlockedOnly && !element.isUnlocked) return false;
      return true;
    }).toList();

    return VisualElementListResponse(
      items: filtered,
      total: filtered.length,
    );
  }

  @override
  Future<VisualElementListResponse> getUnlockedElements({
    VisualElementType? type,
  }) async {
    final unlocked = elements.where((element) {
      if (!element.isUnlocked) return false;
      if (type != null && element.elementType != type) return false;
      return true;
    }).toList();

    return VisualElementListResponse(
      items: unlocked,
      total: unlocked.length,
    );
  }

  @override
  Future<UserVisualConfig> getUserConfig() async => UserVisualConfig(
        equippedBackground: elements[0],
        equippedParticle: elements[1],
        equippedEffect: elements[2],
      );

  @override
  Future<VisualElementListResponse> getDefaultElements() async {
    final defaults = elements.where((element) => element.isDefault).toList();
    return VisualElementListResponse(
      items: defaults,
      total: defaults.length,
    );
  }
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void _noop() {}
