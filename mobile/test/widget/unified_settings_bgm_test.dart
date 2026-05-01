import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/features/user/presentation/screens/unified_settings_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  const snapshotEntry = BgmCatalogEntry(
    id: 'chat_ambient_reading',
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

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{
      'bgm.enabled': true,
      'bgm.palette': 'adaptive',
      'bgm.mode': 'adaptive',
      'bgm.intensity': 'gentle',
      'bgm.variety': 'balanced',
      'bgm.reading_protection': true,
      'bgm.focus_priority': true,
      'bgm.lock_current_style': false,
    });
    await BgmService.debugResetState();
    BgmService.debugSeedCurrentSelection(
      track: BgmTrack.chat,
      entry: snapshotEntry,
    );
  });

  tearDown(() async {
    await BgmService.debugResetState();
  });

  testWidgets('settings screen exposes advanced BGM controls and persists them',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        child: testMaterialApp(
          home: UnifiedSettingsScreen(),
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    await tester.tap(find.text('背景音乐').first);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('当前播放'), findsOneWidget);
    expect(find.text('试听当前场景'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('高级控制'),
      180,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('高级控制'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('阅读保护'), findsOneWidget);
    expect(find.text('锁定当前风格'), findsOneWidget);
    expect(find.text('柔和'), findsOneWidget);
    expect(find.text('平衡'), findsOneWidget);
    expect(find.text('丰盈'), findsOneWidget);
  });
}
