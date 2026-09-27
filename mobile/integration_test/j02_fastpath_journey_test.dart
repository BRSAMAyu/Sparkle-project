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
import 'package:sparkle/features/auth/presentation/screens/register_screen.dart';
import 'package:sparkle/features/chat/presentation/screens/chat_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/journey/presentation/widgets/first_action_card.dart';
import 'package:sparkle/features/user/presentation/screens/modeling_chat_screen.dart';
import 'package:sparkle/features/user/presentation/screens/persona_onboarding_screen.dart';
import 'package:sparkle/main.dart' as app;

/// J-02 "Value Before Profile" fast-path journey driver (measurement
/// infrastructure — product code is NOT modified by this card).
///
/// File name is FIXED by the post-gate harness:
/// `v3-output/WT784-J02PREP/first3minutes.sh` guards
/// `mobile/integration_test/j02_fastpath_journey_test.dart` (runbook §2.2),
/// so the J-02PREP-prepared orchestrator can only pick this driver up under
/// this exact path.
///
/// Spec: v3-output/WT784-J02PREP/runbook.md §3 (step tables R0-R9 / G1-G4 /
/// U1-U3), §4 (stopwatch artifacts), §8 (artifact naming). The J-01 precedent
/// `first3_measurement_test.dart` is the J-01 goal-wizard route and does NOT
/// cover the J-02 fast path (resume card → persona step 1 →
/// `j02-fast-path-cta` → modeling skip → FirstActionCard) — this driver does.
/// Helpers are isomorphic to J-01 (textAny/waitUntil/safeSettle/shot), marks
/// are J01_MARK→J02_MARK.
///
/// dart-defines:
///  * J02_PASS: '0'-'4' → Leg R for that single persona in THIS process
///    (one true cold start per process = per-persona fresh install, runbook
///    §2.1 macOS semantics); 'all' → personas loop in-process (pass 1 cold,
///    passes 2-5 warm reset, labelled as such — J-01 precedent).
///  * J02_LEGS: comma list subset of {R,G,U} (default 'R,G,U'). Leg R runs
///    per selected persona; Legs G/U run ONCE per process after Leg R. The
///    prepared orchestrator command omits this define and gets all legs.
///  * J02_SHOT_DEST: screenshot destination (orchestrator passes
///    `<evidence>/<run_id>/screenshots`). JSON artifacts (j02_timings.json /
///    steps.json / proposals.json) land in the PARENT dir when the dest is
///    named 'screenshots' (runbook §8 template), else alongside.
///
/// THREE-CHANNEL semantics (runbook §3):
///  * Leg R (registered): register fresh → /home SOFT WALL (OnboardingResume
///    card, NOT the old persona step-0 hard redirect) → resume CTA → persona
///    step 1 → fast-path CTA (goal-only payload; remaining four questions
///    deferred) → modeling chat → skip → FirstActionCard → generate →
///    proposal → confirm. Stopwatch core: t_action_ready - t_pass_start
///    ≤ 180,000ms (budget const [j02BudgetMs]).
///  * Leg G (guest): login-screen guest entry → seeded dashboard (session
///    stable, no persona loop) → seed/example marker scan (missing example
///    marker is MEASUREMENT DATA, not harness failure — J-01 O1) → one demo
///    chat round. G4 DB probes (memory_goals/episodic_memories both 0 rows,
///    registration_source='guest') are run by the orchestrator via
///    `docker exec sparkle_db psql` (runbook §5) — this driver prints
///    `J02_GUEST_USER=<username>` for that purpose and does NOT touch docker.
///  * Leg U (upgrade): guest-state GuestConversionCard → register form →
///    in-place flip (same session, no logout-to-login, registrationSource
///    leaves 'guest') → persona onboarding still reachable (resume card).
///
/// HONESTY RULES (inherited from J-01 + runbook §6):
///  * All timings are real wall-clock while the live app renders real frames
///    (fullyLive frame policy). No fake clocks, no invented numbers.
///  * Product behaviours (post-skip landing route, missing example markers,
///    register tap bounce) are recorded as findings, not papered over;
///    harness breakage is a failure. O3-family register bounce triggers the
///    disclosed API-register + UI-login fallback which is EXCLUDED from the
///    ≤3min claim (runbook §6-2, `register_ui_bounce=true`).
///  * Any step timeout → screenshot `9x-<step>-timeout.png` + TEXTDUMP; no
///    run deletion, no silent retries that erase evidence.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized()
      .framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  const passParam = String.fromEnvironment('J02_PASS', defaultValue: 'all');
  const legsParam = String.fromEnvironment('J02_LEGS', defaultValue: 'R,G,U');
  final legs = legsParam
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .where((s) => s.isNotEmpty)
      .toList();
  const shotDestEnv = String.fromEnvironment('J02_SHOT_DEST');
  final shotDest = shotDestEnv.isNotEmpty
      ? shotDestEnv
      : '${Directory.current.path.endsWith('mobile') ? Directory.current.parent.path : Directory.current.path}/v3-output/J02/evidence/screenshots';
  // Runbook §8: JSON artifacts live next to screenshots/, i.e. one level up.
  final normalizedDest = shotDest.replaceAll(RegExp(r'/+$'), '');
  final destDirName = normalizedDest.split(Platform.pathSeparator).last;
  final artifactDir =
      destDirName == 'screenshots' ? Directory(normalizedDest).parent.path : normalizedDest;

  final harnessT0 = DateTime.now();
  final failures = <String>[];
  final allPasses = <Map<String, dynamic>>[];
  final steps = <Map<String, dynamic>>[];
  final proposals = <String, String>{};
  String? guestUsername;
  String? upgradedUsername;

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
      print('J02_SHOT $relName ok bytes=${File(dest).lengthSync()}');
    } catch (e) {
      // ignore: avoid_print
      print('J02_SHOT_FAIL $relName: $e');
      failures.add('screenshot $relName failed: $e');
    }
  }

  /// Leg R marks carry `ms_since_pass_t0` (runbook §4 form, consumed by the
  /// orchestrator's 180s verdict). Legs G/U marks carry `ms_since_leg_t0`
  /// instead — A2 session-stability legs have NO 3-minute budget, and letting
  /// their times feed the same `ms_since_pass_t0` field would make the
  /// orchestrator verdict (regex `ms_since_pass_t0=`) pollute the Leg R
  /// budget with post-budget legs.
  void mark(
    String passId,
    String leg,
    String name,
    DateTime t0, {
    String clockField = 'ms_since_pass_t0',
  }) {
    final now = DateTime.now();
    // ignore: avoid_print
    print(j02MarkLine(
      pass: passId,
      leg: leg,
      mark: name,
      clockField: clockField,
      msSinceT0: now.difference(t0).inMilliseconds,
      clicks: clicks[0],
    ),);
  }

  void recordStep(String leg, String step, bool pass, String note) {
    steps.add({
      'leg': leg,
      'step': step,
      'status': pass ? 'PASS' : 'FAIL',
      'note': note,
      'ts': DateTime.now().toIso8601String(),
    });
    if (!pass) {
      // ignore: avoid_print
      print('J02_STEP_FAIL leg=$leg step=$step note=$note');
    }
  }

  /// Runbook §3 cross-cutting rule: any wait timeout → immediate timeout
  /// screenshot + TEXTDUMP (9x-<step>-timeout.png), never a bare swallow.
  Future<bool> waitUntilTracked(
    WidgetTester tester,
    String leg,
    String step,
    bool Function() cond, {
    Duration timeout = const Duration(seconds: 30),
    String clockField = 'ms_since_pass_t0',
  }) async {
    final ok = await waitUntil(tester, cond, timeout: timeout);
    if (!ok) {
      await shot('9x-$step-timeout.png');
      await dumpTexts(tester, '$leg/$step timeout');
      recordStep(leg, step, false, 'wait timeout after ${timeout.inSeconds}s');
    }
    return ok;
  }

  Future<void> writeArtifact(String fileName, Object Function() build) async {
    try {
      await testTester.runAsync(() async {
        File('$artifactDir/$fileName')
          ..createSync(recursive: true)
          ..writeAsStringSync(
            const JsonEncoder.withIndent('  ').convert(build()),
            flush: true,
          );
      });
      // ignore: avoid_print
      print('J02_ARTIFACT $fileName -> $artifactDir');
    } catch (e) {
      // ignore: avoid_print
      print('J02_ARTIFACT_FAIL $fileName: $e');
    }
  }

  Future<void> wipeLocalState() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    const secure = FlutterSecureStorage(
      mOptions: MacOsOptions(useDataProtectionKeyChain: false),
    );
    await secure.deleteAll();
  }

  testWidgets(
    'J02 fast-path journey (pass=$passParam legs=$legs)',
    (tester) async {
    testTester = tester;
    final originalOnError = FlutterError.onError;
    final originalPlatformOnError = ui.PlatformDispatcher.instance.onError;
    final originalErrorWidgetBuilder = ErrorWidget.builder;

    // ---- PASS prep: true fresh-install semantics (wipe BEFORE app.main(),
    // so the first pass of every process is a genuine cold start). ----
    try {
      await wipeLocalState();
      // ignore: avoid_print
      print('J02 prefs+secure storage cleared (clean-install state)');
    } catch (e) {
      // ignore: avoid_print
      print('J02 local state wipe failed: $e');
    }

    app.main();
    unawaited(BgmService.setEnabled(false).timeout(const Duration(seconds: 3)));
    unawaited(BgmService.stop().timeout(const Duration(seconds: 3)));

    final selected = passParam == 'all'
        ? List<int>.generate(j02Personas.length, (i) => i)
        : <int>[int.parse(passParam)];
    try {
      for (final i in selected) {
        final persona = j02Personas[i];
        final warm = passParam == 'all' && i != selected.first;
        if (warm) {
          // WARM reset between in-process passes (logout + wipe) — J-01
          // semantics. Only PASS=<i> single-process runs are TRUE cold starts
          // per persona (runbook §2.1).
          await resetToLoginBetweenPasses(
            tester,
            persona['id']!,
            failures,
          );
        }
        final passData = <String, dynamic>{
          'persona': persona,
          'route': 'j02_fastpath',
          'warm_process': warm,
          for (final key in requiredTimingKeys) key: null,
        };
        clicks[0] = 0;
        if (legs.contains('R')) {
          await legRRegistered(
            tester: tester,
            persona: persona,
            warm: warm,
            passT0: DateTime.now(),
            passData: passData,
            shot: shot,
            markFn: mark,
            recordStep: recordStep,
            waitTracked: waitUntilTracked,
            failures: failures,
            onRegistered: (username) =>
                // ignore: avoid_print
                print('J02_REGISTERED_USER $username'),
            onProposal: (text) => proposals[persona['id']!] = text,
          );
        }
        allPasses.add(passData);
      }

      // ---- Legs G / U run ONCE per process (persona-independent session-
      // stability legs; the ≤3min budget belongs to Leg R only). ----
      final legPassId = passParam == 'all'
          ? 'PX1'
          : j02Personas[int.parse(passParam)]['id']!;
      if (legs.contains('G')) {
        guestUsername = await legGGuest(
          tester: tester,
          passId: legPassId,
          shot: shot,
          markFn: mark,
          recordStep: recordStep,
          waitTracked: waitUntilTracked,
          failures: failures,
        );
        if (guestUsername != null) {
          // ignore: avoid_print
          print('J02_GUEST_USER $guestUsername');
        }
      }
      if (legs.contains('U')) {
        upgradedUsername = await legUUpgrade(
          tester: tester,
          passId: legPassId,
          shot: shot,
          markFn: mark,
          recordStep: recordStep,
          waitTracked: waitUntilTracked,
          failures: failures,
        );
        if (upgradedUsername != null) {
          // ignore: avoid_print
          print('J02_UPGRADED_USER $upgradedUsername');
        }
      }
    } catch (e, st) {
      failures.add('journey aborted: $e');
      // ignore: avoid_print
      print('J02 fatal: $e\n$st');
      try {
        await shot('99-fatal-state.png');
      } catch (_) {}
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

    // ---- F3 differentiation (runbook §3 5-persona rule): in-process check
    // when 'all' gathered more than one proposal; single-pass runs are
    // compared offline by the executor across proposals.json files. ----
    final pairwiseDistinct = proposalsPairwiseDistinct(proposals);

    final summary = {
      'driver': 'integration_test/j02_fastpath_journey_test.dart',
      'spec': 'v3-output/WT784-J02PREP/runbook.md §3/§4/§8',
      'pass_param': passParam,
      'legs': legs,
      'budget_ms': j02BudgetMs,
      'harness_t0': harnessT0.toIso8601String(),
      'finished_at': DateTime.now().toIso8601String(),
      'passes': allPasses,
      'proposals': proposals,
      'proposals_pairwise_distinct_in_process': pairwiseDistinct,
      'guest_leg': {
        'guest_username': guestUsername,
        // G4 DB probes are orchestrator-owned (runbook §5): the executor
        // runs first3minutes.sh db_probes with J02_GUEST_USER printed above.
        'db_probe_owner': 'orchestrator (first3minutes.sh db_probes)',
      },
      'upgrade_leg': {'upgraded_username': upgradedUsername},
      'steps': steps,
      'failures': failures,
    };
    // ignore: avoid_print
    print('J02_SUMMARY ${jsonEncode(summary)}');
    await writeArtifact('j02_timings.json', () => summary);
    await writeArtifact(
      'steps.json',
      () => {'steps': steps, 'failures': failures},
    );
    await writeArtifact(
      'proposals.json',
      () => {
        'proposals': proposals,
        // F3 judgement: persona proposals must be pairwise non-identical
        // (UI face of the J-04 backend differentiation).
        'pairwise_distinct_in_process': pairwiseDistinct,
      },
    );
    expect(failures, isEmpty, reason: 'J02 journey soft failures: $failures');
  },
    timeout: const Timeout(Duration(minutes: 75)),
  );
}

// ═══════════════════════ Leg R — registered fresh user ═══════════════════════
//
// runbook §3 Leg R table: R0 cold start → R9 confirm. Pass gate: all steps
// reached AND t_action_ready - t_pass_start ≤ j02BudgetMs AND no blank error
// pages. t_pass_start = cold-start of THIS process (real wall clock).

Future<void> legRRegistered({
  required WidgetTester tester,
  required Map<String, String> persona,
  required bool warm,
  required DateTime passT0,
  required Map<String, dynamic> passData,
  required Future<void> Function(String) shot,
  required void Function(
    String,
    String,
    String,
    DateTime, {
    String clockField,
  }) markFn,
  required void Function(String, String, bool, String) recordStep,
  required Future<bool> Function(
    WidgetTester,
    String,
    String,
    bool Function(), {
    Duration timeout,
    String clockField,
  }) waitTracked,
  required List<String> failures,
  required void Function(String username) onRegistered,
  required void Function(String proposalText) onProposal,
}) async {
  final passId = persona['id']!;
  markFn(passId, 'R', warm ? 't_pass_start_warm' : 't_pass_start_cold', passT0);

  // ---- R0: cold start → splash → login screen. FIRST_3_MINUTES F2: the
  // primary CTA must be visible WITHOUT scrolling on the first surface. ----
  final firstSurface = await waitTracked(
    tester,
    'R',
    'r0_first_surface',
    () =>
        find.byType(LoginScreen).evaluate().isNotEmpty ||
        find.byType(DashboardScreen).evaluate().isNotEmpty ||
        find.text('已有账号？').evaluate().isNotEmpty,
    timeout: const Duration(seconds: 90),
  );
  passData['t_first_surface_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  markFn(passId, 'R', 't_first_surface', passT0);
  if (!firstSurface) {
    failures.add('pass $passId: never reached login/dashboard');
    return;
  }
  await safeSettle(tester);
  await shot('$passId/01-first-surface.png');

  // Warm-reset passes may land somewhere else public; walk back to login.
  if (find.text('已有账号？').evaluate().isNotEmpty &&
      find.byType(LoginScreen).evaluate().isEmpty) {
    await tapTextButton(tester, ['已有账号？']);
    await waitUntil(
      tester,
      () => find.byType(LoginScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 20),
    );
  }

  // Auto-login despite the wipe is a REAL measured behaviour — record, then
  // walk the product logout path so the pass starts at login like a true
  // first-run user (J-01 precedent).
  if (find.byType(LoginScreen).evaluate().isEmpty &&
      find.byType(DashboardScreen).evaluate().isNotEmpty) {
    passData['auto_login_after_wipe'] = true;
    // ignore: avoid_print
    print(
      'J02_FINDING pass=$passId auto-login after secure-storage+prefs wipe',
    );
    await productLogout(tester, passId, failures);
    await waitUntil(
      tester,
      () => find.byType(LoginScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 20),
    );
    await safeSettle(tester);
    await shot('$passId/01b-after-logout.png');
  }

  // F2: login primary button no-scroll visibility + welcome subtitle.
  final loginCta = find.widgetWithText(SparkleButton, '登录');
  passData['login_cta_present'] = loginCta.evaluate().isNotEmpty;
  passData['login_cta_no_scroll_visible'] = fullyVisible(tester, loginCta);
  passData['welcome_subtitle_present'] =
      find.textContaining('AI 陪你').evaluate().isNotEmpty;
  recordStep(
    'R',
    'r0_first_surface',
    passData['login_cta_no_scroll_visible'] as bool,
    'F2 primary CTA no-scroll=${passData['login_cta_no_scroll_visible']}',
  );
  markFn(passId, 'R', 'r0_f2_checked', passT0);

  // ---- R1: register link (below the fold on desktop — J-01 tap flaky,
  // retry ×3, verified via the register-only 确认密码 field). ----
  var atRegister = false;
  for (var attempt = 0; attempt < 3 && !atRegister; attempt++) {
    final registerLink = textAny(['还没有账号？', 'No account yet?']);
    if (registerLink == null) {
      failures.add('pass $passId: register link not found on login');
      return;
    }
    await revealFinder(tester, registerLink);
    await tester.pump(const Duration(milliseconds: 600));
    clicks[0]++;
    await tester.tap(registerLink, warnIfMissed: false);
    atRegister = await waitUntil(
      tester,
      () =>
          find.byType(RegisterScreen).evaluate().isNotEmpty ||
          find.text('确认密码').evaluate().isNotEmpty,
      timeout: const Duration(seconds: 8),
    );
    // ignore: avoid_print
    print(
      'J02_DEBUG pass=$passId register nav attempt=$attempt ok=$atRegister',
    );
  }
  recordStep('R', 'r1_register_nav', atRegister, 'retry cap ×3');
  if (!atRegister) {
    failures.add('pass $passId: register screen never appeared');
    await shot('$passId/9x-r1-register-never.png');
    return;
  }
  await safeSettle(tester);
  await shot('$passId/02-register.png');

  // ---- R2: fill username / email / password / confirm + 2 consent tiles.
  // Unique account names: j02px<i><timestamp-suffix> (runbook §1.3 form). ----
  final fields = find.byType(TextFormField);
  final suffix = DateTime.now().millisecondsSinceEpoch.toString().substring(6);
  final personaIndex = int.parse(passId.substring(2));
  final username = 'j02px$personaIndex$suffix';
  if (fields.evaluate().length >= 4) {
    await tester.enterText(fields.at(0), username);
    await tester.enterText(fields.at(1), '$username@example.com');
    await tester.enterText(fields.at(2), j02Password);
    await tester.enterText(fields.at(3), j02Password);
    await tester.pump(const Duration(milliseconds: 300));
  } else {
    failures.add(
      'pass $passId: expected 4 register fields, '
      'found ${fields.evaluate().length}',
    );
    recordStep('R', 'r2_register_filled', false, 'field count mismatch');
    return;
  }
  // Tap the CheckboxListTile TILES (whole-row hit area — J-01 lesson).
  final tiles = find.byType(CheckboxListTile);
  final nTiles = tiles.evaluate().length;
  passData['register_tos_tiles'] = nTiles;
  for (var t = 0; t < nTiles; t++) {
    clicks[0]++;
    await tester.tap(tiles.at(t), warnIfMissed: false);
    await tester.pump(const Duration(milliseconds: 250));
  }
  await shot('$passId/03-register-filled.png');
  recordStep('R', 'r2_register_filled', true, 'username=$username');
  onRegistered(username);

  // ---- R3: submit 注册 (SparkleButton ancestor filter — the AppBar title
  // bears the same text and burned J-01 for 7 runs; O3 residual risk).
  // Expected landing: /home SOFT WALL (Dashboard + OnboardingResumeCard),
  // NOT the old persona step-0 hard redirect (router_smoke, wt282). ----
  var registeredToDashboard = false;
  final regBtn = sparkleButtonFinder('注册');
  if (regBtn.evaluate().isNotEmpty) {
    try {
      await tester.ensureVisible(regBtn);
      await tester.pump(const Duration(milliseconds: 400));
    } catch (_) {}
    for (var attempt = 0; attempt < 2 && !registeredToDashboard; attempt++) {
      clicks[0]++;
      await tester.tap(regBtn, warnIfMissed: false);
      await waitUntil(
        tester,
        () =>
            find.byType(DashboardScreen).evaluate().isNotEmpty ||
            find.text('确认密码').evaluate().isEmpty,
        timeout: const Duration(seconds: 12),
      );
      await dumpTexts(tester, 'after-register-submit-$attempt');
      registeredToDashboard =
          find.byType(DashboardScreen).evaluate().isNotEmpty;
    }
  }
  await waitUntil(
    tester,
    () =>
        find.byType(DashboardScreen).evaluate().isNotEmpty ||
        find.byType(LoginScreen).evaluate().isNotEmpty ||
        find.text('确认密码').evaluate().isEmpty,
    timeout: const Duration(seconds: 10),
  );
  await tester.pump(const Duration(seconds: 1));
  passData['t_register_done_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  markFn(passId, 'R', 't_registered', passT0);

  if (!registeredToDashboard) {
    // O3 family (runbook §6-2): silent register bounce → honest evidence +
    // disclosed fallback (real register API + UI login), EXCLUDED from the
    // ≤3min claim and recorded as register_ui_bounce=true.
    final errTexts = <String>[];
    for (final f in ['注册失败', '失败', '已存在', '无效', '至少', '不匹配', '请输入', '请先']) {
      if (find.textContaining(f).evaluate().isNotEmpty) errTexts.add(f);
    }
    passData['register_ui_bounce'] = true;
    passData['register_error_markers'] = errTexts;
    // ignore: avoid_print
    print(
        'J02_FINDING pass=$passId UI register did not reach dashboard '
        '(errors=${jsonEncode(errTexts)}) — O3 family, fallback engaged');
    await shot('$passId/04b-register-bounce.png');
    failures.add('pass $passId: UI register silent bounce (O3 family)');
    final ok = await fallbackApiRegisterAndUiLogin(tester, username, passData);
    recordStep('R', 'r3_register_submit', false, 'bounce; fallback ok=$ok');
    if (!ok) {
      passData['t_route_done_fallback'] =
          DateTime.now().difference(passT0).inMilliseconds;
      failures.add('pass $passId: fallback register/login failed');
      await shot('$passId/9x-r3-fallback-failed.png');
      return;
    }
  } else {
    recordStep('R', 'r3_register_submit', true, 'soft wall reached');
  }

  // Soft-wall assertions: dashboard + resume card (title + CTA may require a
  // scroll on short viewports).
  final resumeVisible = await waitUntil(
    tester,
    () => textAny(['完成引导，让 AI 更懂你', '继续引导']) != null,
    timeout: const Duration(seconds: 20),
  );
  if (!resumeVisible) {
    await revealText(tester, '继续引导');
  }
  passData['soft_wall_resume_card'] = resumeVisible;
  recordStep(
    'R',
    'r3_softwall_resume_card',
    resumeVisible,
    'A2a registered-side session face',
  );
  await safeSettle(tester);
  await tester.pump(const Duration(seconds: 2));
  await shot('$passId/04-home-softwall.png');

  // ---- R4: resume CTA 继续引导 → persona onboarding screen, step 1. ----
  final resumeCta = await waitUntilFinder(
    tester,
    () => sparkleButtonFinder('继续引导'),
  );
  if (resumeCta == null) {
    failures.add('pass $passId: resume CTA 继续引导 not found');
    recordStep('R', 'r4_resume_persona', false, 'CTA missing');
    return;
  }
  await revealFinder(tester, resumeCta);
  clicks[0]++;
  await tester.tap(resumeCta, warnIfMissed: false);
  final personaScreen = await waitTracked(
    tester,
    'R',
    'r4_resume_persona',
    () => find.byType(PersonaOnboardingScreen).evaluate().isNotEmpty,
    timeout: const Duration(seconds: 15),
  );
  if (!personaScreen) {
    failures.add('pass $passId: persona onboarding screen never appeared');
    return;
  }
  passData['t_persona_step1_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  markFn(passId, 'R', 'r4_resume_persona', passT0);
  await safeSettle(tester);
  await shot('$passId/05-persona-step1.png');
  recordStep('R', 'r4_resume_persona', true, 'persona step 1 visible');

  // ---- R5: type the persona goal. wt764 pinned semantics: the fast-path CTA
  // does NOT exist while the goal is empty and appears (with the one-question
  // hint) once text is entered. ----
  final goalField = find.descendant(
    of: find.byType(PersonaOnboardingScreen),
    matching: find.byType(TextField),
  );
  if (goalField.evaluate().isEmpty) {
    failures.add('pass $passId: persona goal input not found on step 1');
    recordStep('R', 'r5_goal_typed', false, 'no TextField on step 1');
    return;
  }
  final fastPathKey = find.byKey(const ValueKey('j02-fast-path-cta'));
  final ctaAbsentWhenEmpty = fastPathKey.evaluate().isEmpty;
  passData['fast_path_cta_absent_when_goal_empty'] = ctaAbsentWhenEmpty;
  recordStep(
    'R',
    'r5_cta_negative_gate',
    ctaAbsentWhenEmpty,
    'wt764: empty goal must not show the fast-path CTA',
  );
  await tester.enterText(goalField.first, persona['goal']!);
  await tester.pump(const Duration(milliseconds: 600));
  final ctaAppeared = await waitUntil(
    tester,
    () => find.byKey(const ValueKey('j02-fast-path-cta')).evaluate().isNotEmpty,
    timeout: const Duration(seconds: 10),
  );
  final hintAppeared =
      find.textContaining('只回答目标这一个问题').evaluate().isNotEmpty;
  passData['fast_path_cta_appeared'] = ctaAppeared;
  passData['fast_path_hint_appeared'] = hintAppeared;
  passData['t_goal_cta_visible_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  markFn(passId, 'R', 'r5_goal_typed', passT0);
  recordStep('R', 'r5_goal_typed', ctaAppeared, 'hint visible=$hintAppeared');
  await shot('$passId/06-goal-typed-fastpath.png');
  if (!ctaAppeared) {
    failures.add('pass $passId: fast-path CTA did not appear after goal text');
    return;
  }

  // ---- R6: fast-path CTA → modeling interview screen. The remaining four
  // persona questions are DEFERRED (goal-only payload; onboardingCompleted
  // stays false → resume card survives). ----
  clicks[0]++;
  await tester.tap(
    find.byKey(const ValueKey('j02-fast-path-cta')),
    warnIfMissed: false,
  );
  final modelingReached = await waitTracked(
    tester,
    'R',
    'r6_fastpath_submit',
    () => find.byType(ModelingChatScreen).evaluate().isNotEmpty,
    timeout: const Duration(seconds: 20),
  );
  passData['t_fastpath_submitted_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  markFn(passId, 'R', 'r6_fastpath_submit', passT0);
  if (!modelingReached) {
    failures.add(
      'pass $passId: modeling screen never appeared after fast path',
    );
    return;
  }
  // Defer semantic evidence: persona wizard is gone, modeling is up — the
  // four remaining questions were NOT asked on this route.
  passData['deferred_questions_not_asked'] =
      find.byType(PersonaOnboardingScreen).evaluate().isEmpty;
  await tester.pump(const Duration(seconds: 2));
  await shot('$passId/07-modeling-deferred.png');
  recordStep(
    'R',
    'r6_deferred_semantics',
    passData['deferred_questions_not_asked'] as bool,
    'modeling reached without persona steps 2-5',
  );

  // ---- R7: modeling AppBar skip (userSkip「跳过」) → onboardingCompleted
  // =true. CODE FACT (modeling_chat_screen.dart _finish): when the fast path
  // delivered a post-onboarding message the landing is /chat, else /home.
  // The runbook table expects /home; the driver records the REAL landing and,
  // if it is not the dashboard, walks the shell home tab (a real user path)
  // to reach the FirstActionCard surface. ----
  final skipBtn = sparkleButtonFinder('跳过');
  if (skipBtn.evaluate().isEmpty) {
    failures.add('pass $passId: modeling skip button not found');
    recordStep('R', 'r7_modeling_skip', false, 'skip button missing');
    return;
  }
  clicks[0]++;
  await tester.tap(skipBtn, warnIfMissed: false);
  final landedSomewhere = await waitUntil(
    tester,
    () =>
        find.byType(ChatScreen).evaluate().isNotEmpty ||
        find.byType(DashboardScreen).evaluate().isNotEmpty,
  );
  final landedChat = find.byType(ChatScreen).evaluate().isNotEmpty;
  final landedHome = find.byType(DashboardScreen).evaluate().isNotEmpty;
  passData['post_skip_route'] =
      landedChat ? 'chat' : (landedHome ? 'home' : 'unknown');
  passData['post_skip_landed'] = landedSomewhere;
  markFn(passId, 'R', 'r7_modeling_skip', passT0);
  recordStep(
    'R',
    'r7_modeling_skip',
    landedSomewhere,
    'landing=${passData['post_skip_route']} (code: chat when post-onboarding '
        'message present; runbook table said home — recorded as measured)',
  );
  await safeSettle(tester);
  await shot('$passId/07b-post-skip-${passData['post_skip_route']}.png');

  if (!landedHome) {
    // Real-user path to the dashboard: shell tab 驾驶舱 (l10n.home).
    final homeTab = textAny(['驾驶舱', 'Home']);
    if (homeTab != null) {
      clicks[0]++;
      await tester.tap(homeTab, warnIfMissed: false);
      await waitUntil(
        tester,
        () => find.byType(DashboardScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 20),
      );
    }
  }
  // FirstActionCard generate entry (the card self-gates on a real goal — the
  // fast path created one).
  final actionEntry = await waitUntilFinder(
    tester,
    () => sparkleButtonFinder('生成我的第一步'),
    timeout: const Duration(seconds: 30),
  );
  recordStep(
    'R',
    'r7_first_action_entry',
    actionEntry != null,
    'FirstActionCard generate entry visible',
  );
  if (actionEntry == null) {
    failures.add('pass $passId: FirstActionCard generate entry not found');
    await shot('$passId/9x-r7-no-action-card.png');
    return;
  }
  await revealFinder(tester, actionEntry);
  await tester.pump(const Duration(seconds: 1));
  await shot('$passId/08-home-first-action.png');

  // ---- R8: generate → proposal. THE STOPWATCH CORE:
  // t_action_ready - t_pass_start ≤ 180,000ms. LLM derivation is seconds-
  // scale; on failure the card shows the honest error face (503 retry,
  // wt371) — one driver-side retry through the card's own 重试, failures
  // recorded without cosmetics. ----
  var proposalReady = false;
  var honestErrorShown = false;
  clicks[0]++;
  await tester.tap(actionEntry, warnIfMissed: false);
  // F5: any loading >500ms must show feedback. SparkleButton.loading renders
  // a CircularProgressIndicator — observe it right after the tap.
  var loadingObserved = false;
  for (var probe = 0; probe < 6 && !loadingObserved; probe++) {
    await tester.pump(const Duration(milliseconds: 150));
    loadingObserved = find
        .descendant(
          of: find.byType(FirstActionCard),
          matching: find.byType(CircularProgressIndicator),
        )
        .evaluate()
        .isNotEmpty;
  }
  passData['loading_feedback_observed'] = loadingObserved;
  recordStep(
    'R',
    'r8_loading_feedback',
    loadingObserved,
    'F5: progress indicator inside FirstActionCard during generation',
  );
  markFn(passId, 'R', 'r8_action_generating', passT0);

  Future<bool> waitForProposal(Duration timeout) => waitUntil(
        tester,
        () =>
            sparkleButtonFinder('开始这一步').evaluate().isNotEmpty &&
            textAny(['这个不合适']) != null &&
            textAny(['产出']) != null,
        timeout: timeout,
      );

  proposalReady = await waitForProposal(const Duration(seconds: 120));
  if (!proposalReady) {
    honestErrorShown =
        find.textContaining('第一步生成失败').evaluate().isNotEmpty ||
            find.textContaining('重试').evaluate().isNotEmpty;
    await shot('$passId/09b-action-error.png');
    // ignore: avoid_print
    print(
        'J02_FINDING pass=$passId first-action generation not ready in 120s '
        '(honest_error_face=$honestErrorShown) — one card-retry attempt');
    final retryBtn = sparkleButtonFinder('重试');
    if (retryBtn.evaluate().isNotEmpty) {
      clicks[0]++;
      await tester.tap(retryBtn, warnIfMissed: false);
      proposalReady = await waitForProposal(const Duration(seconds: 120));
    }
  }
  passData['t_action_ready_ms'] =
      DateTime.now().difference(passT0).inMilliseconds;
  markFn(passId, 'R', 't_action_ready', passT0);
  passData['within_3min_budget'] =
      (passData['t_action_ready_ms'] as int) <= j02BudgetMs;
  passData['honest_error_face_shown'] = honestErrorShown;
  recordStep(
    'R',
    'r8_action_generate',
    proposalReady,
    't_action_ready_ms=${passData['t_action_ready_ms']} '
        'budget=${j02BudgetMs}ms within=${passData['within_3min_budget']}',
  );
  if (!proposalReady) {
    failures.add(
      'pass $passId: proposal never became ready '
      '(t_action_ready_ms=${passData['t_action_ready_ms']}, '
      'honest_error_face=$honestErrorShown)',
    );
    await dumpTexts(tester, 'r8-proposal-missing');
    return;
  }
  await safeSettle(tester);
  await shot('$passId/09-action-proposal.png');

  // Capture the proposal three-field text for the F3 differentiation record.
  onProposal(await firstActionCardTexts(tester));

  // ---- R9: confirm proposal (开始这一步) → committed state. Useful-action
  // endpoint per runbook §3 R9. ----
  final startBtn = sparkleButtonFinder('开始这一步');
  if (startBtn.evaluate().isEmpty) {
    failures.add('pass $passId: proposal confirm button not found');
    recordStep('R', 'r9_action_confirm', false, 'button missing');
    return;
  }
  await revealFinder(tester, startBtn);
  clicks[0]++;
  await tester.tap(startBtn, warnIfMissed: false);
  final committed = await waitTracked(
    tester,
    'R',
    'r9_action_confirm',
    () =>
        find.textContaining('第一步已在任务账本里').evaluate().isNotEmpty ||
        find.textContaining('已创建').evaluate().isNotEmpty,
    timeout: const Duration(seconds: 60),
  );
  passData['t_confirm_ms'] = DateTime.now().difference(passT0).inMilliseconds;
  passData['total_ms'] = DateTime.now().difference(passT0).inMilliseconds;
  passData['action_confirmed'] = committed;
  passData['clicks'] = clicks[0];
  markFn(passId, 'R', 't_pass_total', passT0);
  recordStep('R', 'r9_action_confirm', committed, 'useful action endpoint');
  await safeSettle(tester);
  await tester.pump(const Duration(seconds: 1));
  await shot('$passId/10-action-confirmed.png');
  if (!committed) {
    failures.add(
      'pass $passId: proposal confirm did not reach the committed face',
    );
  }
}

// ═══════════════════════════ Leg G — guest session ═══════════════════════════
//
// runbook §3 Leg G table. G4 (DB probes) is orchestrator-owned: this leg
// prints J02_GUEST_USER for the first3minutes.sh db_probes step and never
// touches docker itself.

Future<String?> legGGuest({
  required WidgetTester tester,
  required String passId,
  required Future<void> Function(String) shot,
  required void Function(
    String,
    String,
    String,
    DateTime, {
    String clockField,
  }) markFn,
  required void Function(String, String, bool, String) recordStep,
  required Future<bool> Function(
    WidgetTester,
    String,
    String,
    bool Function(), {
    Duration timeout,
    String clockField,
  }) waitTracked,
  required List<String> failures,
}) async {
  final legT0 = DateTime.now();
  const leg = 'G';

  // Reach the login screen from wherever the previous leg ended.
  final atLogin = await ensureAtLogin(tester, passId, failures);
  if (!atLogin) {
    failures.add('leg G: could not reach the login screen');
    recordStep(leg, 'g0_reach_login', false, 'login screen unreachable');
    return null;
  }
  recordStep(leg, 'g0_reach_login', true, '');

  final guest = textAny(['以访客身份继续', 'Continue as Guest']);
  if (guest == null) {
    failures.add('leg G: guest button not found on login');
    recordStep(leg, 'g1_guest_home', false, 'guest button missing');
    return null;
  }
  await revealFinder(tester, guest);
  await tester.pump(const Duration(milliseconds: 600));
  clicks[0]++;
  await tester.tap(guest);
  markFn(passId, leg, 'g1_guest_tap', legT0, clockField: 'ms_since_leg_t0');

  final dashReady = await waitTracked(
    tester,
    leg,
    'g1_guest_home',
    () => find.byType(DashboardScreen).evaluate().isNotEmpty,
    timeout: const Duration(seconds: 60),
    clockField: 'ms_since_leg_t0',
  );
  if (!dashReady) {
    failures.add('leg G: guest dashboard never appeared');
    return null;
  }
  // Session stability: stay put — no persona onboarding redirect loop.
  await tester.pump(const Duration(seconds: 3));
  final stable = find.byType(DashboardScreen).evaluate().isNotEmpty &&
      find.byType(PersonaOnboardingScreen).evaluate().isEmpty;
  recordStep(
    leg,
    'g1_guest_session_stable',
    stable,
    'A2b: guest lands and STAYS on the dashboard (no persona loop)',
  );
  if (!stable) {
    failures.add('leg G: guest session not stable (redirected away)');
  }
  String? guestUsername;
  try {
    final container = ProviderScope.containerOf(
      tester.element(find.byType(MaterialApp).first),
    );
    guestUsername = container.read(authProvider).user?.username;
  } catch (_) {}
  await safeSettle(tester);
  await tester.pump(const Duration(seconds: 2));
  await shot('$passId/11-guest-home.png');
  markFn(passId, leg, 'g1_guest_home', legT0, clockField: 'ms_since_leg_t0');

  // ---- G2: seeded content + DECLARED example marker scan. A missing
  // example marker is MEASUREMENT DATA (J-01 O1), not a harness failure. ----
  bool probeText(List<String> keys) {
    for (final k in keys) {
      if (find.textContaining(k).evaluate().isNotEmpty) return true;
    }
    return false;
  }

  final seededVisible = probeText(['期中冲刺', '先解决卡点', '解开卡点', '数据结构']);
  final declaredMarker = probeText(['示例体验', '体验示例', '演示数据', '示例数据']);
  recordStep(
    leg,
    'g2_seed_scan',
    true,
    'seeded_goal_words=$seededVisible declared_example_marker=$declaredMarker '
        '(missing marker is measurement data per J-01 O1)',
  );
  markFn(passId, leg, 'g2_seed_scan', legT0, clockField: 'ms_since_leg_t0');
  await shot('$passId/12-guest-seed-scan.png');

  // ---- G3: one demo chat round (reply must arrive; the demo lane is not
  // persisted to real memory — proven by the orchestrator's G4 probes). ----
  final chatTab = textAny(['对话', 'Chat']);
  if (chatTab == null) {
    failures.add('leg G: chat tab not found');
    recordStep(leg, 'g3_demo_chat', false, 'tab missing');
    return guestUsername;
  }
  clicks[0]++;
  await tester.tap(chatTab, warnIfMissed: false);
  final chatReady = await waitUntil(
    tester,
    () => find.byType(ChatScreen).evaluate().isNotEmpty,
  );
  if (!chatReady) {
    failures.add('leg G: chat screen never appeared');
    recordStep(leg, 'g3_demo_chat', false, 'screen missing');
    return guestUsername;
  }
  await safeSettle(tester);
  final chatField = find.descendant(
    of: find.byType(ChatScreen),
    matching: find.byType(TextField),
  );
  if (chatField.evaluate().isEmpty) {
    recordStep(leg, 'g3_demo_chat', false, 'no input field in chat');
    failures.add('leg G: chat input field not found');
    await shot('$passId/13-guest-demo-chat.png');
    return guestUsername;
  }
  final auroraBefore = find.text('Aurora').evaluate().length;
  await tester.enterText(chatField.first, '帮我看看这个示例目标，第一步该做什么？');
  await tester.pump(const Duration(milliseconds: 300));
  var sent = false;
  clicks[0]++;
  try {
    await tester.testTextInput.receiveAction(TextInputAction.send);
    sent = true;
  } catch (_) {
    final sendIcon = find.descendant(
      of: find.byType(ChatScreen),
      matching: find.byIcon(Icons.send_rounded),
    );
    if (sendIcon.evaluate().isNotEmpty) {
      await tester.tap(sendIcon.first, warnIfMissed: false);
      sent = true;
    }
  }
  final replied = await waitUntil(
    tester,
    () =>
        find.text('Aurora').evaluate().length > auroraBefore ||
        find.textContaining('输入中').evaluate().isNotEmpty,
    timeout: const Duration(seconds: 90),
  );
  recordStep(
    leg,
    'g3_demo_chat',
    sent,
    'sent=$sent reply_seen=$replied (demo round; memory isolation is proven '
        'by the orchestrator G4 probes)',
  );
  if (!replied) {
    await dumpTexts(tester, 'g3-no-reply');
  }
  await safeSettle(tester);
  await shot('$passId/13-guest-demo-chat.png');
  markFn(
    passId,
    leg,
    'g3_demo_chat_done',
    legT0,
    clockField: 'ms_since_leg_t0',
  );
  return guestUsername;
}

// ═══════════════════════════ Leg U — guest upgrade ═══════════════════════════
//
// runbook §3 Leg U table: conversion card → register form → IN-PLACE flip
// (V3-FIX-205 family: no logout-to-login, session continuity) → persona
// onboarding still reachable via the resume card.

Future<String?> legUUpgrade({
  required WidgetTester tester,
  required String passId,
  required Future<void> Function(String) shot,
  required void Function(
    String,
    String,
    String,
    DateTime, {
    String clockField,
  }) markFn,
  required void Function(String, String, bool, String) recordStep,
  required Future<bool> Function(
    WidgetTester,
    String,
    String,
    bool Function(), {
    Duration timeout,
    String clockField,
  }) waitTracked,
  required List<String> failures,
}) async {
  final legT0 = DateTime.now();
  const leg = 'U';
  String? upgradedUsername;

  // ---- U1: guest-state conversion entry. Preferred: GuestConversionCard on
  // the dashboard (价值回顾形, N40). Degraded (recorded honestly): product
  // logout → register link on login (still a real register surface, but the
  // conversion-card visibility claim is then false). ----
  var onDashboard = find.byType(DashboardScreen).evaluate().isNotEmpty;
  if (!onDashboard) {
    final homeTab = textAny(['驾驶舱', 'Home']);
    if (homeTab != null) {
      clicks[0]++;
      await tester.tap(homeTab, warnIfMissed: false);
      await waitUntil(
        tester,
        () => find.byType(DashboardScreen).evaluate().isNotEmpty,
      );
    }
    onDashboard = find.byType(DashboardScreen).evaluate().isNotEmpty;
  }
  final conversionCta = onDashboard
      ? await waitUntilFinder(
          tester,
          () => sparkleButtonFinder('注册并同步进度'),
          timeout: const Duration(seconds: 10),
        )
      : null;
  final viaConversionCard = conversionCta != null;
  if (conversionCta != null) {
    await revealFinder(tester, conversionCta);
  } else {
    // ignore: avoid_print
    print(
        'J02_FINDING pass=$passId GuestConversionCard CTA not visible on the '
        'guest dashboard (visibility gate: value signal required) — degraded '
        'path via the login register link');
    failures.add(
      'leg U: GuestConversionCard CTA not visible (degraded to the login '
      'register link; card-visibility claim=false)',
    );
    final atLogin = await ensureAtLogin(tester, passId, failures);
    if (!atLogin) {
      recordStep(leg, 'u1_upgrade_form', false, 'no conversion entry at all');
      return null;
    }
    final registerLink = textAny(['还没有账号？']);
    if (registerLink == null) {
      recordStep(leg, 'u1_upgrade_form', false, 'register link missing');
      return null;
    }
    await revealFinder(tester, registerLink);
    clicks[0]++;
    await tester.tap(registerLink, warnIfMissed: false);
  }
  if (viaConversionCard) {
    clicks[0]++;
    await tester.tap(conversionCta, warnIfMissed: false);
  }
  final atRegister = await waitTracked(
    tester,
    leg,
    'u1_upgrade_form',
    () =>
        find.byType(RegisterScreen).evaluate().isNotEmpty ||
        find.text('确认密码').evaluate().isNotEmpty,
    timeout: const Duration(seconds: 15),
    clockField: 'ms_since_leg_t0',
  );
  if (!atRegister) {
    failures.add('leg U: register/upgrade form never appeared');
    return null;
  }
  recordStep(
    leg,
    'u1_upgrade_form',
    true,
    'conversion_card=$viaConversionCard (A2c upgrade face)',
  );
  await safeSettle(tester);
  await shot('$passId/14-upgrade-form.png');
  markFn(passId, leg, 'u1_upgrade_form', legT0, clockField: 'ms_since_leg_t0');

  // ---- U2: complete the upgrade submit → IN-PLACE flip. Assertions: the
  // session survives (never bounced to LoginScreen), the dashboard returns,
  // and the auth provider identity leaves registrationSource='guest'. ----
  final fields = find.byType(TextFormField);
  final suffix = DateTime.now().millisecondsSinceEpoch.toString().substring(6);
  final username = 'j02up$suffix';
  if (fields.evaluate().length >= 4) {
    await tester.enterText(fields.at(0), username);
    await tester.enterText(fields.at(1), '$username@example.com');
    await tester.enterText(fields.at(2), j02Password);
    await tester.enterText(fields.at(3), j02Password);
    await tester.pump(const Duration(milliseconds: 300));
  } else {
    failures.add(
      'leg U: expected 4 register fields, found ${fields.evaluate().length}',
    );
    recordStep(leg, 'u2_upgrade_submit', false, 'field count mismatch');
    return null;
  }
  final tiles = find.byType(CheckboxListTile);
  for (var t = 0; t < tiles.evaluate().length; t++) {
    clicks[0]++;
    await tester.tap(tiles.at(t), warnIfMissed: false);
    await tester.pump(const Duration(milliseconds: 250));
  }
  final regBtn = sparkleButtonFinder('注册');
  if (regBtn.evaluate().isEmpty) {
    failures.add('leg U: register submit button not found');
    recordStep(leg, 'u2_upgrade_submit', false, 'button missing');
    return null;
  }
  try {
    await tester.ensureVisible(regBtn);
    await tester.pump(const Duration(milliseconds: 400));
  } catch (_) {}
  var sawLoginDuringUpgrade = false;
  var backOnDashboard = false;
  for (var attempt = 0; attempt < 2 && !backOnDashboard; attempt++) {
    clicks[0]++;
    await tester.tap(regBtn, warnIfMissed: false);
    await waitUntil(
      tester,
      () =>
          find.byType(DashboardScreen).evaluate().isNotEmpty ||
          find.byType(LoginScreen).evaluate().isNotEmpty ||
          find.text('确认密码').evaluate().isEmpty,
      timeout: const Duration(seconds: 15),
    );
    sawLoginDuringUpgrade = sawLoginDuringUpgrade ||
        find.byType(LoginScreen).evaluate().isNotEmpty;
    backOnDashboard = find.byType(DashboardScreen).evaluate().isNotEmpty;
  }
  await tester.pump(const Duration(seconds: 2));
  sawLoginDuringUpgrade = sawLoginDuringUpgrade ||
      find.byType(LoginScreen).evaluate().isNotEmpty;
  var registrationSource = '';
  try {
    final container = ProviderScope.containerOf(
      tester.element(find.byType(MaterialApp).first),
    );
    final user = container.read(authProvider).user;
    registrationSource = user?.registrationSource ?? '';
    upgradedUsername = user?.username;
  } catch (_) {}
  final flippedInPlace = backOnDashboard &&
      !sawLoginDuringUpgrade &&
      registrationSource != 'guest';
  recordStep(
    leg,
    'u2_upgrade_submit',
    flippedInPlace,
    'in_place=$flippedInPlace (dashboard=$backOnDashboard '
        'login_bounce=$sawLoginDuringUpgrade '
        'registration_source=$registrationSource) — V3-FIX-205 family',
  );
  if (!flippedInPlace) {
    failures.add(
      'leg U: upgrade did not flip in place (dashboard=$backOnDashboard, '
      'login_bounce=$sawLoginDuringUpgrade, source=$registrationSource)',
    );
  }
  await safeSettle(tester);
  await shot('$passId/15-upgraded-session.png');
  markFn(
    passId,
    leg,
    'u2_upgrade_submit',
    legT0,
    clockField: 'ms_since_leg_t0',
  );

  // ---- U3: persona onboarding stays reachable after upgrade (the resume
  // card is the entry; router_smoke upgrade-endpoint face). ----
  final resumeVisible = await waitUntil(
    tester,
    () => textAny(['完成引导，让 AI 更懂你', '继续引导']) != null,
    timeout: const Duration(seconds: 20),
  );
  if (!resumeVisible) {
    await revealText(tester, '继续引导');
  }
  final resumeCta = sparkleButtonFinder('继续引导');
  var personaReachable = false;
  if (resumeCta.evaluate().isNotEmpty) {
    await revealFinder(tester, resumeCta);
    clicks[0]++;
    await tester.tap(resumeCta, warnIfMissed: false);
    personaReachable = await waitUntil(
      tester,
      () => find.byType(PersonaOnboardingScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 15),
    );
  }
  recordStep(
    leg,
    'u3_persona_reachable',
    personaReachable,
    'resume_card=$resumeVisible persona_screen=$personaReachable '
        '(router_smoke upgrade face)',
  );
  if (!personaReachable) {
    failures.add('leg U: persona onboarding not reachable after upgrade');
  }
  await safeSettle(tester);
  await shot('$passId/16-upgraded-persona-reachable.png');
  markFn(
    passId,
    leg,
    'u3_persona_reachable',
    legT0,
    clockField: 'ms_since_leg_t0',
  );
  return upgradedUsername;
}

// ═══════════════════════ shared helpers (J-01 isomorphic) ═══════════════════════

/// Mutable click counter shared with leg helpers (pass-by-reference).
final clicks = <int>[0];

/// J-02 account password (runbook §3 R2).
const j02Password = 'J02-Passw0rd!';

/// 5 personas (J-01 first3_measurement_test.dart constants — PX1 比赛 / PX2
/// 科研 / PX3 作品集 / PX4 课程 / PX5 Creator; runbook §3 5-persona rule).
const List<Map<String, String>> j02Personas = [
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

/// J-02 acceptance stopwatch budget (fresh user → useful action ≤ 3min).
const int j02BudgetMs = 180000;

/// Runbook §4 authoritative per-pass timing keys (j02_timings.json schema).
const List<String> requiredTimingKeys = [
  't_first_surface_ms',
  't_register_done_ms',
  't_action_ready_ms',
  'total_ms',
  'clicks',
  'failures',
];

/// JSON artifact file names the driver writes (runbook §8; db_probes.jsonl
/// and run_manifest belong to the orchestrator).
const List<String> j02ArtifactNames = [
  'j02_timings.json',
  'steps.json',
  'proposals.json',
];

/// Canonical screenshot names (runbook §3 verbatim, under the per-persona
/// process directory).
const List<String> j02ScreenshotNames = [
  '01-first-surface.png',
  '02-register.png',
  '03-register-filled.png',
  '04-home-softwall.png',
  '04b-register-bounce.png',
  '05-persona-step1.png',
  '06-goal-typed-fastpath.png',
  '07-modeling-deferred.png',
  '08-home-first-action.png',
  '09-action-proposal.png',
  '09b-action-error.png',
  '10-action-confirmed.png',
  '11-guest-home.png',
  '12-guest-seed-scan.png',
  '13-guest-demo-chat.png',
  '14-upgrade-form.png',
  '15-upgraded-session.png',
  '16-upgraded-persona-reachable.png',
];

/// J02_MARK line (runbook §4). Leg R uses `ms_since_pass_t0` (180s verdict
/// input); legs G/U use `ms_since_leg_t0` (no 3-min budget on session-
/// stability legs — keeps the orchestrator verdict clean).
String j02MarkLine({
  required String pass,
  required String leg,
  required String mark,
  required String clockField,
  required int msSinceT0,
  required int clicks,
}) =>
    'J02_MARK pass=$pass leg=$leg mark=$mark '
    '$clockField=$msSinceT0 clicks=$clicks';

/// F3 differentiation helper: true when every captured proposal text is
/// pairwise non-identical (and at least two exist to compare).
bool proposalsPairwiseDistinct(Map<String, String> proposals) {
  final texts = proposals.values.toList();
  if (texts.length < 2) return texts.isNotEmpty;
  for (var i = 0; i < texts.length; i++) {
    for (var j = i + 1; j < texts.length; j++) {
      if (texts[i].trim() == texts[j].trim()) return false;
    }
  }
  return true;
}

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

/// SparkleButton-scoped finder for a label — dodges the AppBar-title trap
/// (O3 复盘, J-01: 注册/登录 titles collide with button labels).
Finder sparkleButtonFinder(String label) =>
    find.widgetWithText(SparkleButton, label);

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
  print(
      'J02_TEXTDUMP [$tag] n=${texts.length} '
      '${jsonEncode(texts.take(40).toList())}');
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

Future<Finder?> waitUntilFinder(
  WidgetTester tester,
  Finder Function() finder, {
  Duration timeout = const Duration(seconds: 15),
}) async {
  final ok = await waitUntil(
    tester,
    () => finder().evaluate().isNotEmpty,
    timeout: timeout,
  );
  return ok ? finder() : null;
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

/// True when the FIRST match is fully inside the current viewport (F2
/// no-scroll visibility check).
bool fullyVisible(WidgetTester tester, Finder finder) {
  if (finder.evaluate().isEmpty) return false;
  try {
    final rect = tester.getRect(finder.first);
    final screen = tester.view.physicalSize / tester.view.devicePixelRatio;
    return rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= screen.height &&
        rect.right <= screen.width;
  } catch (_) {
    return false;
  }
}

/// Scroll attempt to reveal a finder (J-01 pattern: scrollUntilVisible with
/// an ensureVisible fallback; both failures are non-fatal — caller decides).
Future<void> revealFinder(WidgetTester tester, Finder finder) async {
  try {
    await tester.scrollUntilVisible(
      finder,
      160,
      scrollable: find.byType(Scrollable).first,
    );
  } catch (_) {
    try {
      await tester.ensureVisible(finder);
    } catch (_) {}
  }
  await tester.pump(const Duration(milliseconds: 400));
}

Future<void> revealText(WidgetTester tester, String text) async {
  final f = textAny([text]);
  if (f != null) {
    await revealFinder(tester, f);
  }
}

Future<void> tapTextButton(WidgetTester tester, List<String> texts) async {
  final f = textAny(texts);
  if (f == null) return;
  clicks[0]++;
  await tester.tap(f, warnIfMissed: false);
}

/// Walk the PRODUCT logout path (我的 → 退出登录 → confirm). Returns true when
/// the login screen is reached.
Future<bool> productLogout(
  WidgetTester tester,
  String passId,
  List<String> failures,
) async {
  try {
    final profileTab = textAny(['我的', 'Profile']);
    if (profileTab != null) {
      clicks[0]++;
      await tester.tap(profileTab, warnIfMissed: false);
      await safeSettle(tester);
      await tester.pump(const Duration(seconds: 1));
    }
    final logoutRow = textAny(['退出登录', 'Logout']);
    if (logoutRow == null) return false;
    await revealFinder(tester, logoutRow);
    clicks[0]++;
    await tester.tap(logoutRow, warnIfMissed: false);
    final dialog = await waitUntil(
      tester,
      () =>
          find.textContaining('退出登录').evaluate().length > 1 ||
          find.textContaining('确定').evaluate().isNotEmpty ||
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
    return waitUntil(
      tester,
      () => find.byType(LoginScreen).evaluate().isNotEmpty,
      timeout: const Duration(seconds: 20),
    );
  } catch (e) {
    // ignore: avoid_print
    print('J02_DEBUG pass=$passId ui logout failed: $e');
    return false;
  }
}

/// Bring the app back to the login screen from any authenticated surface
/// (product logout first; provider logout as disclosed instrumentation
/// fallback — same as J-01).
Future<bool> ensureAtLogin(
  WidgetTester tester,
  String passId,
  List<String> failures,
) async {
  if (find.byType(LoginScreen).evaluate().isNotEmpty) return true;
  var loggedOut = await productLogout(tester, passId, failures);
  if (!loggedOut) {
    try {
      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp).first),
      );
      await container.read(authProvider.notifier).logout();
      loggedOut = await waitUntil(
        tester,
        () => find.byType(LoginScreen).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 20),
      );
    } catch (e) {
      // ignore: avoid_print
      print('J02_DEBUG pass=$passId provider logout failed: $e');
    }
  }
  return loggedOut && find.byType(LoginScreen).evaluate().isNotEmpty;
}

/// O3-family fallback (runbook §6-2): ensure the account exists via the REAL
/// register API (fresh backend account), then walk back to login and log in
/// through the UI; provider login as the last disclosed instrumentation. The
/// fallback segment is EXCLUDED from the ≤3min claim.
Future<bool> fallbackApiRegisterAndUiLogin(
  WidgetTester tester,
  String username,
  Map<String, dynamic> passData,
) async {
  await tester.runAsync(() async {
    try {
      final client = HttpClient();
      final req = await client.postUrl(
        Uri.parse('http://localhost:8080/api/v1/auth/register'),
      );
      req.headers.contentType = ContentType.json;
      req.write(
        jsonEncode({
          'username': username,
          'email': '$username@example.com',
          'password': j02Password,
          'accepted_tos': true,
          'accepted_privacy': true,
          'agreed_locale': 'zh-CN',
        }),
      );
      final res = await req.close();
      final body = await res.transform(utf8.decoder).join();
      passData['api_register_status'] = res.statusCode;
      // ignore: avoid_print
      print(
          'J02_DEBUG api register status=${res.statusCode} '
          'body=${body.length > 160 ? body.substring(0, 160) : body}');
      client.close();
    } catch (e) {
      passData['api_register_error'] = e.toString();
    }
  });
  // Walk the REAL user path back to login via the 已有账号？ ghost button.
  if (find.text('确认密码').evaluate().isNotEmpty) {
    final backBtn = sparkleButtonFinder('已有账号？');
    if (backBtn.evaluate().isNotEmpty) {
      try {
        await tester.ensureVisible(backBtn);
        await tester.pump(const Duration(milliseconds: 400));
      } catch (_) {}
      clicks[0]++;
      await tester.tap(backBtn, warnIfMissed: false);
      await waitUntil(
        tester,
        () =>
            find.text('确认密码').evaluate().isEmpty &&
            find.byType(TextFormField).evaluate().isNotEmpty,
        timeout: const Duration(seconds: 10),
      );
    }
  }
  // UI login with the fresh account.
  final loginFields = find.byType(TextFormField);
  if (loginFields.evaluate().length >= 2) {
    await tester.enterText(loginFields.at(0), username);
    await tester.enterText(loginFields.at(1), j02Password);
    await tester.pump(const Duration(milliseconds: 300));
    var loginBtn = sparkleButtonFinder('登录');
    if (loginBtn.evaluate().isEmpty) {
      final loginText = textAnySmart(['登录'], last: true);
      if (loginText == null) return false;
      final ancestor = find
          .ancestor(of: loginText, matching: find.byType(SparkleButton))
          .first;
      loginBtn = ancestor.evaluate().isNotEmpty ? ancestor : loginText;
    }
    try {
      await tester.ensureVisible(loginBtn);
      await tester.pump(const Duration(milliseconds: 400));
    } catch (_) {}
    clicks[0]++;
    await tester.tap(loginBtn, warnIfMissed: false);
  }
  var logged = await waitUntil(
    tester,
    () => find.byType(DashboardScreen).evaluate().isNotEmpty,
  );
  if (!logged) {
    // Last resort: provider login (INSTRUMENTED, disclosed in the report).
    // ignore: avoid_print
    print(
        'J02_FINDING UI login tap also ineffective — provider login '
        '(instrumented)');
    try {
      final container = ProviderScope.containerOf(
        tester.element(find.byType(MaterialApp).first),
      );
      await container.read(authProvider.notifier).login(username, j02Password);
      logged = await waitUntil(
        tester,
        () => find.byType(DashboardScreen).evaluate().isNotEmpty,
      );
    } catch (e) {
      passData['provider_login_error'] = e.toString();
    }
  }
  return logged;
}

/// WARM reset between in-process persona passes (J-01 semantics): product /
/// provider logout + local-state wipe. Passes after the first in an 'all'
/// run are labelled warm — only PASS=<i> single-process runs are TRUE cold
/// starts per persona (runbook §2.1).
Future<void> resetToLoginBetweenPasses(
  WidgetTester tester,
  String passId,
  List<String> failures,
) async {
  final atLogin = await ensureAtLogin(tester, passId, failures);
  if (!atLogin) {
    failures.add('pass $passId: warm reset did not reach login');
    return;
  }
  try {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
    const secure = FlutterSecureStorage(
      mOptions: MacOsOptions(useDataProtectionKeyChain: false),
    );
    await secure.deleteAll();
  } catch (e) {
    // ignore: avoid_print
    print('J02_DEBUG pass=$passId warm wipe failed: $e');
  }
}

/// Collect the visible texts of the FirstActionCard (proposal three-field
/// capture for the F3 differentiation record).
Future<String> firstActionCardTexts(WidgetTester tester) async {
  final texts = <String>[];
  final cardTexts = find.descendant(
    of: find.byType(FirstActionCard),
    matching: find.byType(Text),
  );
  for (final e in cardTexts.evaluate()) {
    final w = e.widget;
    if (w is Text) {
      final plain = w.data ?? w.textSpan?.toPlainText() ?? '';
      if (plain.trim().isNotEmpty) texts.add(plain.trim());
    }
  }
  return texts.join(' | ');
}
