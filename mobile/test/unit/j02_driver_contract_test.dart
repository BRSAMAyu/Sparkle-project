import 'package:flutter_test/flutter_test.dart';

/// Contract pinning for the J-02 fast-path journey driver
/// (integration_test/j02_fastpath_journey_test.dart) — the pure, non-UI
/// surface is locked here so runbook drift is caught without a device:
///
///  * persona set (runbook §3 5-persona rule, F3),
///  * J02_MARK line format (runbook §4; the orchestrator first3minutes.sh
///    verdict greps `ms_since_pass_t0=(\d+)` and `pass=(\S+)` from it),
///  * artifact file names and the authoritative timing-key schema
///    (runbook §4/§8),
///  * screenshot name canon (runbook §3 verbatim),
///  * the 180,000ms stopwatch budget and the F3 pairwise-distinct rule.
///
/// This is a UNIT-level contract test only — the journey itself stays a
/// device-side integration test and is NEVER executed here.
import '../../integration_test/j02_fastpath_journey_test.dart' as driver;

void main() {
  group('J02 driver contract · personas (runbook §3 5-persona rule)', () {
    test('exactly 5 personas with unique ids and distinct goals', () {
      expect(driver.j02Personas, hasLength(5));
      final ids = driver.j02Personas.map((p) => p['id']!).toList();
      expect(ids, ['PX1', 'PX2', 'PX3', 'PX4', 'PX5']);
      final goals = driver.j02Personas.map((p) => p['goal']!).toSet();
      expect(goals.length, 5, reason: 'goals must be pairwise distinct');
      for (final p in driver.j02Personas) {
        expect(p['goal']!.length, greaterThanOrEqualTo(10));
        expect(p['name'], isNotEmpty);
        expect(p['arc'], isNotEmpty);
      }
    });
  });

  group('J02 driver contract · J02_MARK line (runbook §4)', () {
    test('leg R form uses ms_since_pass_t0 (orchestrator verdict input)', () {
      final line = driver.j02MarkLine(
        pass: 'PX1',
        leg: 'R',
        mark: 't_action_ready',
        clockField: 'ms_since_pass_t0',
        msSinceT0: 123456,
        clicks: 9,
      );
      expect(
        line,
        'J02_MARK pass=PX1 leg=R mark=t_action_ready '
        'ms_since_pass_t0=123456 clicks=9',
      );
      // first3minutes.sh verdict(): re.search(r"ms_since_pass_t0=(\d+)")
      // and re.search(r"pass=(\S+)") must both hit.
      expect(RegExp(r'ms_since_pass_t0=(\d+)').hasMatch(line), isTrue);
      expect(RegExp(r'pass=(\S+)').hasMatch(line), isTrue);
    });

    test('legs G/U form uses ms_since_leg_t0 (kept out of the 180s verdict)',
        () {
      final line = driver.j02MarkLine(
        pass: 'PX1',
        leg: 'G',
        mark: 'g1_guest_home',
        clockField: 'ms_since_leg_t0',
        msSinceT0: 3211,
        clicks: 2,
      );
      expect(
        line,
        'J02_MARK pass=PX1 leg=G mark=g1_guest_home '
        'ms_since_leg_t0=3211 clicks=2',
      );
      // The G/U marks must NOT be picked up by the 3-minute verdict.
      expect(RegExp(r'ms_since_pass_t0=(\d+)').hasMatch(line), isFalse);
    });
  });

  group('J02 driver contract · artifacts (runbook §4/§8)', () {
    test('authoritative per-pass timing keys are all present in the schema',
        () {
      expect(
        driver.requiredTimingKeys,
        containsAll(<String>[
          't_first_surface_ms',
          't_register_done_ms',
          't_action_ready_ms',
          'total_ms',
          'clicks',
          'failures',
        ]),
      );
      expect(driver.requiredTimingKeys, hasLength(6));
    });

    test('writes exactly the driver-owned artifact files', () {
      expect(
        driver.j02ArtifactNames,
        ['j02_timings.json', 'steps.json', 'proposals.json'],
      );
      // db_probes.jsonl / run_manifest.json belong to the orchestrator.
      expect(driver.j02ArtifactNames, isNot(contains('db_probes.jsonl')));
      expect(driver.j02ArtifactNames, isNot(contains('run_manifest.json')));
    });
  });

  group('J02 driver contract · screenshot canon (runbook §3 verbatim)', () {
    test('all named evidence shots exist in the canon', () {
      final canon = driver.j02ScreenshotNames.toSet();
      const legR = [
        '01-first-surface.png',
        '02-register.png',
        '03-register-filled.png',
        '04-home-softwall.png',
        '05-persona-step1.png',
        '06-goal-typed-fastpath.png',
        '07-modeling-deferred.png',
        '08-home-first-action.png',
        '09-action-proposal.png',
        '10-action-confirmed.png',
      ];
      const legG = [
        '11-guest-home.png',
        '12-guest-seed-scan.png',
        '13-guest-demo-chat.png',
      ];
      const legU = [
        '14-upgrade-form.png',
        '15-upgraded-session.png',
        '16-upgraded-persona-reachable.png',
      ];
      expect(canon, containsAll(legR));
      expect(canon, containsAll(legG));
      expect(canon, containsAll(legU));
      // Failure-evidence faces (runbook §3/§6: failures are recorded, never
      // papered over).
      expect(
        canon,
        containsAll(<String>[
          '04b-register-bounce.png',
          '09b-action-error.png',
        ]),
      );
    });
  });

  group('J02 driver contract · stopwatch + differentiation rules', () {
    test('budget is exactly the 3-minute acceptance bound', () {
      expect(driver.j02BudgetMs, 180000);
    });

    test('F3 pairwise-distinct rule: duplicates are flagged, uniques pass',
        () {
      expect(
        driver.proposalsPairwiseDistinct({
          'PX1': '整理算法可视化清单',
          'PX2': '跑通论文实验三',
          'PX3': '搭作品集首页',
        }),
        isTrue,
      );
      expect(
        driver.proposalsPairwiseDistinct({
          'PX1': '同一个模板化动作',
          'PX2': '同一个模板化动作',
        }),
        isFalse,
        reason: 'identical proposals = 模板化 action = F3 FAIL',
      );
      expect(
        driver.proposalsPairwiseDistinct({
          'PX1': '同一个',
          'PX2': '同一个 ',
        }),
        isFalse,
        reason: 'trim-only differences do not count as distinct',
      );
      // A single captured proposal cannot be compared in-process — the
      // cross-run comparison is the executor's job; empty means no data.
      expect(driver.proposalsPairwiseDistinct({'PX1': 'x'}), isTrue);
      expect(driver.proposalsPairwiseDistinct({}), isFalse);
    });
  });

  group('J02 driver contract · credentials', () {
    test('account password matches the runbook §3 R2 literal', () {
      expect(driver.j02Password, 'J02-Passw0rd!');
    });
  });
}
