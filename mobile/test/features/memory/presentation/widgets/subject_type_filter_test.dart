import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_panel_screen.dart';

class _SubjectTypeApiService implements MemoryApiService {
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
      [
        EpisodicMemoryItem(
          id: 'rel_1',
          summary: '你提到过一段与他人的关系动态',
          sourceType: 'chat',
          sourceLane: 'inferred_extraction',
          subjectType: 'relationship',
          evidenceMissing: false,
          evidenceRefs: const [],
          evidenceScore: 0.7,
          correctionCount: 0,
          occurredAt: DateTime(2026, 4, 20),
        ),
      ];

  @override
  Future<List<PendingCommitmentItem>> getPendingCommitments() async => [];

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
  Future<MemorySettingsModel> getMemorySettings() async => MemorySettingsModel(
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
  Future<PendingCommitmentItem> resolvePendingCommitment(String id) async =>
      PendingCommitmentItem(
        id: id,
        summary: 'resolved',
        dueAt: DateTime(2026, 4, 20),
        subjectType: 'commitment',
      );

  @override
  Future<MemorySettingsModel> updateMemorySettings(
    MemorySettingsModel settings,
  ) async =>
      settings;

  @override
  Future<PushOptInSettingsModel> getPushSettings() async =>
      PushOptInSettingsModel(
        enabled: false,
        allowCommitmentFollowUp: false,
        allowEngagementRecovery: false,
        quietHoursStart: '22:00',
        quietHoursEnd: '08:00',
        timezone: 'Asia/Shanghai',
      );

  @override
  Future<PushOptInSettingsModel> updatePushSettings(
    PushOptInSettingsModel settings,
  ) async =>
      settings;
}

void main() {
  testWidgets('subject type metadata appears in episodic subtitle', (
    WidgetTester tester,
  ) async {
    AppFeatureFlags.enableMemoryPanelV2 = false;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(_SubjectTypeApiService()),
        ],
        child: const MaterialApp(home: MemoryPanelScreen()),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.textContaining('relationship'), findsOneWidget);
  });
}
