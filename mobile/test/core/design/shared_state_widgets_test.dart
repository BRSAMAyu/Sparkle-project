import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/components/atoms/ai_status_capsule.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/materials.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  group('shared state widgets', () {
    testWidgets('EmptyState renders in light and dark with large text', (
      tester,
    ) async {
      for (final brightness in [Brightness.light, Brightness.dark]) {
        await tester.pumpWidget(
          _TestShell(
            brightness: brightness,
            disableAnimations: true,
            textScaleFactor: 1.4,
            child: EmptyState.noTasks(
              onCreateTask: () {},
            ),
          ),
        );

        await tester.pump();
        expect(find.byType(EmptyState), findsOneWidget);
        expect(find.byIcon(Icons.task_alt_rounded), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
    });

    testWidgets(
        'shimmer skeleton (ListItemSkeleton) disables shimmer when reduce motion is on',
        (tester) async {
      // U-01 Step 0：骨架家族收敛到 sparkle_skeleton.dart 后，本用例改为直接
      // 泵入 shimmer 骨架 owner 处的 ListItemSkeleton，reduce-motion 语义不变。
      await tester.pumpWidget(
        const _TestShell(
          disableAnimations: true,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [ListItemSkeleton(), ListItemSkeleton()],
          ),
        ),
      );

      await tester.pump();
      expect(find.byType(ListItemSkeleton), findsNWidgets(2));
      expect(find.byType(Shimmer), findsNothing);
      expect(tester.takeException(), isNull);
    });

    testWidgets('CustomErrorWidget retry action remains functional', (
      tester,
    ) async {
      var retried = false;

      await tester.pumpWidget(
        _TestShell(
          disableAnimations: true,
          // 文案演进适配：l10n 由工厂构造注入（.page/.banner/.inline），
          // 默认构造 l10n=null 会走英文兜底 'Retry'，断言找 '重试' 落空。
          // 用 Builder 拿 MaterialApp 下的 context，走产品注入正路。
          child: Builder(
            builder: (context) => CustomErrorWidget.page(
              message: '网络连接失败',
              context: context,
              onRetry: () => retried = true,
            ),
          ),
        ),
      );

      await tester.pump();
      await tester.tap(find.text('重试'));
      await tester.pump();

      expect(retried, isTrue);
      expect(tester.takeException(), isNull);
    });

    testWidgets(
        'CustomErrorWidget default constructor resolves zh retry from context', (
      tester,
    ) async {
      // l10n 债项：默认构造 l10n=null 原先静默走英文硬编码兜底（'Retry'），
      // 不走 .page 工厂的调用点（如 main.dart ErrorWidget.builder）在中文
      // 环境拿到英文文案。修复后 build 时从 context 兜底解析 l10n。
      // 复刻 main.dart 真实用法：默认构造 + ErrorType.page（重试按钮可见）。
      var retried = false;

      await tester.pumpWidget(
        _TestShell(
          disableAnimations: true,
          child: CustomErrorWidget(
            type: ErrorType.page,
            message: '网络连接失败',
            onRetry: () => retried = true,
          ),
        ),
      );

      await tester.pump();
      expect(find.text('重试'), findsOneWidget);
      expect(find.text('Retry'), findsNothing);
      await tester.tap(find.text('重试'));
      await tester.pump();
      expect(retried, isTrue);
      expect(tester.takeException(), isNull);
    });

    testWidgets('shared theme-aware components update in system mode', (
      tester,
    ) async {
      tester.platformDispatcher.platformBrightnessTestValue = Brightness.light;
      addTearDown(tester.platformDispatcher.clearPlatformBrightnessTestValue);

      await tester.pumpWidget(const _SystemThemeComponentsShell());
      await tester.pumpAndSettle();

      expect(find.text('theme:light'), findsOneWidget);

      final lightButtonColor = _materialColor(
        tester,
        ancestorKey: const Key('sparkle-button'),
      );
      final lightCapsuleColor = _materialColor(
        tester,
        ancestorKey: const Key('status-capsule'),
      );
      final lightSurfaceColor = _decoratedContainerColor(
        tester,
        ancestorKey: const Key('material-styler'),
      );

      tester.platformDispatcher.platformBrightnessTestValue = Brightness.dark;
      tester.binding.handlePlatformBrightnessChanged();
      await tester.pumpAndSettle();

      expect(find.text('theme:dark'), findsOneWidget);

      final darkButtonColor = _materialColor(
        tester,
        ancestorKey: const Key('sparkle-button'),
      );
      final darkCapsuleColor = _materialColor(
        tester,
        ancestorKey: const Key('status-capsule'),
      );
      final darkSurfaceColor = _decoratedContainerColor(
        tester,
        ancestorKey: const Key('material-styler'),
      );

      expect(darkButtonColor, isNot(equals(lightButtonColor)));
      expect(darkCapsuleColor, isNot(equals(lightCapsuleColor)));
      expect(darkSurfaceColor, isNot(equals(lightSurfaceColor)));
      expect(tester.takeException(), isNull);
    });
  });

  group('CompactEmptyState U-01 Step 3 extensions', () {
    testWidgets('description renders as tertiary hint under message',
        (tester) async {
      await tester.pumpWidget(
        const _TestShell(
          disableAnimations: true,
          child: CompactEmptyState(
            message: '暂无记录',
            description: '先去创建第一条吧',
          ),
        ),
      );

      expect(find.text('暂无记录'), findsOneWidget);
      expect(find.text('先去创建第一条吧'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('iconSize overrides default 64 for compact inline empty states',
        (tester) async {
      await tester.pumpWidget(
        const _TestShell(
          disableAnimations: true,
          child: CompactEmptyState(
            message: '暂无记录',
            icon: Icons.history_toggle_off,
            iconSize: 36,
          ),
        ),
      );

      final icon = tester.widget<Icon>(find.byType(Icon));
      expect(icon.size, 36);
      expect(icon.icon, Icons.history_toggle_off);
      expect(tester.takeException(), isNull);
    });

    testWidgets('defaults stay unchanged (64px icon, no description row)',
        (tester) async {
      await tester.pumpWidget(
        const _TestShell(
          disableAnimations: true,
          child: CompactEmptyState(message: '暂无记录', icon: Icons.inbox),
        ),
      );

      final icon = tester.widget<Icon>(find.byType(Icon));
      expect(icon.size, 64);
      expect(find.byType(Icon), findsOneWidget);
      expect(find.byType(SparkleButton), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });
}

Color? _materialColor(WidgetTester tester, {required Key ancestorKey}) => tester
    .widget<Material>(
      find
          .descendant(
            of: find.byKey(ancestorKey),
            matching: find.byType(Material),
          )
          .first,
    )
    .color;

Color? _decoratedContainerColor(WidgetTester tester,
    {required Key ancestorKey}) {
  final container = tester.widget<Container>(
    find
        .descendant(
          of: find.byKey(ancestorKey),
          matching: find.byWidgetPredicate(
            (widget) =>
                widget is Container &&
                widget.decoration is BoxDecoration &&
                (widget.decoration as BoxDecoration).color != null,
          ),
        )
        .first,
  );

  return (container.decoration! as BoxDecoration).color;
}

class _TestShell extends StatelessWidget {
  const _TestShell({
    required this.child,
    this.brightness = Brightness.light,
    this.disableAnimations = false,
    this.textScaleFactor = 1.0,
  });

  final Widget child;
  final Brightness brightness;
  final bool disableAnimations;
  final double textScaleFactor;

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQueryData(
      platformBrightness: brightness,
      disableAnimations: disableAnimations,
      boldText: textScaleFactor >= 1.3,
      textScaler: TextScaler.linear(textScaleFactor),
    );

    return MaterialApp(
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      themeMode:
          brightness == Brightness.dark ? ThemeMode.dark : ThemeMode.light,
      // U-03 harness repair：不钉 locale 时测试环境默认 en，
      // CustomErrorWidget 的 l10n 重试按钮渲染 'Retry'，断言找 '重试' 落空。
      locale: const Locale('zh'),
      localizationsDelegates: const [
        ...AppLocalizations.localizationsDelegates,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: MediaQuery(
        data: mediaQuery,
        child: Scaffold(body: Center(child: child)),
      ),
    );
  }
}

class _SystemThemeComponentsShell extends StatelessWidget {
  const _SystemThemeComponentsShell();

  @override
  Widget build(BuildContext context) => MaterialApp(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        themeMode: ThemeMode.system,
        home: Builder(
          builder: (context) => Scaffold(
            body: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('theme:${Theme.of(context).brightness.name}'),
                SparkleButton(
                  key: const Key('sparkle-button'),
                  label: 'Action',
                  variant: ButtonVariant.ghost,
                  onPressed: () {},
                ),
                const SizedBox(height: 12),
                const AiStatusCapsule(
                  key: Key('status-capsule'),
                  label: 'Online',
                ),
                const SizedBox(height: 12),
                MaterialStyler(
                  key: const Key('material-styler'),
                  material: AppMaterials.ceramic(context),
                  child: const SizedBox(width: 80, height: 32),
                ),
              ],
            ),
          ),
        ),
      );
}
