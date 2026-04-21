import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_panel_screen.dart';

class _V2MemoryApiService implements MemoryApiService {
  @override
  Future<List<MemoryPreferenceItem>> getPreferences() async => [
        MemoryPreferenceItem(
          id: 'pref_1',
          prefKey: 'depth_preference',
          prefValue: {'value': 0.5},
          version: 1,
          evidenceMissing: false,
          evidenceRefs: const [],
          evidenceScore: 0.6,
          correctionCount: 0,
          updatedAt: DateTime(2025, 1, 2),
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
          title: 'Goal Alpha',
          status: 'active',
          evidenceMissing: false,
          evidenceRefs: const [],
          evidenceScore: 0.4,
          correctionCount: 0,
          updatedAt: DateTime(2025, 1, 3),
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
          id: 'epi_1',
          summary: 'Episodic Alpha',
          sourceType: 'analysis',
          evidenceMissing: false,
          evidenceRefs: const [],
          evidenceScore: 0.5,
          correctionCount: 0,
          occurredAt: DateTime(2025, 1, 4),
        ),
      ];

  @override
  Future<List<PendingCommitmentItem>> getPendingCommitments() async => [];

  @override
  Future<List<UnresolvedConflictItem>> getUnresolvedConflicts() async => [];

  @override
  Future<UnresolvedConflictItem> arbitrateUnresolvedConflict(
    String id, {
    required String selection,
  }) async =>
      UnresolvedConflictItem(
        id: id,
        conflictKey: 'stub',
        status: 'resolved',
        selectedSide: selection,
        leftCandidate: UnresolvedConflictCandidate(
            summary: 'A', lane: 'inferred_extraction'),
        rightCandidate: UnresolvedConflictCandidate(
            summary: 'B', lane: 'inferred_extraction'),
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
  Future<WorkingMemorySessionModel> getWorkingMemorySession({
    String? sessionId,
  }) async =>
      WorkingMemorySessionModel(sessionId: sessionId, items: const []);

  @override
  Future<void> forgetWorkingMemoryEntry(
    String entryId, {
    String? sessionId,
  }) async {}

  @override
  Future<WorkingMemoryItem> markWorkingMemoryEntryCorrect(
    String entryId, {
    String? sessionId,
  }) async =>
      WorkingMemoryItem(
        id: entryId,
        summary: 'correct',
        subjectType: 'self',
        mentionCount: 1,
        salienceScore: 0.5,
        sourceTurnIds: const [],
        evidenceToken: 'turn',
        confirmationStatus: 'correct',
        rejected: false,
        lastSeenAt: DateTime(2026, 4, 21),
      );

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
  testWidgets('Memory panel V2 shows filters and applies type filter',
      (WidgetTester tester) async {
    await tester.binding.setSurfaceSize(const Size(1440, 2200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    AppFeatureFlags.enableMemoryPanelV2 = true;
    AppFeatureFlags.enableEvidenceViewer = false;
    AppFeatureFlags.enableMemoryExplain = false;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(_V2MemoryApiService()),
        ],
        child: const MaterialApp(home: MemoryPanelScreen()),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('证据全部'), findsOneWidget);
    expect(find.text('Episodic Alpha'), findsOneWidget);

    await tester.tap(find.text('经历'));
    await tester.pumpAndSettle();

    expect(find.text('Episodic Alpha'), findsOneWidget);
    expect(find.text('depth_preference'), findsNothing);
  });
}
