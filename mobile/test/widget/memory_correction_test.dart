import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_detail_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class _CorrectionApiService implements MemoryApiService {
  _CorrectionApiService(this.result);

  final MemoryCorrectionResult result;
  String? lastAction;

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
  }) async {
    lastAction = action;
    return result;
  }

  @override
  Future<MemorySettingsModel> getMemorySettings() async =>
      MemorySettingsModel(
        enabled: true,
        allowPreferences: true,
        allowGoals: true,
        allowEpisodic: true,
        allowInferredEpisodic: true,
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
  setUp(() {
    AppFeatureFlags.enableMemoryCorrection = false;
  });

  tearDown(() {
    AppFeatureFlags.enableMemoryCorrection = false;
  });

  testWidgets('Correction buttons hidden when flag off',
      (WidgetTester tester) async {
    AppFeatureFlags.enableMemoryCorrection = false;
    final preference = MemoryPreferenceItem(
      id: 'pref_1',
      prefKey: 'depth_preference',
      prefValue: {'value': 0.4},
      version: 1,
      evidenceMissing: false,
      evidenceRefs: const [],
      evidenceScore: 0.5,
      correctionCount: 0,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(
            _CorrectionApiService(
              MemoryCorrectionResult(
                id: 'pref_1',
                evidenceRefs: const [],
                evidenceMissing: false,
                evidenceScore: 0.5,
                correctionCount: 1,
              ),
            ),
          ),
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
    expect(find.text('纠错操作'), findsNothing);
  });

  testWidgets('Correction action triggers API and updates UI',
      (WidgetTester tester) async {
    AppFeatureFlags.enableMemoryCorrection = true;
    final preference = MemoryPreferenceItem(
      id: 'pref_1',
      prefKey: 'depth_preference',
      prefValue: {'value': 0.4},
      version: 1,
      evidenceMissing: false,
      evidenceRefs: const [],
      evidenceScore: 0.5,
      correctionCount: 0,
      confidence: 0.6,
    );
    final service = _CorrectionApiService(
      MemoryCorrectionResult(
        id: 'pref_1',
        evidenceRefs: const [],
        evidenceMissing: false,
        evidenceScore: 0.6,
        correctionCount: 2,
        confidence: 0.5,
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(service),
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
    await tester.tap(find.text('Not true'));
    await tester.pumpAndSettle();

    expect(service.lastAction, 'reject');
    expect(find.textContaining('已提交纠错'), findsOneWidget);
  });
}
