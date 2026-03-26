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
      'bgm.palette': 'warm',
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

  test('recent de-dup favors alternate entry when variety is dynamic', () {
    final picked = BgmService.debugPickCatalogEntry(
      entries: const [chatEntry, chatAltEntry],
      track: BgmTrack.chat,
      palette: BgmPalette.adaptive,
      tuning: const BgmUserTuning(variety: BgmVariety.dynamic),
      recentIds: const ['chat_soft'],
    );

    expect(picked?.id, 'chat_alt');
  });

  test('same-family transitions within 20 seconds retain current selection',
      () async {
    final now = DateTime(2026, 3, 26, 9, 0);
    BgmService.debugSetNowProvider(() => now);
    BgmService.debugSeedCurrentSelection(
      track: BgmTrack.plan,
      entry: dashboardEntry,
      startedAt: now.subtract(const Duration(seconds: 10)),
    );

    final reason = await BgmService.debugResolveSelectionReason(
      BgmTrack.calendar,
    );

    expect(reason, contains('同一氛围家族在 20 秒内延续当前音乐'));
  });

  test('falls back to bundled mapping when catalog is empty', () async {
    BgmService.debugSetCatalogEntries(const []);

    final reason = await BgmService.debugResolveSelectionReason(
      BgmTrack.dashboard,
      force: true,
    );

    expect(reason, contains('内置兜底'));
  });

  test('missing insights asset falls back to bundled mapping reason', () async {
    BgmService.debugSetCatalogEntries(const []);
    BgmService.debugMarkAssetMissing('audio/bgm/insights_harp.m4a');

    final reason = await BgmService.debugResolveSelectionReason(
      BgmTrack.insights,
      force: true,
    );

    expect(reason, contains('内置兜底'));
  });

  test('thinking mix ducks harder than reading mix', () async {
    await BgmService.setReadingActivity(true);
    await BgmService.setThinkingActivity(true);

    final factor = await BgmService.debugEffectiveDuckFactor();

    expect(factor, closeTo(0.54, 0.001));
  });
}
