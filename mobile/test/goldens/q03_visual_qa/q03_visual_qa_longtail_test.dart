/// Q-03 Autonomous Visual QA — long-tail reachable 屏逐屏截图（wt401）。
///
/// 全部走真实 GoRouter（demo mode），每屏跑布局探针并落 golden（capture 模式）。
/// 分 5 组隔离：单组失败不影响其余组证据产出。
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/performance_service.dart';

import 'q03_harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() async {
    await q03LoadRealFont();
    await q03EnsureTestStorage();
  });

  tearDownAll(() async {
    await q03FlushProbeReports('longtail');
  });

  group('Q03 visual QA: long-tail cluster 1 (auth + plan/task)', () {
    testWidgets('L01-L09 auth + task surfaces', (tester) async {
      final harness = await pumpQ03App(tester);
      harness.router.go('/register');
      await harness.pumpFrames(tester);
      await harness.capture(tester, 'L01_register', 'default');

      harness.router.go('/forgot-password');
      await harness.pumpFrames(tester);
      await harness.capture(tester, 'L02_forgot_password', 'default');

      harness.router.go('/reset-password');
      await harness.pumpFrames(tester);
      await harness.capture(tester, 'L03_reset_password', 'default');

      harness.router.go('/legal/terms');
      await harness.pumpFrames(tester);
      await harness.capture(tester, 'L04_legal_terms', 'default');

      harness.router.go('/legal/privacy');
      await harness.pumpFrames(tester);
      await harness.capture(tester, 'L05_legal_privacy', 'default');

      DemoDataService.isDemoMode = true;
      harness.router.go('/focus');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L06_focus', 'default');

      harness.router.go('/tasks');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L07_tasks', 'default');

      harness.router.go('/tasks/new');
      await harness.pumpFrames(tester);
      await harness.capture(tester, 'L08_task_new', 'default');

      harness.router.go('/openclaw');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L09_openclaw', 'default');
      PerformanceService.instance.stopMonitoring();

      await harness.dispose(tester);
    });

    testWidgets('L10-L21 calendar + sprint + exam-sprint', (tester) async {
      DemoDataService.isDemoMode = true;
      final harness = await pumpQ03App(tester);

      harness.router.go('/calendar?date=2026-03-06T00:00:00.000');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L10_calendar', 'default');

      harness.router.go('/calendar-stats?date=2026-03-07T00:00:00.000');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L11_calendar_stats', 'default');

      harness.router.go('/calendar/day?date=2026-03-08T00:00:00.000');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L12_calendar_day', 'default');

      harness.router.go('/sprint');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L13_sprint', 'default');

      harness.router.go('/sprint/history');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L14_sprint_history', 'default');

      harness.router.go('/growth');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L15_growth', 'default');

      harness.router.go('/plans/history');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L16_plans_history', 'default');

      harness.router.go('/exam-sprint/setup');
      await harness.pumpFrames(tester);
      await harness.capture(tester, 'L17_exam_sprint_setup', 'default');

      harness.router.go('/exam-sprint/diagnose');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L18_exam_sprint_diagnose', 'default');

      harness.router.go('/exam-sprint/review');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L19_exam_sprint_review', 'default');

      harness.router.go('/exam-sprint/completion');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L20_exam_sprint_completion', 'default');

      harness.router.go('/exam-sprint/portfolio');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L21_exam_sprint_portfolio', 'default');

      await harness.dispose(tester);
    });
  });

  group('Q03 visual QA: long-tail cluster 2 (insights + review + memory)', () {
    testWidgets('L22-L30 insights/report/review/reflection', (tester) async {
      DemoDataService.isDemoMode = true;
      final harness = await pumpQ03App(tester);

      const insightsRoutes = <String, String>{
        '/learning/insights': 'L22_learning_insights',
        '/learning/forecast': 'L23_learning_forecast',
        '/learning/insights/growth-chronicle': 'L24_growth_chronicle',
        '/learning/insights/dashboard': 'L25_insights_dashboard',
        '/learning/insights/directives': 'L26_directive_audit',
        '/learning-path': 'L27_learning_path',
        '/learning-report': 'L28_learning_report',
        '/review-plan': 'L29_review_plan_hub',
        '/reflection/summary': 'L30_reflection_summary',
      };
      for (final entry in insightsRoutes.entries) {
        harness.router.go(entry.key);
        await harness.pumpFrames(tester, 10);
        await harness.capture(tester, entry.value, 'default');
      }

      await harness.dispose(tester);
    });

    testWidgets('L31-L33 memory surfaces', (tester) async {
      DemoDataService.isDemoMode = true;
      final harness = await pumpQ03App(tester);

      harness.router.go('/memory');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L31_memory_panel', 'default');

      harness.router.go('/memory/settings');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L32_memory_settings', 'default');

      harness.router.go('/memory/understanding');
      await harness.pumpFrames(tester, 10);
      await harness.capture(tester, 'L33_memory_understanding', 'default');

      await harness.dispose(tester);
    });
  });

  group('Q03 visual QA: long-tail cluster 3 (profile family)', () {
    testWidgets('L34-L45 profile sub-screens', (tester) async {
      DemoDataService.isDemoMode = true;
      final harness = await pumpQ03App(tester);

      const profileRoutes = <String, String>{
        '/profile/edit': 'L34_profile_edit',
        '/profile/settings': 'L35_profile_settings',
        '/profile/music-library': 'L36_music_library',
        '/profile/persona': 'L37_profile_persona',
        '/profile/posters': 'L38_poster_studio',
        '/profile/system-updates': 'L39_system_updates',
        '/profile/memory-settings': 'L40_profile_memory_settings',
        '/profile/openclaw-settings': 'L41_openclaw_settings',
        '/profile/sync-center': 'L42_sync_center',
        '/profile/sessions': 'L43_session_management',
        '/profile/security-log': 'L44_security_log',
        '/profile/export-data': 'L45_export_data',
      };
      for (final entry in profileRoutes.entries) {
        harness.router.go(entry.key);
        await harness.pumpFrames(tester, 10);
        await harness.capture(tester, entry.value, 'default');
      }

      await harness.dispose(tester);
    });
  });

  group('Q03 visual QA: long-tail cluster 4 (achievement + community)', () {
    testWidgets('L46-L50 achievements + self anchor', (tester) async {
      DemoDataService.isDemoMode = true;
      final harness = await pumpQ03App(tester);

      const routes = <String, String>{
        '/achievements': 'L46_achievements',
        '/achievements/map': 'L47_achievements_map',
        '/achievements/streak': 'L48_streak_details',
        '/achievements/contract': 'L49_achievement_contract',
        '/leaderboards/self-anchor': 'L50_self_anchor',
      };
      for (final entry in routes.entries) {
        harness.router.go(entry.key);
        await harness.pumpFrames(tester, 10);
        await harness.capture(tester, entry.value, 'default');
      }

      await harness.dispose(tester);
    });

    testWidgets('L51-L64 community sub-screens', (tester) async {
      DemoDataService.isDemoMode = true;
      final harness = await pumpQ03App(tester);

      const routes = <String, String>{
        '/community/feed': 'L51_community_feed',
        '/community/friends': 'L52_friends',
        '/community/friends/requests': 'L53_friend_requests',
        '/community/friends/discover': 'L54_friends_discover',
        '/community/users/search': 'L55_user_search',
        '/community/groups': 'L56_groups',
        '/community/groups/search': 'L57_group_search',
        '/community/groups/discover': 'L58_groups_discover',
        '/community/groups/create': 'L59_group_create',
        '/community/posts/create': 'L60_post_create',
        '/community/favorites': 'L61_favorites',
        '/community/blocked': 'L62_blocked_users',
        '/community/accountability': 'L63_accountability',
        '/community/squads': 'L64_squads',
      };
      for (final entry in routes.entries) {
        harness.router.go(entry.key);
        await harness.pumpFrames(tester, 10);
        await harness.capture(tester, entry.value, 'default');
      }

      await harness.dispose(tester);
    });
  });

  group('Q03 visual QA: long-tail cluster 5 (tools + shops + params)', () {
    testWidgets('L65-L78 tools/cognitive/photon/seed/shop/visual/theater etc',
        (tester) async {
      DemoDataService.isDemoMode = true;
      final harness = await pumpQ03App(tester);

      const routes = <String, String>{
        '/curiosity-capsule': 'L65_curiosity_capsule',
        '/cognitive/patterns': 'L66_cognitive_patterns',
        '/tools/library': 'L67_tools_library',
        '/tools/translator?context=home': 'L68_tool_host_translator',
        '/photon/history': 'L69_photon_history',
        '/seed-libraries': 'L70_seed_libraries',
        '/seed-libraries/marketplace': 'L71_seed_marketplace',
        '/shop': 'L72_shop',
        '/visual-elements': 'L73_visual_elements',
        '/theater': 'L74_theater',
        '/simulation': 'L75_simulation',
        '/documents': 'L76_documents',
        '/translations/history': 'L77_translation_history',
        '/weather': 'L78_weather_guide',
      };
      for (final entry in routes.entries) {
        harness.router.go(entry.key);
        await harness.pumpFrames(tester, 10);
        await harness.capture(tester, entry.value, 'default');
      }
      PerformanceService.instance.stopMonitoring();

      await harness.dispose(tester);
    });

    testWidgets('L79-L85 param screens with demo/unknown ids', (tester) async {
      DemoDataService.isDemoMode = true;
      final harness = await pumpQ03App(tester);

      const routes = <String, String>{
        '/memory/detail?q=q03-demo': 'L79_memory_detail',
        '/galaxy/drafts/review': 'L80_galaxy_draft_review',
        '/errors/q03-demo-error': 'L81_error_detail_unknown_id',
        '/goals/q03-demo-goal': 'L82_goal_detail_unknown_id',
        '/tasks/q03-demo-task': 'L83_task_detail_unknown_id',
        '/community/groups/q03-demo-group': 'L84_group_detail_unknown_id',
        '/community/users/q03-demo-user': 'L85_user_profile_unknown_id',
      };
      for (final entry in routes.entries) {
        harness.router.go(entry.key);
        await harness.pumpFrames(tester, 10);
        await harness.capture(tester, entry.value, 'default');
      }
      PerformanceService.instance.stopMonitoring();

      await harness.dispose(tester);
    });
  });
}
