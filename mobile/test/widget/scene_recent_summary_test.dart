import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_panel_screen.dart';
import '../shared/i18n_test_helper.dart';

class _SceneSummaryApiService implements MemoryApiService {
  _SceneSummaryApiService({required this.recentScenes});

  final List<RecentSceneSummaryItem> recentScenes;

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
  Future<List<PendingCommitmentItem>> getPendingCommitments() async => [];

  @override
  Future<List<RecentSceneSummaryItem>> getRecentScenes() async => recentScenes;

  @override
  Future<ForesightHintSummaryItem?> getForesightHintSummary() async => null;

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

  setUp(setUpI18nForTesting);
  Future<void> pumpPanel(
    WidgetTester tester, {
    required bool v2,
    required List<RecentSceneSummaryItem> scenes,
  }) async {
    AppFeatureFlags.enableMemoryPanelV2 = v2;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(
            _SceneSummaryApiService(recentScenes: scenes),
          ),
        ],
        child: const MaterialApp(home: MemoryPanelScreen()),
      ),
    );
    await tester.pumpAndSettle();
  }

  final scenes = [
    RecentSceneSummaryItem(
      sceneId: 'scene_1',
      title: '周末早晨学习场景 · 数学',
      timeStart: DateTime(2026, 4, 19, 9),
      timeEnd: DateTime(2026, 4, 19, 11),
      memberCount: 3,
      qualityScore: 0.82,
    ),
  ];

  testWidgets('scene recent summary renders in V2 panel',
      (WidgetTester tester) async {
    await pumpPanel(tester, v2: true, scenes: scenes);

    expect(find.text('最近场景'), findsOneWidget);
    expect(find.text('周末早晨学习场景 · 数学'), findsOneWidget);
    expect(find.text('Q 0.82'), findsOneWidget);
  });

  testWidgets('scene recent summary renders in V1 panel',
      (WidgetTester tester) async {
    await pumpPanel(tester, v2: false, scenes: scenes);

    expect(find.text('最近场景'), findsWidgets);
    expect(find.textContaining('3 条记忆'), findsOneWidget);
  });

  testWidgets('scene recent summary stays hidden when empty',
      (WidgetTester tester) async {
    await pumpPanel(tester, v2: true, scenes: const []);

    expect(find.text('最近场景'), findsNothing);
  });
}
