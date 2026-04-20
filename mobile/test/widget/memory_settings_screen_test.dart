import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_settings_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class _MemorySettingsApiStub implements MemoryApiService {
  _MemorySettingsApiStub(this.settings);

  MemorySettingsModel settings;
  MemorySettingsModel? lastUpdate;

  @override
  Future<List<MemoryPreferenceItem>> getPreferences() async => [];

  @override
  Future<List<MemoryGoalItem>> getGoals({
    String? status,
    bool includeExpired = false,
    int limit = 20,
  }) async =>
      [];

  @override
  Future<List<EpisodicMemoryItem>> getEpisodic({
    DateTime? start,
    DateTime? end,
    int limit = 20,
  }) async =>
      [];

  @override
  Future<List<MemoryPreferenceHistoryItem>> getPreferenceHistory(
    String prefKey,
  ) async =>
      [];

  @override
  Future<void> retractMemory({
    required String type,
    required String id,
    String? reason,
  }) async {}

  @override
  Future<MemoryCorrectionResult> correctMemory({
    required String type,
    required String id,
    required String action,
    String? reason,
  }) async =>
      MemoryCorrectionResult(
        id: id,
        evidenceRefs: const [],
        evidenceMissing: false,
        evidenceScore: 0.5,
        correctionCount: 0,
      );

  @override
  Future<MemorySettingsModel> getMemorySettings() async => settings;

  @override
  Future<MemorySettingsModel> updateMemorySettings(
    MemorySettingsModel settings,
  ) async {
    lastUpdate = settings;
    return settings;
  }
}

void main() {
  tearDown(() {
    AppFeatureFlags.enableUserMemoryControls = false;
  });

  testWidgets('Memory settings screen renders and saves',
      (WidgetTester tester) async {
    AppFeatureFlags.enableUserMemoryControls = true;
    final stub = _MemorySettingsApiStub(
      MemorySettingsModel(
        enabled: true,
        allowPreferences: true,
        allowGoals: true,
        allowEpisodic: true,
        allowInferredEpisodic: true,
        captureLevel: 'medium',
        blockedPrefKeys: const [],
        blockedSources: const [],
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(stub),
        ],
        child: const MaterialApp(
          home: MemorySettingsScreen(),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: Locale('zh'),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('记忆控制'), findsWidgets);
    expect(find.text('AI 自动记忆'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('保存设置'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('保存设置'));
    await tester.pumpAndSettle();

    expect(stub.lastUpdate, isNotNull);
  });
}
