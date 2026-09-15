import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/bgm_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const chatEntry = BgmCatalogEntry(
    id: 'chat_soft',
    assetPath: 'audio/bgm/chat_ambient.m4a',
    album: 'Test Album',
    sceneTags: ['chat', 'reading', 'soft'],
    paletteTags: ['adaptive'],
    energy: 0.20,
    density: 0.16,
    baseGain: 0.92,
    loopable: true,
    releaseApproved: true,
  );

  const chatAltEntry = BgmCatalogEntry(
    id: 'chat_alt',
    assetPath: 'audio/bgm/thinking.m4a',
    album: 'Test Album',
    sceneTags: ['chat', 'reading', 'soft'],
    paletteTags: ['adaptive'],
    energy: 0.20,
    density: 0.16,
    baseGain: 0.90,
    loopable: true,
    releaseApproved: true,
  );

  const chatThirdEntry = BgmCatalogEntry(
    id: 'chat_third',
    assetPath: 'audio/bgm/profile_reflect.m4a',
    album: 'Test Album',
    sceneTags: ['chat', 'reading', 'soft'],
    paletteTags: ['adaptive'],
    energy: 0.21,
    density: 0.18,
    baseGain: 0.91,
    loopable: true,
    releaseApproved: true,
  );

  const dashboardEntry = BgmCatalogEntry(
    id: 'dashboard_home',
    assetPath: 'audio/bgm/home_morning.m4a',
    album: 'Test Album',
    sceneTags: ['dashboard', 'home', 'warm'],
    paletteTags: ['adaptive', 'warm'],
    energy: 0.30,
    density: 0.26,
    baseGain: 0.96,
    loopable: true,
    releaseApproved: true,
  );

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'bgm.palette': 'adaptive',
      'bgm.intensity': 'gentle',
      'bgm.variety': 'balanced',
    });
    await BgmService.debugResetState();
  });

  tearDown(() async {
    await BgmService.debugResetState();
  });

  test('scene matching prefers chat-tagged entry for chat track', () {
    final picked = BgmService.debugPickCatalogEntry(
      entries: const [dashboardEntry, chatEntry],
      track: BgmTrack.chat,
      palette: BgmPalette.adaptive,
      tuning: const BgmUserTuning(),
    );

    expect(picked?.id, 'chat_soft');
  });

  test('unfinished scene resumes the same curated track from its saved state',
      () async {
    BgmService.debugSetCatalogEntries(const [chatEntry, chatAltEntry]);
    BgmService.debugSeedSceneState(
      track: BgmTrack.chat,
      entry: chatEntry,
      position: const Duration(seconds: 42),
    );

    final reason = await BgmService.debugResolveSelectionReason(BgmTrack.chat);
    final assetPath = await BgmService.debugResolveSelectionAssetPath(
      BgmTrack.chat,
    );

    expect(reason, contains('恢复 聊天 上次播放断点'));
    expect(assetPath, chatEntry.assetPath);
  });

  test('completed scene advances to the next curated track on re-entry',
      () async {
    const entries = [chatEntry, chatAltEntry];
    BgmService.debugSetCatalogEntries(entries);
    BgmService.debugSeedSceneState(
      track: BgmTrack.chat,
      entry: chatEntry,
      completed: true,
      queueCursor: 1,
    );
    final queue = BgmService.debugCatalogQueueIds(
      entries: entries,
      track: BgmTrack.chat,
      palette: BgmPalette.adaptive,
      tuning: const BgmUserTuning(),
    );

    final assetPath = await BgmService.debugResolveSelectionAssetPath(
      BgmTrack.chat,
    );

    final expectedEntry = entries.firstWhere((entry) => entry.id == queue[1]);
    expect(assetPath, expectedEntry.assetPath);
  });

  test('scene playback states stay isolated per track', () {
    BgmService.debugSeedSceneState(
      track: BgmTrack.chat,
      entry: chatEntry,
      position: const Duration(seconds: 12),
      queueCursor: 1,
    );
    BgmService.debugSeedSceneState(
      track: BgmTrack.dashboard,
      entry: dashboardEntry,
      position: const Duration(seconds: 4),
      queueCursor: 0,
    );

    final chatState = BgmService.debugSceneStateForTrack(BgmTrack.chat);
    final dashboardState = BgmService.debugSceneStateForTrack(
      BgmTrack.dashboard,
    );

    expect(chatState['trackId'], chatEntry.id);
    expect(chatState['positionMs'], const Duration(seconds: 12).inMilliseconds);
    expect(dashboardState['trackId'], dashboardEntry.id);
    expect(
      dashboardState['positionMs'],
      const Duration(seconds: 4).inMilliseconds,
    );
  });

  test('switch-on-enter no longer retains same-family selection by default',
      () async {
    BgmService.debugSeedCurrentSelection(
        track: BgmTrack.plan, entry: dashboardEntry);

    final reason = await BgmService.debugResolveSelectionReason(
      BgmTrack.calendar,
    );

    expect(reason, isNot(contains('延续当前音乐')));
  });

  test('falls back to bundled mapping when catalog is empty', () async {
    BgmService.debugSetCatalogEntries(const []);

    final reason = await BgmService.debugResolveSelectionReason(
      BgmTrack.dashboard,
      force: true,
      palette: BgmPalette.piano,
    );

    expect(reason, contains('内置兜底'));
  });

  test('piano palette avoids short loop fallback for chat scenes', () async {
    BgmService.debugSetCatalogEntries(const []);

    final assetPath = await BgmService.debugResolveSelectionAssetPath(
      BgmTrack.chat,
      force: true,
      palette: BgmPalette.piano,
    );

    expect(assetPath, 'audio/bgm/thinking.m4a');
  });

  test('missing insights asset falls back to bundled mapping reason', () async {
    BgmService.debugSetCatalogEntries(const []);
    BgmService.debugMarkAssetMissing('audio/bgm/insights_harp.m4a');

    final reason = await BgmService.debugResolveSelectionReason(
      BgmTrack.insights,
      force: true,
      palette: BgmPalette.piano,
    );

    expect(reason, contains('内置兜底'));
  });

  test('thinking mix ducks harder than reading mix', () async {
    await BgmService.setReadingActivity(true);
    await BgmService.setThinkingActivity(true);

    final factor = await BgmService.debugEffectiveDuckFactor();

    expect(factor, closeTo(0.54, 0.001));
  });

  test('Aurora status strategies cover the six-state BGM mapping', () {
    final strategies = <String, AuroraBgmStrategy>{
      for (final status in const [
        'sensing',
        'calibrated',
        'risk_found',
        'needs_confirm',
        'calibration_available',
        'cooling_down',
      ])
        status: BgmService.auroraStrategyForStatus(
          status,
          sceneTrack: BgmTrack.galaxy,
        ),
    };

    expect(strategies['sensing']!.trackOverride, isNull);
    expect(strategies['calibrated']!.trackOverride, BgmTrack.galaxy);
    expect(strategies['risk_found']!.trackOverride, BgmTrack.thinking);
    expect(strategies['needs_confirm']!.trackOverride, isNull);
    expect(strategies['needs_confirm']!.duckFactor, lessThan(0.25));
    expect(
      strategies['calibration_available']!.trackOverride,
      BgmTrack.visualUnlock,
    );
    expect(strategies['calibration_available']!.highlightPulse, isTrue);
    expect(strategies['cooling_down']!.trackOverride, BgmTrack.focusDeep);
  });

  test('curated catalog is preferred over bundled fallback by default',
      () async {
    BgmService.debugSetCatalogEntries([
      const BgmCatalogEntry(
        id: 'chat_catalog_pick',
        assetPath: 'audio/bgm/catalog_chat_pick.m4a',
        album: 'Curated',
        sceneTags: ['chat'],
        paletteTags: ['piano'],
        energy: 0.2,
        density: 0.2,
        baseGain: 1,
        loopable: true,
        releaseApproved: true,
      ),
    ]);

    final assetPath = await BgmService.debugResolveSelectionAssetPath(
      BgmTrack.chat,
      force: true,
    );

    expect(assetPath, 'audio/bgm/catalog_chat_pick.m4a');
  });

  test('dynamic variety advances queue with a non-repeating jump', () {
    BgmService.debugSeedSceneState(
      track: BgmTrack.chat,
      entry: chatEntry,
      queueCursor: 0,
    );

    BgmService.debugAdvanceSceneQueue(
      BgmTrack.chat,
      playlistLength: 3,
      variety: BgmVariety.dynamic,
    );

    final state = BgmService.debugSceneStateForTrack(BgmTrack.chat);

    expect(state['queueCursor'], 2);
  });

  test('dynamic queue uses the advanced cursor when resolving catalog entry',
      () async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'bgm.palette': 'warm',
      'bgm.variety': 'dynamic',
    });
    await BgmService.debugResetState();
    const entries = [chatEntry, chatAltEntry, chatThirdEntry];
    BgmService.debugSetCatalogEntries(entries);
    BgmService.debugSeedSceneState(
      track: BgmTrack.chat,
      entry: chatEntry,
      queueCursor: 2,
      completed: true,
      variety: BgmVariety.dynamic,
    );
    final queue = BgmService.debugCatalogQueueIds(
      entries: entries,
      track: BgmTrack.chat,
      palette: BgmPalette.adaptive,
      tuning: const BgmUserTuning(variety: BgmVariety.dynamic),
    );

    final assetPath = await BgmService.debugResolveSelectionAssetPath(
      BgmTrack.chat,
    );

    final expectedEntry = entries.firstWhere((entry) => entry.id == queue[2]);
    expect(assetPath, expectedEntry.assetPath);
  });

  test('BgmUserTuning copyWith preserves unchanged fields', () {
    const original = BgmUserTuning(
      intensity: BgmIntensity.lush,
      variety: BgmVariety.dynamic,
      readingProtection: false,
    );
    final copy = original.copyWith(focusPriority: true);
    expect(copy.intensity, BgmIntensity.lush);
    expect(copy.variety, BgmVariety.dynamic);
    expect(copy.readingProtection, isFalse);
    expect(copy.focusPriority, isTrue);
    expect(copy.lockCurrentStyle, isFalse);
  });

  test('BgmCatalogEntry.fromJson parses numeric fields robustly', () {
    final entry = BgmCatalogEntry.fromJson({
      'id': 'test-entry',
      'assetPath': 'audio/bgm/test.m4a',
      'album': 'Test',
      'sceneTags': ['dashboard'],
      'paletteTags': ['adaptive'],
      'energy': '0.5', // String instead of number
      'density': 0.3,
      'baseGain': null, // Missing
      'loopable': true,
      'releaseApproved': false,
    });
    expect(entry.id, 'test-entry');
    expect(entry.energy, 0.5);
    expect(entry.density, 0.3);
    expect(entry.baseGain, 1.0); // Fallback
  });

  test('BgmLibraryEntry sourceLabel varies by source kind', () {
    const curated = BgmLibraryEntry(
      id: '1', title: 'T', album: 'My Album', path: '/a',
      sourceKind: BgmLibrarySourceKind.curated, isAsset: true,
      sceneTags: [], paletteTags: [], energy: 0.5, density: 0.5, baseGain: 1.0,
    );
    const imported = BgmLibraryEntry(
      id: '2', title: 'T', album: 'A', path: '/b',
      sourceKind: BgmLibrarySourceKind.imported, isAsset: false,
      sceneTags: [], paletteTags: [], energy: 0.5, density: 0.5, baseGain: 1.0,
    );
    const bundled = BgmLibraryEntry(
      id: '3', title: 'T', album: 'A', path: '/c',
      sourceKind: BgmLibrarySourceKind.bundled, isAsset: true,
      sceneTags: [], paletteTags: [], energy: 0.5, density: 0.5, baseGain: 1.0,
    );
    expect(curated.sourceLabel, 'My Album');
    expect(imported.sourceLabel, contains('导入'));
    expect(bundled.sourceLabel, contains('内置'));
  });

  test('BgmTrack mixVolume values are within valid range', () {
    for (final track in BgmTrack.values) {
      expect(track.mixVolume, inInclusiveRange(0.0, 1.0));
    }
  });

  test('BgmLibrarySnapshot totalCount matches entries length', () {
    const snapshot = BgmLibrarySnapshot(
      entries: [
        BgmLibraryEntry(
          id: '1', title: 'A', album: 'B', path: '/',
          sourceKind: BgmLibrarySourceKind.bundled, isAsset: true,
          sceneTags: [], paletteTags: [], energy: 0.5, density: 0.5, baseGain: 1.0,
        ),
        BgmLibraryEntry(
          id: '2', title: 'C', album: 'D', path: '/',
          sourceKind: BgmLibrarySourceKind.curated, isAsset: true,
          sceneTags: [], paletteTags: [], energy: 0.5, density: 0.5, baseGain: 1.0,
        ),
      ],
      curatedCount: 1,
      importedCount: 0,
      bundledCount: 1,
      importDirectoryPath: '/import',
      downloadDirectoryPath: '/download',
    );
    expect(snapshot.totalCount, 2);
  });
}
