import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/goal/presentation/screens/goal_creation_wizard_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/main.dart' as app;

/// J-01 First-3-Minutes measurement driver (measurement infrastructure —
/// product code is NOT modified by this card).
///
/// Drives the real macOS app against the REAL backend through the fresh-user
/// first-3-minutes journey for 5 personas (from
/// v3/01_product/USER_SEGMENTS_AND_JTBD.md), in one of two routes selected
/// via --dart-define=J01_ROUTE:
///
///  own_goal — TWO legs per persona, both as a real new user:
///    leg A "guest reality":  splash -> login -> guest -> dashboard, then
///      record what the first screen actually offers (finding measured, not
///      assumed: the backend seeds every new guest with a demo goal via
///      guest_seed_service.py, so the set-first-goal CTA may not exist).
///    leg B "register + own goal": logout -> register a fresh account ->
///      dashboard -> set-first-goal CTA -> goal wizard (real AI intent
///      analysis) -> create goal.
///
///  example — splash -> login -> guest -> dashboard, then scan every shell
///    tab for any DECLARED "experience an example" surface (FIRST_3_MINUTES
///    requires a persistent 示例体验 marker). The run itself must be compiled
///    with DEMO_MODE=true because no UI entry exists — that dependency is a
///    finding.
///
/// HONESTY RULES (card J-01):
///  * All timings are real wall-clock (DateTime.now() while the live app
///    renders real frames under fullyLive frame policy). No fake clocks,
///    no invented numbers.
///  * Pass 1 of each process is a true cold start (secure storage +
///    SharedPreferences cleared before app.main()). Passes 2-5 reset state
///    in-process (logout + secure-storage wipe + prefs.clear) — these are
///    WARM-process fresh-state passes and labelled as such.
///  * Product behaviours are recorded as findings; only harness breakage is
///    a failure.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized()
    ..framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  const route = String.fromEnvironment('J01_ROUTE', defaultValue: 'own_goal');
  const shotDestEnv = String.fromEnvironment('J01_SHOT_DEST');
  final shotDest = shotDestEnv.isNotEmpty
      ? shotDestEnv
      : '${Directory.current.path.endsWith('mobile') ? Directory.current.parent.path : Directory.current.path}/v3-output/J01/evidence';

  // 5 personas from v3/01_product/USER_SEGMENTS_AND_JTBD.md (5 Builder
  // personas). backend persona.py is a seeded 3-arc population generator
  // (stalled/deadline/completion), not 10 named personas — the arc mapping
  // recorded here is documented in the J-01 report.
  const personas = <Map<String, String>>[
    {
      'id': 'PX1',
      'name': '比赛 Builder',
      'arc': 'deadline',
      'goal': '两周内做出一个可展示的算法可视化比赛作品，至少能完整跑起来给评委演示。',
    },
    {
      'id': 'PX2',
      'name': '科研 Builder',
      'arc': 'stalled',
      'goal': '推进毕业论文：两周内跑完实验并写出前三节初稿。',
    },
    {
      'id': 'PX3',
      'name': '作品集 Builder',
      'arc': 'stalled',
      'goal': '边学 React 边做出 3 个能放进作品集的前端项目。',
    },
    {
      'id': 'PX4',
      'name': '课程 Builder',
      'arc': 'deadline',
      'goal': '7天后《计算机网络》期末考试，目前基本没学，目标是别挂科。',
    },
    {
      'id': 'PX5',
      'name': 'Creator',
      'arc': 'completion',
      'goal': '持续产出学习类播客，第一个月先发出 2 期。',
    },
  ];

  // J01_PASS: '0'-'4' -> run that single persona (own_goal: one TRUE cold
  // start per process, one process per persona); 'all' -> run all 5 in a
  // loop (example route, UI logout between passes).
  const passParam = String.fromEnvironment('J01_PASS', defaultValue: 'all');

  final harnessT0 = DateTime.now();
  final failures = <String>[];
  final allPasses = <Map<String, dynamic>>[];

  late WidgetTester testTester;

  Future<void> shot(String relName) async {
    final dest = '$shotDest/$relName';
    try {
      await testTester.runAsync(() async {
        RenderObject root;
        try {
          root = WidgetsBinding.instance.renderViews.first;
        } catch (_) {
          root = RendererBinding.instance.renderViews.first;
        }
        RenderRepaintBoundary? boundary;
        void walk(RenderObject ro) {
          if (boundary != null) return;
          if (ro is RenderRepaintBoundary) {
            boundary = ro;
            return;
          }
          ro.visitChildren(walk);
        }

        walk(root);
        if (boundary == null) throw StateError('no RepaintBoundary in tree');
        final image = await boundary!.toImage(pixelRatio: 2.0);
        final data = await image.toByteData(format: ui.ImageByteFormat.png);
        if (data == null) throw StateError('null png bytes');
        File(dest)
          ..createSync(recursive: true)
          ..writeAsBytesSync(data.buffer.asUint8List(), flush: true);
      });
      // ignore: avoid_print
      print('J01_SHOT $relName ok bytes=${File(dest).lengthSync()}');
    } catch (e) {
      // ignore: avoid_print
      print('J01_SHOT_FAIL $relName: $e');
      failures.add('screenshot $relName failed: $e');
    }
  }

  void mark(String passId, String leg, String name, DateTime passT0) {
    final now = DateTime.now();
    // ignore: avoid_print
    print('J01_MARK pass=$passId leg=$leg mark=$name '
        'ms_since_harness_t0=${now.difference(harnessT0).inMilliseconds} '
        'ms_since_pass_t0=${now.difference(passT0).inMilliseconds} '
        'clicks=${clicks[0]}');
  }

  Future<void> wipeLocalState() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    const secure = FlutterSecureStorage(
      mOptions: MacOsOptions(useDataProtectionKeyChain: false),
    );
    await secure.deleteAll();
  }

  testWidgets('J01 first-3-minutes measurement ($route)', (tester) async {
    testTester = tester;
    final originalOnError = FlutterError.onError;
    final originalPlatformOnError = ui.PlatformDispatcher.instance.onError;
    final originalErrorWidgetBuilder = ErrorWidget.builder;

    // ---- PASS 1 prep: true fresh-install semantics (pass 1 cold start) ----
    try {
      await wipeLocalState();
      // ignore: avoid_print
      print('J01 prefs+secure storage cleared (clean-install state)');
    } catch (e) {
      // ignore: avoid_print
      print('J01 local state wipe failed: $e');
    }

    app.main();
    unawaited(BgmService.setEnabled(false).timeout(const Duration(seconds: 3)));
    unawaited(BgmService.stop().timeout(const Duration(seconds: 3)));

    final selected = passParam == 'all'
        ? List<int>.generate(personas.length, (i) => i)
        : <int>[int.parse(passParam)];
    try {
      for (final i in selected) {
        final persona = personas[i];
        final passId = persona['id']!;
        final warm = passParam == 'all' && i > selected.first;
        final passData = <String, dynamic>{
          'persona': persona,
          'route': route,
          'warm_process': warm,
        };
        clicks[0] = 0;
        final passT0 = DateTime.now();
        mark(
          passId,
          '-',
          warm ? 't_pass_start_warm' : 't_pass_start_cold',
          passT0,
        );
        try {
          if (warm) {
            // WARM reset (instrumentation, not user path).
            try {
              final container = ProviderScope.containerOf(
                tester.element(find.byType(MaterialApp).first),
              );
              await container.read(authProvider.notifier).logout();
            } catch (e) {
              failures.add('pass $passId warm logout failed: $e');
            }
            await wipeLocalState();
          }

          // ---- reach first actionable surface ----
          final splashOrLogin = await waitUntil(
            tester,
            () =>
                find.byType(LoginScreen).evaluate().isNotEmpty ||
                find.byType(DashboardScreen).evaluate().isNotEmpty ||
                // Warm reset may land on another public auth page (e.g. the
                // register screen the previous leg failed on).
                find.text('已有账号？').evaluate().isNotEmpty,
            timeout: const Duration(seconds: 90),
          );
          passData['t_first_surface_ms'] =
              DateTime.now().difference(passT0).inMilliseconds;
          mark(passId, '-', 't_first_surface', passT0);
          if (!splashOrLogin) {
            failures.add('pass $passId: never reached login/dashboard');
          }
          await safeSettle(tester);
          await shot('$passId/01-first-surface.png');

          // Land on a public auth page other than login (e.g. register from
          // a failed previous leg) → walk back to login first.
          if (find.text('已有账号？').evaluate().isNotEmpty &&
              find.byType(LoginScreen).evaluate().isEmpty) {
            final backLink = textAny(['已有账号？']);
            if (backLink != null) {
              clicks[0]++;
              await tester.tap(backLink, warnIfMissed: false);
              await waitUntil(
                tester,
                () => find.byType(LoginScreen).evaluate().isNotEmpty,
                timeout: const Duration(seconds: 20),
              );
            }
          }

          // Auto-login despite the wipe is a REAL measured behaviour (auth
          // token survives best-effort local wipe) — record it as a finding,
          // then walk the product logout path so the pass still starts at
          // login like a true first-run user.
          final sawLogin = find.byType(LoginScreen).evaluate().isNotEmpty;
          passData['saw_login'] = sawLogin;
          if (!sawLogin &&
              find.byType(DashboardScreen).evaluate().isNotEmpty) {
            passData['auto_login_after_wipe'] = true;
            // ignore: avoid_print
            print(
                'J01_FINDING pass=$passId auto-login after secure-storage+prefs wipe');
            try {
              final container = ProviderScope.containerOf(
                tester.element(find.byType(MaterialApp).first),
              );
              await container.read(authProvider.notifier).logout();
            } catch (e) {
              failures.add('pass $passId: post-auto-login logout failed: $e');
            }
            final backAtLogin = await waitUntil(
              tester,
              () => find.byType(LoginScreen).evaluate().isNotEmpty,
              timeout: const Duration(seconds: 30),
            );
            if (!backAtLogin) {
              failures.add(
                'pass $passId: logout after auto-login did not reach login',
              );
            }
            passData['t_first_surface_ms'] =
                DateTime.now().difference(passT0).inMilliseconds;
            await safeSettle(tester);
            await shot('$passId/01b-after-logout.png');
          }

          // Probe: does login offer any "example" entry? (FIRST_3_MINUTES
          // target design: secondary CTA 体验一个示例)
          passData['example_entry_on_login'] =
              textAny(['体验一个示例', '体验示例', '示例体验', 'Try an example']) != null;

          if (route == 'example') {
            await _exampleRoute(
              tester: tester,
              passId: passId,
              passT0: passT0,
              passData: passData,
              shot: shot,
              mark: mark,
              textAny: textAny,
            );
          } else {
            await _ownGoalRoute(
              tester: tester,
              passId: passId,
              persona: persona,
              passT0: passT0,
              passData: passData,
              shot: shot,
              mark: mark,
              textAny: textAny,
              failures: failures,
            );
          }
        } catch (e, st) {
          failures.add('pass $passId aborted: $e');
          // ignore: avoid_print
          print('J01 pass $passId fatal: $e\n$st');
          try {
            await shot('$passId/99-fatal-state.png');
          } catch (_) {}
        }
        // Example route loops personas in-process: walk the PRODUCT logout
        // path (Profile -> 退出登录 -> confirm) to return to login.
        if (passParam == 'all' && i != selected.last) {
          try {
            final profileTab = textAny(['我的', 'Profile']);
            if (profileTab != null) {
              clicks[0]++;
              await tester.tap(profileTab, warnIfMissed: false);
              await safeSettle(tester);
              await tester.pump(const Duration(seconds: 1));
            }
            final logoutRow = textAny(['退出登录', 'Logout']);
            if (logoutRow != null) {
              try {
                await tester.scrollUntilVisible(
                  logoutRow,
                  160,
                  scrollable: find.byType(Scrollable).first,
                );
              } catch (_) {
                try {
                  await tester.ensureVisible(logoutRow);
                } catch (_) {}
              }
              clicks[0]++;
              await tester.tap(logoutRow, warnIfMissed: false);
              final dialog = await waitUntil(
                tester,
                () => find
                        .textContaining('退出登录')
                        .evaluate()
                        .length >
                    1 ||
                    find.textContaining('sure').evaluate().isNotEmpty,
                timeout: const Duration(seconds: 15),
              );
              if (dialog) {
                final confirmBtn = textAny(['确定', 'Confirm', '退出']);
                if (confirmBtn != null) {
                  clicks[0]++;
                  await tester.tap(confirmBtn, warnIfMissed: false);
                }
              }
              await waitUntil(
                tester,
                () => find.byType(LoginScreen).evaluate().isNotEmpty,
                timeout: const Duration(seconds: 20),
              );
            }
          } catch (e) {
            // ignore: avoid_print
            print('J01_DEBUG pass=$passId ui logout failed: $e');
          }
        }
        passData['clicks'] = clicks[0];
        allPasses.add(passData);
      }
    } finally {
      try {
        await BgmService.dispose().timeout(const Duration(seconds: 3));
      } catch (_) {}
      try {
        await SensoryFeedbackService.dispose()
            .timeout(const Duration(seconds: 3));
      } catch (_) {}
      FlutterError.onError = originalOnError;
      ui.PlatformDispatcher.instance.onError = originalPlatformOnError;
      ErrorWidget.builder = originalErrorWidgetBuilder;
    }

    final summary = {
      'route': route,
      'harness_t0': harnessT0.toIso8601String(),
      'finished_at': DateTime.now().toIso8601String(),
      'passes': allPasses,
      'failures': failures,
    };
    // ignore: avoid_print
    print('J01_SUMMARY ${jsonEncode(summary)}');
    try {
      await tester.runAsync(() async {
        File('$shotDest/j01_timings_$route.json')
          ..createSync(recursive: true)
          ..writeAsStringSync(
            const JsonEncoder.withIndent('  ').convert(summary),
          );
      });
    } catch (e) {
      // ignore: avoid_print
      print('J01_SUMMARY_WRITE_FAIL $e');
    }
    expect(failures, isEmpty, reason: 'J01 journey soft failures: $failures');
  }, timeout: const Timeout(Duration(minutes: 40)));
}

// ─────────────────────────── shared helpers ───────────────────────────

/// Mutable click counter shared with route helpers (pass-by-reference).
final clicks = <int>[0];

Finder? textAny(List<String> texts) {
  for (final t in texts) {
    final f = find.text(t);
    if (f.evaluate().isNotEmpty) return f.first;
  }
  return null;
}

/// Matches Text by data OR rich-text span (SparkleButton label paths).
Finder? textAnySmart(List<String> texts, {bool last = false}) {
  final smart = find.byWidgetPredicate((w) {
    if (w is! Text) return false;
    final plain = w.data ?? w.textSpan?.toPlainText() ?? '';
    return texts.any(plain.contains);
  });
  if (smart.evaluate().isEmpty) return null;
  return last ? smart.last : smart.first;
}

Future<void> dumpTexts(WidgetTester tester, String tag) async {
  final texts = <String>[];
  final allText = find.byType(Text);
  for (final e in allText.evaluate()) {
    final w = e.widget;
    if (w is Text) {
      final plain = w.data ?? w.textSpan?.toPlainText() ?? '';
      if (plain.trim().isNotEmpty) texts.add(plain.trim());
    }
  }
  // ignore: avoid_print
  print('J01_TEXTDUMP [$tag] n=${texts.length} ${jsonEncode(texts.take(40).toList())}');
}

Future<bool> waitUntil(
  WidgetTester tester,
  bool Function() cond, {
  Duration timeout = const Duration(seconds: 30),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (cond()) return true;
    await tester.pump(const Duration(milliseconds: 250));
  }
  return cond();
}

Future<void> safeSettle(
  WidgetTester tester, [
  Duration timeout = const Duration(seconds: 6),
]) async {
  try {
    await tester.pumpAndSettle(
      const Duration(milliseconds: 100),
      EnginePhase.sendSemanticsUpdate,
      timeout,
    );
  } catch (_) {
    await tester.pump(const Duration(seconds: 1));
  }
}

// ─────────────────────────── example route ───────────────────────────

Future<void> _exampleRoute({
  required WidgetTester tester,
  required String passId,
  required DateTime passT0,
  required Map<String, dynamic> passData,
  required Future<void> Function(String) shot,
  required void Function(String, String, String, DateTime) mark,
  required Finder? Function(List<String>) textAny,
}) async {
  final guest = textAny(['以访客身份继续', 'Continue as Guest']);
  if (guest == null) {
    passData['guest_leg'] = 'guest button not found';
    return;
  }
  try {
    await tester.scrollUntilVisible(
      guest,
      180,
      scrollable: find.byType(Scrollable).first,
    );
  } catch (_) {
    try {
      await tester.ensureVisible(guest);
    } catch (_) {}
  }
  await tester.pump(const Duration(milliseconds: 600));
  await shot('$passId/02-login.png');
  clicks[0]++;
  await tester.tap(guest);
  mark(passId, 'guest', 't_guest_tap', passT0);

  final dashReady = await waitUntil(
    tester,
    () => find.byType(DashboardScreen).evaluate().isNotEmpty,
    timeout: const Duration(seconds: 60),
  );
  passData['t_dashboard_visible_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  mark(passId, 'guest', 't_dashboard_visible', passT0);
  if (!dashReady) return;
  await safeSettle(tester);
  await tester.pump(const Duration(seconds: 2));
  await shot('$passId/03-dashboard-first-screen.png');

  // Scan: is the seeded demo data DECLARED as an example?
  bool probeText(List<String> keys) {
    for (final k in keys) {
      if (find.textContaining(k).evaluate().isNotEmpty) return true;
    }
    return false;
  }

  passData['example_scan_dashboard'] = {
    'seeded_goal_words': probeText(['期中冲刺', '先解决卡点', '解开卡点']),
    'declared_example_marker': probeText(['示例体验', '体验示例', '演示数据', '示例数据']),
    'onboarding_resume_hint': probeText(['继续完成', '继续引导', '个性化']),
    'seed_library_word': probeText(['种子库', '种子']),
  };
  mark(passId, 'guest', 't_example_scan_dashboard', passT0);
  await shot('$passId/04-example-scan-dashboard.png');

  // Scan remaining shell tabs once for declared example/seed entries.
  final scan2 = <String, String>{};
  for (final tab in const [
    ('星图', 'Galaxy'),
    ('对话', 'Chat'),
    ('社群', 'Community'),
    ('我的', 'Profile'),
  ]) {
    final f = textAny([tab.$1, tab.$2]);
    if (f != null) {
      clicks[0]++;
      await tester.tap(f, warnIfMissed: false);
      await safeSettle(tester);
      await tester.pump(const Duration(seconds: 1));
      final hasExample = find.textContaining('示例').evaluate().isNotEmpty ||
          find.textContaining('种子').evaluate().isNotEmpty;
      scan2[tab.$1] = hasExample ? 'example/seed words found' : 'none';
      await shot('$passId/05-tab-${tab.$1}.png');
    }
  }
  passData['example_scan_tabs'] = scan2;
  mark(passId, 'guest', 't_example_scan_tabs_done', passT0);
}

// ─────────────────────────── own-goal route ───────────────────────────

Future<void> _ownGoalRoute({
  required WidgetTester tester,
  required String passId,
  required Map<String, String> persona,
  required DateTime passT0,
  required Map<String, dynamic> passData,
  required Future<void> Function(String) shot,
  required void Function(String, String, String, DateTime) mark,
  required Finder? Function(List<String>) textAny,
  required List<String> failures,
}) async {
  // ════ Leg A: guest reality (what a zero-friction new user sees) ════
  final guest = textAny(['以访客身份继续', 'Continue as Guest']);
  if (guest == null) {
    failures.add('pass $passId: guest button not found on login');
    return;
  }
  try {
    await tester.scrollUntilVisible(
      guest,
      180,
      scrollable: find.byType(Scrollable).first,
    );
  } catch (_) {
    try {
      await tester.ensureVisible(guest);
    } catch (_) {}
  }
  await tester.pump(const Duration(milliseconds: 600));
  await shot('$passId/02-login.png');
  clicks[0]++;
  await tester.tap(guest);
  mark(passId, 'guest', 't_guest_tap', passT0);

  final dashReady = await waitUntil(
    tester,
    () => find.byType(DashboardScreen).evaluate().isNotEmpty,
    timeout: const Duration(seconds: 60),
  );
  passData['guest_leg'] = <String, dynamic>{
    't_dashboard_visible_ms': DateTime.now().difference(passT0).inMilliseconds,
    'reached': dashReady,
  };
  mark(passId, 'guest', 't_dashboard_visible', passT0);
  if (dashReady) {
    await safeSettle(tester);
    await tester.pump(const Duration(seconds: 2));
    await shot('$passId/03-dashboard-guest-first-screen.png');
    bool probeText(List<String> keys) {
      for (final k in keys) {
        if (find.textContaining(k).evaluate().isNotEmpty) return true;
      }
      return false;
    }

    final cta = textAny(['和 AI 定目标', '先定下你的第一个目标']);
    (passData['guest_leg'] as Map<String, dynamic>).addAll({
      'seeded_goal_visible': probeText(['期中冲刺', '先解决卡点', '解开卡点', '数据结构']),
      'declared_example_marker': probeText(['示例体验', '体验示例', '演示数据', '示例数据']),
      'set_first_goal_cta_visible': cta != null,
      'stuck_recovery_cta_visible': textAny(['解开卡点']) != null,
    });
    mark(passId, 'guest', 't_guest_dashboard_analyzed', passT0);
  }

  // ════ Leg B: register a fresh account → real own-goal journey ════
  final legT0 = DateTime.now();
  try {
    final container = ProviderScope.containerOf(
      tester.element(find.byType(MaterialApp).first),
    );
    await container.read(authProvider.notifier).logout();
  } catch (e) {
    failures.add('pass $passId: leg B logout failed: $e');
  }
  final backAtLogin = await waitUntil(
    tester,
    () => find.byType(LoginScreen).evaluate().isNotEmpty,
    timeout: const Duration(seconds: 30),
  );
  if (!backAtLogin) {
    failures.add('pass $passId: leg B did not return to login');
    return;
  }
  // Navigate to register. The link tap is flaky at real-UI level (button
  // sits below the fold) — retry up to 3 times and verify via the
  // register-only field 确认密码.
  var atRegister = false;
  for (var attempt = 0; attempt < 3 && !atRegister; attempt++) {
    final registerLink = textAny(['还没有账号？', 'No account yet?']);
    if (registerLink == null) {
      failures.add('pass $passId: register link not found on login');
      return;
    }
    try {
      await tester.scrollUntilVisible(
        registerLink,
        120,
        scrollable: find.byType(Scrollable).first,
      );
    } catch (_) {
      try {
        await tester.ensureVisible(registerLink);
      } catch (_) {}
    }
    await tester.pump(const Duration(milliseconds: 600));
    clicks[0]++;
    await tester.tap(registerLink, warnIfMissed: false);
    atRegister = await waitUntil(
      tester,
      () => find.text('确认密码').evaluate().isNotEmpty,
      timeout: const Duration(seconds: 8),
    );
    // ignore: avoid_print
    print('J01_DEBUG pass=$passId register nav attempt=$attempt ok=$atRegister');
  }
  if (!atRegister) {
    failures.add('pass $passId: register screen never appeared');
    await shot('$passId/06-register-never.png');
    return;
  }
  await safeSettle(tester);
  await shot('$passId/06-register-screen.png');
  final tRegisterStart = DateTime.now();
  passData['register_fields_to_fill'] = 4;

  // Fill username / email / password / confirm.
  final fields = find.byType(TextFormField);
  final suffix = DateTime.now().millisecondsSinceEpoch.toString().substring(6);
  final username = 'j01${persona['id']!.toLowerCase()}$suffix';
  if (fields.evaluate().length >= 4) {
    await tester.enterText(fields.at(0), username);
    await tester.enterText(fields.at(1), '$username@example.com');
    await tester.enterText(fields.at(2), 'J01-Passw0rd!');
    await tester.enterText(fields.at(3), 'J01-Passw0rd!');
    await tester.pump(const Duration(milliseconds: 300));
  } else {
    failures.add(
      'pass $passId: expected 4 register fields, '
      'found ${fields.evaluate().length}',
    );
    return;
  }
  // Accept TOS + privacy: tap the CheckboxListTile TILES (whole-row hit
  // area is more reliable than the label text).
  final tiles = find.byType(CheckboxListTile);
  final nTiles = tiles.evaluate().length;
  passData['register_tos_tiles'] = nTiles;
  for (var t = 0; t < nTiles; t++) {
    clicks[0]++;
    await tester.tap(tiles.at(t), warnIfMissed: false);
    await tester.pump(const Duration(milliseconds: 250));
  }
  await shot('$passId/07-register-filled.png');
  // Locate the submit BUTTON component (the AppBar title is also 注册 and a
  // plain-text tap can land on the adjacent ghost button).
  final submitText = textAnySmart(['注册'], last: true);
  if (submitText != null) {
    final btn = find
        .ancestor(of: submitText, matching: find.byType(SparkleButton))
        .evaluate()
        .isNotEmpty
        ? find.ancestor(of: submitText, matching: find.byType(SparkleButton)).first
        : submitText;
    try {
      await tester.ensureVisible(btn);
      await tester.pump(const Duration(milliseconds: 400));
    } catch (_) {}
    for (var attempt = 0; attempt < 2; attempt++) {
      clicks[0]++;
      await tester.tap(btn, warnIfMissed: false);
      final landed = await waitUntil(
        tester,
        () =>
            find.byType(DashboardScreen).evaluate().isNotEmpty ||
            find.byType(LoginScreen).evaluate().isNotEmpty ||
            find.text('确认密码').evaluate().isEmpty,
        timeout: const Duration(seconds: 12),
      );
      await dumpTexts(tester, 'after-register-submit-$attempt');
      if (find.text('确认密码').evaluate().isEmpty) break;
      // ignore: avoid_print
      print('J01_DEBUG pass=$passId register submit attempt=$attempt stayed=$landed');
    }
  }
  final registered = await waitUntil(
    tester,
    () =>
        find.byType(DashboardScreen).evaluate().isNotEmpty ||
        find.byType(LoginScreen).evaluate().isNotEmpty ||
        find.text('确认密码').evaluate().isEmpty,
    timeout: const Duration(seconds: 10),
  );
  await tester.pump(const Duration(seconds: 1));
  passData['t_register_done_ms'] =
      DateTime.now().difference(tRegisterStart).inMilliseconds;
  passData['registered_to_dashboard'] =
      find.byType(DashboardScreen).evaluate().isNotEmpty;
  mark(passId, 'own_goal', 't_registered', legT0);
  if (!(passData['registered_to_dashboard'] as bool)) {
    // Record the failure state honestly: visible error texts + the auth
    // provider's own error, then fall back to API-register + UI-login so
    // the wizard measurement can still proceed on a REAL fresh account.
    final errTexts = <String>[];
    for (final f in [
      '注册失败', '失败', '已存在', '无效', '至少', '不匹配', '请输入', '请先',
    ]) {
      if (find.textContaining(f).evaluate().isNotEmpty) errTexts.add(f);
    }
    passData['register_error_markers'] = errTexts;
    try {
      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp).first),
      );
      final authState = container.read(authProvider);
      passData['auth_provider_error'] = authState.error?.toString();
    } catch (_) {}
    // ignore: avoid_print
    print(
        'J01_FINDING pass=$passId UI register did not reach dashboard '
        '(errors=${jsonEncode(errTexts)}, '
        'provider=${passData['auth_provider_error']})');
    await shot('$passId/07b-register-result.png');
    failures.add(
      'pass $passId: UI register did not reach dashboard (silent bounce)',
    );

    // FALLBACK: ensure the account exists via the real register API
    // (fresh backend account, no guest seed), then log in through the UI.
    await tester.runAsync(() async {
      try {
        final client = HttpClient();
        final req = await client.postUrl(
          Uri.parse('http://localhost:8080/api/v1/auth/register'),
        );
        req.headers.contentType = ContentType.json;
        req.write(jsonEncode({
          'username': username,
          'email': '$username@example.com',
          'password': 'J01-Passw0rd!',
          'accepted_tos': true,
          'accepted_privacy': true,
          'agreed_locale': 'zh-CN',
        }));
        final res = await req.close();
        final body = await res.transform(utf8.decoder).join();
        passData['api_register_status'] = res.statusCode;
        // ignore: avoid_print
        print(
            'J01_DEBUG pass=$passId api register status=${res.statusCode} '
            'body=${body.length > 160 ? body.substring(0, 160) : body}');
        client.close();
      } catch (e) {
        passData['api_register_error'] = e.toString();
      }
    });
    await dumpTexts(tester, 'before-fallback-login');
    // If still on the register screen, walk the REAL user path back to
    // login via the 已有账号？ ghost button.
    if (find.text('确认密码').evaluate().isNotEmpty) {
      final backLink = textAnySmart(['已有账号？', '已有账号']);
      if (backLink != null) {
        final backBtn = find
            .ancestor(of: backLink, matching: find.byType(SparkleButton))
            .evaluate()
            .isNotEmpty
            ? find.ancestor(of: backLink, matching: find.byType(SparkleButton)).first
            : backLink;
        try {
          await tester.ensureVisible(backBtn);
          await tester.pump(const Duration(milliseconds: 400));
        } catch (_) {}
        clicks[0]++;
        await tester.tap(backBtn, warnIfMissed: false);
        final atLogin = await waitUntil(
          tester,
          () => find.text('确认密码').evaluate().isEmpty &&
              find.byType(TextFormField).evaluate().isNotEmpty,
          timeout: const Duration(seconds: 10),
        );
        // ignore: avoid_print
        print('J01_DEBUG pass=$passId back-to-login ok=$atLogin');
      }
    }
    // UI login with the fresh account (smart finder: rich-text safe).
    final loginFields = find.byType(TextFormField);
    if (loginFields.evaluate().length >= 2) {
      await tester.enterText(loginFields.at(0), username);
      await tester.enterText(loginFields.at(1), 'J01-Passw0rd!');
      await tester.pump(const Duration(milliseconds: 300));
      var loginBtn = textAnySmart(['登录'], last: true);
      if (loginBtn == null) {
        failures.add('pass $passId: login button not findable (rich text?)');
        await dumpTexts(tester, 'login-button-missing');
        return;
      }
      final loginBtnWidget = find
          .ancestor(of: loginBtn, matching: find.byType(SparkleButton))
          .evaluate()
          .isNotEmpty
          ? find.ancestor(of: loginBtn, matching: find.byType(SparkleButton)).first
          : loginBtn;
      try {
        await tester.ensureVisible(loginBtnWidget);
        await tester.pump(const Duration(milliseconds: 400));
      } catch (_) {}
      clicks[0]++;
      await tester.tap(loginBtnWidget, warnIfMissed: false);
    }
    var logged = await waitUntil(
      tester,
      () => find.byType(DashboardScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 30),
    );
    passData['fallback_login_to_dashboard'] = logged;
    mark(passId, 'own_goal', 't_fallback_logged_in', legT0);
    if (!logged) {
      // UI login also not automatable on this surface — log in via the
      // auth provider (INSTRUMENTED step, disclosed in the report) so the
      // goal-wizard leg still runs on a real fresh registered account.
      // ignore: avoid_print
      print(
          'J01_FINDING pass=$passId UI login tap also ineffective — using provider login (instrumented)');
      try {
        final container = ProviderScope.containerOf(
          tester.element(find.byType(MaterialApp).first),
        );
        await container
            .read(authProvider.notifier)
            .login(username, 'J01-Passw0rd!');
        logged = await waitUntil(
          tester,
          () => find.byType(DashboardScreen).evaluate().isNotEmpty,
          timeout: const Duration(seconds: 30),
        );
        passData['provider_login_to_dashboard'] = logged;
      } catch (e) {
        passData['provider_login_error'] = e.toString();
      }
      if (!logged) {
        failures.add('pass $passId: fallback login failed (incl. provider)');
        await shot('$passId/07c-login-failed.png');
        return;
      }
    }
  }
  await safeSettle(tester);
  await tester.pump(const Duration(seconds: 2));
  await shot('$passId/08-dashboard-registered-first-screen.png');

  // ---- first-goal CTA ----
  // NOTE: 先定下你的第一个目标 is the card HEADLINE (not tappable); the
  // tappable primary button is 和 AI 定目标 (dashboardStartWithAI).
  await waitUntil(
    tester,
    () => textAny(['和 AI 定目标', '先定下你的第一个目标']) != null,
    timeout: const Duration(seconds: 20),
  );
  var ctaFinder = textAny(['和 AI 定目标']);
  ctaFinder ??= textAny(['Set your first goal', '先定下你的第一个目标']);
  passData['t_goal_cta_visible_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  passData['goal_cta_found'] = ctaFinder != null;
  mark(passId, 'own_goal', 't_goal_cta_visible', passT0);
  if (ctaFinder == null) {
    failures.add('pass $passId: first-goal CTA not found on registered dashboard');
    await shot('$passId/08b-no-cta.png');
    return;
  }
  try {
    await tester.ensureVisible(ctaFinder);
  } catch (_) {}
  await tester.pump(const Duration(milliseconds: 400));
  await shot('$passId/09-first-goal-cta.png');
  // Tap the BUTTON ancestor of the CTA text (plain-text taps can miss the
  // hit area inside the card stack).
  final ctaBtn = find
      .ancestor(of: ctaFinder, matching: find.byType(SparkleButton))
      .evaluate()
      .isNotEmpty
      ? find.ancestor(of: ctaFinder, matching: find.byType(SparkleButton)).first
      : ctaFinder;
  var wizardAppeared = false;
  for (var attempt = 0; attempt < 4 && !wizardAppeared; attempt++) {
    // If the CTA sits in the bottom overlap zone (floating toolbar / chat
    // input), push the scrollable content up before tapping.
    try {
      final rect = tester.getRect(ctaBtn);
      final screenH = tester.view.physicalSize.height /
          tester.view.devicePixelRatio;
      // ignore: avoid_print
      print('J01_DEBUG pass=$passId cta rect=$rect screenH=$screenH');
      if (rect.center.dy > screenH * 0.65) {
        await tester.drag(find.byType(Scrollable).first, const Offset(0, 260));
        await tester.pump(const Duration(milliseconds: 600));
      }
    } catch (e) {
      // ignore: avoid_print
      print('J01_DEBUG pass=$passId cta rect probe failed: $e');
    }
    clicks[0]++;
    await tester.tap(ctaBtn, warnIfMissed: false);
    wizardAppeared = await waitUntil(
      tester,
      () => find.byType(GoalCreationWizardScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 10),
    );
    // ignore: avoid_print
    print('J01_DEBUG pass=$passId cta tap attempt=$attempt wizard=$wizardAppeared');
  }

  // ---- wizard ----
  final wizardReady = wizardAppeared ||
      await waitUntil(
        tester,
        () => find.byType(GoalCreationWizardScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 10),
      );
  passData['t_wizard_visible_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  passData['wizard_reached'] = wizardReady;
  mark(passId, 'own_goal', 't_wizard_visible', passT0);
  if (!wizardReady) {
    failures.add('pass $passId: goal wizard never appeared');
    return;
  }
  await safeSettle(tester);
  await shot('$passId/10-wizard-step0-intent.png');

  // Step 0: type persona goal, submit intent analysis (real AI backend).
  final intentField = find.descendant(
    of: find.byKey(const ValueKey('goal-intent-input-step')),
    matching: find.byType(TextField),
  );
  if (intentField.evaluate().isEmpty) {
    failures.add('pass $passId: intent input field not found');
    return;
  }
  await tester.enterText(intentField.first, persona['goal']!);
  await tester.pump(const Duration(milliseconds: 400));
  final analyzeBtn = textAny(['让我先看看你的情况', '继续']);
  if (analyzeBtn != null) {
    clicks[0]++;
    await tester.tap(analyzeBtn, warnIfMissed: false);
  }
  passData['t_intent_submitted_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  mark(passId, 'own_goal', 't_intent_submitted', passT0);
  await shot('$passId/11-intent-analyzing.png');

  // Wait for the analysis result: confirmation card OR legacy chooser
  // (both are real outcomes; the variance itself is measurement data).
  final analyzed = await waitUntil(
    tester,
    () =>
        find
            .byKey(const ValueKey('goal-intent-confirm-step'))
            .evaluate()
            .isNotEmpty ||
        find.byKey(const ValueKey('goal-type-step')).evaluate().isNotEmpty ||
        find
            .byKey(const ValueKey('goal-motivation-step'))
            .evaluate()
            .isNotEmpty,
    timeout: const Duration(seconds: 90),
  );
  passData['t_intent_analyzed_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  passData['intent_analyzed'] = analyzed;
  passData['intent_outcome'] = find
          .byKey(const ValueKey('goal-intent-confirm-step'))
          .evaluate()
          .isNotEmpty
      ? 'actionable_card'
      : (find.byKey(const ValueKey('goal-type-step')).evaluate().isNotEmpty
          ? 'legacy_type_chooser'
          : (find
                  .byKey(const ValueKey('goal-motivation-step'))
                  .evaluate()
                  .isNotEmpty
              ? 'legacy_step1'
              : 'unknown'));
  mark(passId, 'own_goal', 't_intent_analyzed', passT0);
  await safeSettle(tester);
  await shot('$passId/12-intent-result.png');

  // If the actionable card appeared: follow the first suggested action
  // (what a real new user would do).
  if (passData['intent_outcome'] == 'actionable_card') {
    final actionRow = find.descendant(
      of: find.byKey(const ValueKey('goal-intent-confirm-step')),
      matching: find.byIcon(Icons.play_arrow_rounded),
    );
    if (actionRow.evaluate().isNotEmpty) {
      clicks[0]++;
      await tester.tap(actionRow.first, warnIfMissed: false);
    } else {
      failures.add('pass $passId: actionable card without visible action row');
    }
    await tester.pump(const Duration(seconds: 1));
  } else if (passData['intent_outcome'] == 'legacy_type_chooser') {
    // Legacy fallback: pick a type pill, then continue.
    final pill = textAny(['项目', '学术', '技能', '习惯', '其他']);
    if (pill != null) {
      clicks[0]++;
      await tester.tap(pill, warnIfMissed: false);
      await tester.pump(const Duration(milliseconds: 400));
    }
  }

  // Walk the remaining wizard steps with the bottom primary button,
  // filling required fields at the motivation step. Stalls (disabled
  // button / backend preview failing) are recorded, not guessed.
  var stalls = 0;
  var lastStepKey = '';
  for (var guard = 0; guard < 10; guard++) {
    final onMotivation = find
        .byKey(const ValueKey('goal-motivation-step'))
        .evaluate()
        .isNotEmpty;
    if (onMotivation) {
      final fields = find.descendant(
        of: find.byKey(const ValueKey('goal-motivation-step')),
        matching: find.byType(TextField),
      );
      if (fields.evaluate().length >= 2) {
        final goalText = persona['goal']!;
        await tester.enterText(
          fields.at(0),
          goalText.length > 40 ? goalText.substring(0, 40) : goalText,
        );
        await tester.enterText(fields.at(1), '这是我想完成它的原因。');
        await tester.pump(const Duration(milliseconds: 300));
      }
    }
    await shot('$passId/13-wizard-step-$guard.png');
    final onConfirmNow = find
        .byKey(const ValueKey('goal-confirm-step'))
        .evaluate()
        .isNotEmpty;
    // On the confirm step the primary action is 创建 (a real backend create).
    final cont = onConfirmNow
        ? (textAny(['创建']) ?? textAny(['继续']))
        : textAny(['继续', '创建']);
    if (cont == null) break;
    clicks[0]++;
    await tester.tap(cont, warnIfMissed: false);
    // Goal creation is a real backend POST — give it room and watch for
    // the success dialog or a visible failure message.
    final created = await waitUntil(
      tester,
      () =>
          find.byType(GoalCreationWizardScreen).evaluate().isEmpty ||
          find.textContaining('创建失败').evaluate().isNotEmpty ||
          find.textContaining('目标已创建').evaluate().isNotEmpty,
      timeout: const Duration(seconds: 15),
    );
    await safeSettle(tester);
    if (find.textContaining('创建失败').evaluate().isNotEmpty) {
      passData['create_failed_marker'] = true;
      // ignore: avoid_print
      print('J01_FINDING pass=$passId goal create failed marker shown');
      await shot('$passId/13b-create-failed.png');
    }
    if (find.textContaining('目标已创建').evaluate().isNotEmpty) {
      passData['goal_created_dialog'] = true;
      // ignore: avoid_print
      print('J01_FINDING pass=$passId goal created dialog shown');
      await shot('$passId/13c-goal-created-dialog.png');
    }
    final wizardGone =
        find.byType(GoalCreationWizardScreen).evaluate().isEmpty;
    mark(passId, 'own_goal', 't_wizard_step_$guard', passT0);
    if (wizardGone) {
      passData['t_wizard_exited_after_steps'] = guard + 1;
      break;
    }
    final stepKey =
        find.byKey(const ValueKey('goal-confirm-step')).evaluate().isNotEmpty
            ? 'confirm'
            : find
                    .byKey(const ValueKey('goal-milestone-step'))
                    .evaluate()
                    .isNotEmpty
                ? 'milestone'
                : find
                        .byKey(const ValueKey('goal-time-step'))
                        .evaluate()
                        .isNotEmpty
                    ? 'time'
                    : find
                            .byKey(const ValueKey('goal-motivation-step'))
                            .evaluate()
                            .isNotEmpty
                        ? 'motivation'
                        : find
                                .byKey(const ValueKey('goal-type-step'))
                                .evaluate()
                                .isNotEmpty
                            ? 'type'
                            : find
                                    .byKey(
                                      const ValueKey('goal-intent-confirm-step'),
                                    )
                                    .evaluate()
                                    .isNotEmpty
                                ? 'intent_confirm'
                                : 'intent_input';
    if (stepKey == lastStepKey) {
      stalls++;
      if (stalls >= 3) {
        failures.add(
          'pass $passId: wizard stalled at step "$stepKey" after 3 taps '
          '(likely backend preview/intent dependency or disabled CTA)',
        );
        break;
      }
    } else {
      stalls = 0;
      lastStepKey = stepKey;
    }
  }
  await shot('$passId/14-wizard-final-state.png');

  // Goal-created evidence: wizard exited (success dialog / routed onward).
  final exited = await waitUntil(
    tester,
    () => find.byType(GoalCreationWizardScreen).evaluate().isEmpty,
    timeout: const Duration(seconds: 60),
  );
  passData['t_route_done_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  passData['wizard_exited'] = exited;
  mark(passId, 'own_goal', 't_route_done', passT0);
  await safeSettle(tester);
  await tester.pump(const Duration(seconds: 1));
  await shot('$passId/15-after-create.png');
  if (!exited) {
    failures.add('pass $passId: wizard did not finish');
  }
}
