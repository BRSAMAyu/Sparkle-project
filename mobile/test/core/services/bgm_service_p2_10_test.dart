import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const planEntry = BgmCatalogEntry(
    id: 'plan_soft',
    assetPath: 'audio/bgm/plan_soft.m4a',
    album: 'P2 Catalog',
    sceneTags: <String>['plan', 'task', 'structured'],
    paletteTags: <String>['adaptive'],
    energy: 0.24,
    density: 0.18,
    baseGain: 0.90,
    loopable: true,
    releaseApproved: true,
  );

  const taskEntry = BgmCatalogEntry(
    id: 'task_flow',
    assetPath: 'audio/bgm/task_flow.m4a',
    album: 'P2 Catalog',
    sceneTags: <String>['task', 'focus', 'structured'],
    paletteTags: <String>['adaptive'],
    energy: 0.30,
    density: 0.22,
    baseGain: 0.92,
    loopable: true,
    releaseApproved: true,
  );

  const focusEntry = BgmCatalogEntry(
    id: 'focus_deep',
    assetPath: 'audio/bgm/focus_deep.m4a',
    album: 'P2 Catalog',
    sceneTags: <String>['focus', 'deep', 'minimal'],
    paletteTags: <String>['adaptive'],
    energy: 0.18,
    density: 0.12,
    baseGain: 0.86,
    loopable: true,
    releaseApproved: true,
  );

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'bgm.enabled': true,
      'bgm.palette': 'adaptive',
      'bgm.mode': 'adaptive',
      'bgm.intensity': 'gentle',
      'bgm.variety': 'balanced',
    });
    await BgmService.debugResetState();
    BgmService.debugSetCatalogEntries(const <BgmCatalogEntry>[
      planEntry,
      taskEntry,
      focusEntry,
    ]);
  });

  tearDown(BgmService.debugResetState);

  test('preferences clamp volume and persist mode and tuning choices',
      () async {
    await BgmService.setVolume(1.8);
    await BgmService.setMode(BgmMode.focusOnly);
    await BgmService.setUserTuning(
      const BgmUserTuning(
        intensity: BgmIntensity.lush,
        variety: BgmVariety.dynamic,
        readingProtection: false,
        focusPriority: false,
        lockCurrentStyle: true,
      ),
    );

    final tuning = await BgmService.getUserTuning();

    expect(await BgmService.getVolume(), 1);
    expect(await BgmService.getMode(), BgmMode.focusOnly);
    expect(tuning.intensity, BgmIntensity.lush);
    expect(tuning.variety, BgmVariety.dynamic);
    expect(tuning.readingProtection, isFalse);
    expect(tuning.focusPriority, isFalse);
    expect(tuning.lockCurrentStyle, isTrue);
  });

  test('focusOnly mode suppresses non-focus route selections', () async {
    await BgmService.setMode(BgmMode.focusOnly);
    BgmService.activate(BgmTrack.plan);

    final snapshot = await BgmService.currentPlaybackSnapshot();

    expect(snapshot.track, isNull);
    expect(snapshot.enabled, isTrue);
  });

  test('focusOnly mode still resolves focus-critical route selections',
      () async {
    await BgmService.setMode(BgmMode.focusOnly);

    final assetPath = await BgmService.debugResolveSelectionAssetPath(
      BgmTrack.focus,
    );

    expect(assetPath, focusEntry.assetPath);
  });

  test('higher-priority component route wins over route registration',
      () async {
    final routeToken = BgmService.activate(BgmTrack.plan);
    final componentToken = BgmService.activate(
      BgmTrack.task,
      priority: BgmPriority.component,
    );
    addTearDown(() async {
      await BgmService.deactivate(routeToken);
      await BgmService.deactivate(componentToken);
    });

    final reason = await BgmService.debugResolveSelectionReason(BgmTrack.task);
    final taskProfile = BgmService.debugSceneProfileForTrack(BgmTrack.task);

    expect(taskProfile.family, 'productivity');
    expect(reason, contains('任务执行'));
  });

  test('keepPlaying route policy retains the current source across scenes',
      () async {
    BgmService.debugSeedCurrentSelection(
      track: BgmTrack.plan,
      entry: planEntry,
    );

    final reason = await BgmService.debugResolveSelectionReason(
      BgmTrack.task,
      switchBehavior: SceneBgmSwitchBehavior.keepPlaying,
    );
    final assetPath = await BgmService.debugResolveSelectionAssetPath(
      BgmTrack.task,
      switchBehavior: SceneBgmSwitchBehavior.keepPlaying,
    );

    expect(reason, contains('延续当前音乐'));
    expect(assetPath, planEntry.assetPath);
  });

  test('current playback snapshot reflects seeded route-aware selection',
      () async {
    BgmService.debugSeedCurrentSelection(
      track: BgmTrack.task,
      entry: taskEntry,
      position: const Duration(seconds: 8),
    );

    final snapshot = await BgmService.currentPlaybackSnapshot();

    expect(snapshot.track, BgmTrack.task);
    expect(snapshot.scene?.name, '任务执行');
    expect(snapshot.trackId, taskEntry.id);
    expect(snapshot.assetPath, taskEntry.assetPath);
    expect(snapshot.sourceLabel, taskEntry.album);
  });
}
