import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

import '../shared/i18n_test_helper.dart';

/// SparkleIconButton watch accessibilitySettingsProvider，真实 notifier
/// 构造即发起服务端同步（Dio）——widget 测试里 stub 掉（照
/// a11y_batch5_semantics_test 先例），保持纯语义断言。
class _StubAccessibilitySettingsNotifier extends AccessibilitySettingsNotifier {
  _StubAccessibilitySettingsNotifier(super.ref);

  @override
  Future<void> load() async {}
}

/// A11Y-BATCH6A（N32 续 · 无名钮批六 A：10 个多钮集中文件 24 钮清零）：
///
/// 1. 12 个新 l10n 键 zh 侧可取值（en 侧由 l10n regen parity 守卫 +
///    编译期保证；批内另有 8 个既有键复用：back / close / share /
///    commonRefresh / exploreGalaxy / authShowPassword /
///    authHidePassword + 图标可见性图标族）；
/// 2. 甲式（SparkleIconButton semanticLabel）与乙式（material IconButton
///    tooltip + Icon semanticLabel 同键）代表面按名可定位且带按钮角色
///    （semantics finder 断言）；
/// 3. 单节点钉死——乙式下 bySemanticsLabel 命中的节点必须自身 isButton
///    （外挂 Semantics 反形制会把 label 拆成无角色的独立节点）；
/// 4. 两态钮按当前态命名（auth 密码可见 / capsule 收藏 / focus 正念
///    暂停形制），态翻转后语义名随之翻转；
/// 5. 同屏多钮各归其名（knowledge_detail AppBar 三钮形制）。
void main() {
  setUp(setUpI18nForTesting);

  final zh = AppLocalizationsZh();

  test('12 个新 a11y 键 zh 侧全部落地（en 侧走 l10n regen parity 守卫）', () {
    // auth（2）
    expect(zh.authShowConfirmPassword, '显示确认密码');
    expect(zh.authHideConfirmPassword, '隐藏确认密码');
    // cognitive 胶囊簇（2）
    expect(zh.capsuleFavorite, '收藏胶囊');
    expect(zh.capsuleUnfavorite, '取消收藏胶囊');
    // knowledge（2）
    expect(zh.knowledgeFavorite, '收藏知识');
    expect(zh.knowledgeUnfavorite, '取消收藏知识');
    // focus 正念（3）
    expect(zh.focusMindfulnessResume, '继续正念');
    expect(zh.focusMindfulnessPause, '暂停正念');
    expect(zh.focusBackToTask, '返回任务');
    // translation（1，参数化）
    expect(zh.translationRateStar(3), '评为 3 星');
    // documents / translation 复用键（1）
    expect(zh.commonSearchClear, '清除搜索');
    // visual_elements（1）
    expect(zh.visualElementsFilter, '筛选');
    // 本批复用的既有键（防漂移抽查）
    expect(zh.back, '返回');
    expect(zh.close, '关闭');
    expect(zh.share, '分享');
    expect(zh.commonRefresh, '刷新');
    expect(zh.exploreGalaxy, '探索星图');
    expect(zh.authShowPassword, '显示密码');
    expect(zh.authHidePassword, '隐藏密码');
  });

  group('批域标注面 semantics finder 断言', () {
    Future<void> pumpButton(WidgetTester tester, Widget button) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            accessibilitySettingsProvider
                .overrideWith(_StubAccessibilitySettingsNotifier.new),
          ],
          child: MaterialApp(home: Scaffold(body: Center(child: button))),
        ),
      );
      await tester.pump();
    }

    testWidgets(
        '甲式（capsule_jobs 返回/刷新形制）：SparkleIconButton semanticLabel '
        '按名可定位且带按钮角色', (tester) async {
      final semantics = tester.ensureSemantics();
      // 与 capsule_detail / knowledge_detail / theater / document_library /
      // visual_elements / mindfulness 返回任务 同形。
      await pumpButton(
        tester,
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SparkleIconButton(
              icon: const Icon(Icons.arrow_back),
              semanticLabel: zh.back,
              onPressed: () {},
              variant: ButtonVariant.ghost,
            ),
            SparkleIconButton(
              icon: const Icon(Icons.refresh),
              semanticLabel: zh.commonRefresh,
              onPressed: () {},
              variant: ButtonVariant.ghost,
            ),
          ],
        ),
      );

      expect(find.bySemanticsLabel('返回'), findsOneWidget);
      expect(find.bySemanticsLabel('刷新'), findsOneWidget);
      final handle = find.bySemanticsLabel('返回');
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets(
        '乙式（theater 设置面板关闭形制）：tooltip+Icon semanticLabel 同键——'
        '单节点有名按钮（双节点反形制下 label 节点无按钮角色，本断言即钉死'
        '单节点）', (tester) async {
      final semantics = tester.ensureSemantics();
      // 与 document_library / translation_history 搜索清除同形。
      await pumpButton(
        tester,
        IconButton(
          tooltip: zh.close,
          onPressed: () {},
          icon: Icon(
            Icons.close_rounded,
            semanticLabel: zh.close,
          ),
        ),
      );

      final handle = find.bySemanticsLabel('关闭');
      expect(handle, findsOneWidget);
      expect(tester.getSemantics(handle).flagsCollection.isButton, isTrue);
      semantics.dispose();
    });

    testWidgets(
        '两态钮按当前态命名（auth 密码可见性形制）：态翻转后语义名随之翻转',
        (tester) async {
      final semantics = tester.ensureSemantics();
      var obscured = true;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(
              child: StatefulBuilder(
                builder: (context, setState) => IconButton(
                  tooltip: obscured
                      ? zh.authShowPassword
                      : zh.authHidePassword,
                  onPressed: () => setState(() => obscured = !obscured),
                  icon: Icon(
                    obscured
                        ? Icons.visibility_off_outlined
                        : Icons.visibility_outlined,
                    semanticLabel: obscured
                        ? zh.authShowPassword
                        : zh.authHidePassword,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.bySemanticsLabel('显示密码'), findsOneWidget);
      expect(find.bySemanticsLabel('隐藏密码'), findsNothing);

      await tester.tap(find.byIcon(Icons.visibility_off_outlined));
      await tester.pump();

      expect(find.bySemanticsLabel('隐藏密码'), findsOneWidget);
      expect(find.bySemanticsLabel('显示密码'), findsNothing);
      semantics.dispose();
    });

    testWidgets(
        '两态钮按当前态命名（capsule 收藏形制 / focus 正念暂停形制）：'
        '未激活态与激活态各自成名', (tester) async {
      final semantics = tester.ensureSemantics();
      var favorite = false;
      var paused = false;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            accessibilitySettingsProvider
                .overrideWith(_StubAccessibilitySettingsNotifier.new),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: Center(
                child: StatefulBuilder(
                  builder: (context, setState) => Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SparkleIconButton(
                        icon: Icon(
                          favorite ? Icons.favorite : Icons.favorite_border,
                        ),
                        semanticLabel: favorite
                            ? zh.capsuleUnfavorite
                            : zh.capsuleFavorite,
                        onPressed: () =>
                            setState(() => favorite = !favorite),
                        variant: ButtonVariant.ghost,
                      ),
                      SparkleIconButton(
                        icon: Icon(
                          paused
                              ? Icons.play_arrow_rounded
                              : Icons.pause_rounded,
                        ),
                        semanticLabel: paused
                            ? zh.focusMindfulnessResume
                            : zh.focusMindfulnessPause,
                        onPressed: () => setState(() => paused = !paused),
                        variant: ButtonVariant.ghost,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(find.bySemanticsLabel('收藏胶囊'), findsOneWidget);
      expect(find.bySemanticsLabel('取消收藏胶囊'), findsNothing);
      expect(find.bySemanticsLabel('暂停正念'), findsOneWidget);
      expect(find.bySemanticsLabel('继续正念'), findsNothing);

      await tester.tap(find.byIcon(Icons.favorite_border));
      await tester.tap(find.byIcon(Icons.pause_rounded));
      await tester.pump();

      expect(find.bySemanticsLabel('取消收藏胶囊'), findsOneWidget);
      expect(find.bySemanticsLabel('收藏胶囊'), findsNothing);
      expect(find.bySemanticsLabel('继续正念'), findsOneWidget);
      expect(find.bySemanticsLabel('暂停正念'), findsNothing);
      semantics.dispose();
    });

    testWidgets(
        '同域三钮各归其名（knowledge_detail AppBar 形制）：back/favorite/'
        'share 各自按名可定位', (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SparkleIconButton(
              icon: const Icon(Icons.arrow_back),
              semanticLabel: zh.back,
              onPressed: () {},
              variant: ButtonVariant.ghost,
            ),
            SparkleIconButton(
              icon: const Icon(Icons.star_border),
              semanticLabel: zh.knowledgeFavorite,
              onPressed: () {},
              variant: ButtonVariant.ghost,
            ),
            SparkleIconButton(
              icon: const Icon(Icons.share_outlined),
              semanticLabel: zh.share,
              onPressed: () {},
              variant: ButtonVariant.ghost,
            ),
          ],
        ),
      );

      expect(find.bySemanticsLabel('返回'), findsOneWidget);
      expect(find.bySemanticsLabel('收藏知识'), findsOneWidget);
      expect(find.bySemanticsLabel('分享'), findsOneWidget);
      semantics.dispose();
    });

    testWidgets(
        '评级钮按目标档位命名（translation_history 评分对话框形制）：'
        '五档各自成名且带按钮角色', (tester) async {
      final semantics = tester.ensureSemantics();
      await pumpButton(
        tester,
        Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(
            5,
            (index) => SparkleIconButton(
              semanticLabel: zh.translationRateStar(index + 1),
              icon: const Icon(Icons.star),
              onPressed: () {},
              variant: ButtonVariant.ghost,
            ),
          ),
        ),
      );

      for (final value in [1, 2, 3, 4, 5]) {
        final handle = find.bySemanticsLabel(zh.translationRateStar(value));
        expect(handle, findsOneWidget);
        expect(
          tester.getSemantics(handle).flagsCollection.isButton,
          isTrue,
        );
      }
      semantics.dispose();
    });
  });
}
