import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/evidence_resolve_service.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_panel_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class _FakeMemoryApiService implements MemoryApiService {
  @override
  Future<List<MemoryPreferenceItem>> getPreferences() async => [
        MemoryPreferenceItem(
          id: 'pref_1',
          prefKey: 'depth_preference',
          prefValue: {'value': 0.8},
          version: 2,
          evidenceMissing: true,
          evidenceRefs: [
            EvidenceRefModel(type: 'event', id: 'evt_1'),
          ],
          evidenceScore: 0.4,
          correctionCount: 1,
        ),
      ];

  @override
  Future<List<MemoryGoalItem>> getGoals({
    String? status,
    bool includeExpired = false,
    int limit = 20,
  }) async =>
      [
        MemoryGoalItem(
          id: 'goal_1',
          title: 'Goal',
          status: 'active',
          evidenceMissing: false,
          evidenceRefs: [],
          evidenceScore: 0.3,
          correctionCount: 0,
        ),
      ];

  @override
  Future<List<EpisodicMemoryItem>> getEpisodic({
    DateTime? start,
    DateTime? end,
    int limit = 20,
  }) async =>
      [
        EpisodicMemoryItem(
          id: 'mem_1',
          summary: 'Memory',
          sourceType: 'analysis',
          evidenceMissing: false,
          evidenceRefs: [],
          evidenceScore: 0.5,
          correctionCount: 0,
        ),
      ];

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
        evidenceScore: 0.6,
        correctionCount: 2,
      );

  @override
  Future<MemorySettingsModel> getMemorySettings() async => MemorySettingsModel(
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

class _FakeEvidenceResolveService implements EvidenceResolveService {
  @override
  Future<List<EvidenceResolveItem>> resolveEvidence(
    List<EvidenceRefModel> refs,
  ) async =>
      [
        EvidenceResolveItem(
          type: 'event',
          id: 'evt_1',
          status: 'ok',
          payload: const {
            'event': {'event_type': 'test'},
          },
        ),
      ];
}

void main() {
  testWidgets('Memory panel renders sections and opens detail',
      (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1440, 2200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    AppFeatureFlags.enableMemoryPanelV2 = false;
    AppFeatureFlags.enableEvidenceViewer = false;
    AppFeatureFlags.enableMemoryExplain = false;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(_FakeMemoryApiService()),
          evidenceResolveServiceProvider
              .overrideWithValue(_FakeEvidenceResolveService()),
        ],
        child: MaterialApp(
          home: const MemoryPanelScreen(),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: const Locale('zh'),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('偏好'), findsOneWidget);
    expect(find.text('目标'), findsOneWidget);
    expect(find.text('经历'), findsOneWidget);

    await tester.tap(find.text('depth_preference'));
    await tester.pumpAndSettle();

    expect(find.text('版本历史'), findsOneWidget);
    expect(find.text('缺失'), findsOneWidget);
  });
}
