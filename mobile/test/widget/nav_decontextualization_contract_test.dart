import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/features/leaderboard/leaderboard_routes.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/tool_registry.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

import '../shared/i18n_test_helper.dart';

/// U-07 长尾 Feature 导航减负——导航契约钉（navigation contract pins）。
///
/// 卡面验收：
/// - 五 Tab 不增加；
/// - CORE journey 不出现无关 feature 入口（LABS: theater/simulation/
///   seed_library/visual_elements 按 portfolio 为 hidden by default）；
/// - HIDDEN 用户不可达（leaderboard 全站榜按 D-COMM-1 不建路由，仅自我锚）；
/// - CONTEXTUAL 有至少一个自然 journey（计划详情 → 日历；任务执行 → 专注；
///   星图节点 → 知识详情——后两者由既有测试覆盖，本文件钉计划→日历）。
///
/// 形制先例：a11y_batch2_domain_labels_guard_test / UX-COMP 的源码扫描钉 +
/// 直接单元断言混合形制。路由挂载（app/routes.dart 权威真源）零改动——
/// LABS 走 unlisted：不删路由与功能文件，只摘 CORE 面入口。
void main() {
  setUp(setUpI18nForTesting);

  group('U-07 navigation contract', () {
    test('shell keeps exactly five bottom tabs', () {
      final source = File(
        'lib/core/navigation/shell_navigation.dart',
      ).readAsStringSync();
      final count = 'NavigationDestination('.allMatches(source).length;
      expect(count, 5, reason: '五 Tab 铁律：底部目的地数量不得增减');
    });

    test('tool registry exposes no LABS tools or LABS route aliases', () {
      expect(
        ToolRegistry.tryGetById('seed_library'),
        isNull,
        reason: 'seed_library 属 LABS，不得出现在工具库/搜索/首页工具枢纽',
      );
      const labsPrefixes = <String>[
        '/theater',
        '/simulation',
        '/seed-libraries',
        '/visual-elements',
      ];
      for (final tool in ToolRegistry.all) {
        final builder = tool.routeBuilder;
        if (builder == null) continue;
        final resolved = builder(
          const ToolLaunchRequest(
            context: ToolLaunchContext.home,
            surface: ToolSurface.page,
          ),
        );
        for (final prefix in labsPrefixes) {
          expect(
            resolved.startsWith(prefix),
            isFalse,
            reason: '工具 ${tool.id} 的路由别名不得指向 LABS 面 $prefix',
          );
        }
      }    });

    test('leaderboard stays HIDDEN: self-anchor is the only routed surface',
        () {
      final routes = LeaderboardRoutes.routes;
      expect(routes, hasLength(1));
      final route = routes.single;
      expect(route, isA<GoRoute>());
      expect((route as GoRoute).path, '/leaderboards/self-anchor');
      expect(
        LeaderboardRoutes.selfAnchor,
        startsWith('/leaderboards/self-anchor'),
        reason: 'D-COMM-1：全站综合榜不建路由，自我锚是唯一裁决路由面',
      );
    });

    test('CORE surfaces carry zero LABS entry references', () {
      const coreSurfaces = <String>[
        'lib/features/home/presentation/widgets/recent_insights_card.dart',
        'lib/features/home/presentation/widgets/insight_hub_card.dart',
        'lib/features/insights/presentation/screens/learning_insights_overview_screen.dart',
        'lib/features/report/presentation/screens/learning_report_screen.dart',
        'lib/features/chat/presentation/widgets/chat_bubble.dart',
        'lib/features/chat/presentation/screens/chat_settings_screen.dart',
        'lib/features/user/presentation/screens/profile_screen.dart',
        'lib/features/user/presentation/screens/unified_settings_screen.dart',
        'lib/features/tools/tool_registry.dart',
      ];
      const forbiddenTokens = <String>[
        'TheaterRoutes',
        'SimulationRoutes',
        'SeedLibraryRoutes',
        'VisualElementsRoutes',
        "push('/theater')",
        "push('/simulation')",
        'context.push(\'/seed-libraries\')',
      ];
      for (final path in coreSurfaces) {
        final source = File(path).readAsStringSync();
        for (final token in forbiddenTokens) {
          expect(
            source.contains(token),
            isFalse,
            reason: 'CORE 面 $path 不得包含 LABS 入口引用 $token',
          );
        }
      }
    });

    test('plan detail keeps a contextual calendar CTA (natural journey)', () {
      final source = File(
        'lib/features/plan/presentation/screens/plan_detail_screen.dart',
      ).readAsStringSync();
      expect(
        source.contains('CalendarRoutes.calendar'),
        isTrue,
        reason: '计划详情的时间摆位语境必须能 1 跳进入日历（CONTEXTUAL 自然 journey）',
      );
      expect(
        source.contains('calendarTitle'),
        isTrue,
        reason: '日历 CTA 语义标签复用既有 calendarTitle 权威文案',
      );
    });

    testWidgets(
        'galaxy node preview card hides the theater entry by default',
        (tester) async {
      await tester.pumpWidget(
        testMaterialApp(
          home: Scaffold(
            body: GalaxyNodePreviewCard(
              node: GalaxyNodeModel(
                id: 'node-1',
                name: '线性代数',
                importance: 80,
                sector: SectorEnum.wisdom,
                isUnlocked: true,
                masteryScore: 42,
              ),
              onFocus: () {},
              onInspectConnections: () {},
              onViewDetails: () {},
              onStartReview: () {},
              // onLaunchPrediction 缺省（null）= LABS 演练入口不挂载。
            ),
          ),
        ),
      );

      await tester.pump();
      expect(
        find.textContaining('推演'),
        findsNothing,
        reason: '节点预览卡常驻动作只留聚焦/连线/详情/复习，theater 属 LABS',
      );
    });
  });
}
