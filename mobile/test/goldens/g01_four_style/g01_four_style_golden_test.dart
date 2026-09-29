// V4-G01 · 家族关键屏四风格确定性 golden 钉（CI 可失败）。
//
// 面 = 真实表面 + 确定性 seed（F05 判例）；比较 = B04 容差比较器
// （0.5% 分数口径带界，V3-FIX-383 钉死单位；跨机环境漂移实测 ~0.18%
// 落带内，真实回归 ≥0.6% 硬失败——「CI 可失败」由常态比对路径保证，
// 无 skip 门）。基线签发：`G01_GOLDEN_CAPTURE=true flutter test
// --update-goldens test/goldens/g01_four_style/`（仅基线机执行）。
//
// 钉面：首页 dashboard（RF-06 面、家族入口）+ 任务列表内容态，
// 各 × classic/paperDay/dusk/quiet 四档；remount 泵制与语义钉同源
// （g01_family_four_style_sweep_test 的 builder 口径）。
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show MethodChannel;
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/task/presentation/screens/task_list_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../../core/design/style_preview/style_preview_test_harness.dart';
import '../../features/home/dashboard_test_harness.dart';
import '../../goldens/b04_visual_baseline/b04_harness.dart'
    show b04InstallTolerantComparator;
import '../../shared/i18n_test_helper.dart';

const List<PixelPreviewProfile> _kProfiles = <PixelPreviewProfile>[
  PixelPreviewProfile.classic,
  PixelPreviewProfile.paperDay,
  PixelPreviewProfile.dusk,
  PixelPreviewProfile.quiet,
];

void main() {
  setUpAll(b04InstallTolerantComparator);
  setUp(setUpI18nForTesting);
  setUp(() {
    // 任务列表面 mount 时 auth 链读安全存储/连接状态——测试 binding 下
    // 打桩（u08 证据测试同款）：读令牌返回空，按离线路径降级，golden
    // 只钉渲染面。
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
      ..setMockMethodCallHandler(
        const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
        (call) async => null,
      )
      ..setMockMethodCallHandler(
        const MethodChannel('dev.fluttercommunity.plus/connectivity_status'),
        (call) async => null,
      );
  });

  Future<void> pumpProfiled(
    WidgetTester tester,
    PixelPreviewProfile profile,
    Widget Function() build,
  ) async {
    SharedPreferences.setMockInitialValues(const <String, Object>{});
    final manager = await freshThemeManager();
    if (profile != PixelPreviewProfile.classic) {
      await manager.setPixelPreviewProfile(profile);
    }
    await tester.pumpWidget(
      KeyedSubtree(
        key: ValueKey('g01-golden-${profile.name}'),
        child: build(),
      ),
    );
  }

  testWidgets('首页 dashboard × 四风格 golden（基线机签发，常态容差比对）',
      (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(780, 1688);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    for (final profile in _kProfiles) {
      await initializeDashboardTestEnvironment();
      await pumpProfiled(
        tester,
        profile,
        () => buildDashboardTestHarness(
          theme: AppThemes.lightTheme,
          extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
        ),
      );
      for (var i = 0; i < 8; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      expect(tester.takeException(), isNull, reason: '$profile 渲染异常');
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/g01_dashboard_${profile.name}.png'),
      );
    }
  });

  testWidgets('任务列表内容态 × 四风格 golden', (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(780, 1688);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    for (final profile in _kProfiles) {
      // auth 拦截链读共享偏好——mock 实例注入（guest_provider 契约面）。
      SharedPreferences.setMockInitialValues(const <String, Object>{});
      final prefs = await SharedPreferences.getInstance();
      await pumpProfiled(
        tester,
        profile,
        () => MaterialApp(
          theme: AppThemes.lightTheme,
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: ProviderScope(
            overrides: [
              // staticTaskListOverride 来自 dashboard harness（F-9 任务
              // 账本静态钉，与首页/既有任务测试同一 seed 管道）。
              staticTaskListOverride(_goldenTasks()),
              sharedPreferencesProvider.overrideWithValue(prefs),
            ],
            child: const TaskListScreen(),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 200));
      await tester.pump(const Duration(milliseconds: 500));
      expect(tester.takeException(), isNull, reason: '$profile 任务列表异常');
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/g01_task_list_${profile.name}.png'),
      );
    }
  });
}

List<TaskModel> _goldenTasks() {
  final now = DateTime(2026, 4, 8, 9);
  return [
    TaskModel(
      id: 'g01-golden-task-1',
      userId: 'user-1',
      title: '特征值专项练习',
      type: TaskType.learning,
      tags: const ['线性代数'],
      estimatedMinutes: 30,
      difficulty: 2,
      energyCost: 2,
      status: TaskStatus.pending,
      priority: 1,
      createdAt: now,
      updatedAt: now,
      dueDate: now,
    ),
  ];
}
