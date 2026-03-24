import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class _HistoryStubService implements MemoryApiService {
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
        correctionCount: 1,
      );

  @override
  Future<MemorySettingsModel> getMemorySettings() async =>
      MemorySettingsModel(
        enabled: true,
        allowPreferences: true,
        allowGoals: true,
        allowEpisodic: true,
        captureLevel: 'medium',
        blockedPrefKeys: const [],
        blockedSources: const [],
      );

  @override
  Future<MemorySettingsModel> updateMemorySettings(
    MemorySettingsModel settings,
  ) async =>
      settings;
}

void main() {
  tearDown(() {
    AppFeatureFlags.enableMemoryExplain = false;
    AppFeatureFlags.enableMemoryPanelV2 = false;
    AppFeatureFlags.enableUserMemoryControls = false;
  });

  testWidgets('Explanation view renders when flag on',
      (WidgetTester tester) async {
    AppFeatureFlags.enableMemoryExplain = true;
    AppFeatureFlags.enableMemoryPanelV2 = true;
    AppFeatureFlags.enableUserMemoryControls = false;

    final preference = MemoryPreferenceItem(
      id: 'pref_1',
      prefKey: 'depth_preference',
      prefValue: {'value': 0.6},
      version: 1,
      evidenceMissing: false,
      evidenceRefs: const [],
      evidenceScore: 0.6,
      correctionCount: 0,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(_HistoryStubService()),
        ],
        child: MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
          home: MemoryDetailScreen(
            args: MemoryDetailArgs.preference(preference),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('Why this memory?'), findsOneWidget);
  });

  testWidgets('Explanation view shows settings summary when enabled',
      (WidgetTester tester) async {
    AppFeatureFlags.enableMemoryExplain = true;
    AppFeatureFlags.enableMemoryPanelV2 = true;
    AppFeatureFlags.enableUserMemoryControls = true;

    final preference = MemoryPreferenceItem(
      id: 'pref_2',
      prefKey: 'depth_preference',
      prefValue: {'value': 0.7},
      version: 1,
      evidenceMissing: false,
      evidenceRefs: const [],
      evidenceScore: 0.6,
      correctionCount: 0,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(_HistoryStubService()),
        ],
        child: MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
          home: MemoryDetailScreen(
            args: MemoryDetailArgs.preference(preference),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.textContaining('已允许捕获'), findsOneWidget);
    expect(find.textContaining('捕获级别'), findsOneWidget);
  });
}
