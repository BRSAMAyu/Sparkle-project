import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_panel_screen.dart';
import '../../../../shared/i18n_test_helper.dart';

class _MemoryPanelApiService implements MemoryApiService {
  String? lastSelection;

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
          id: 'auto_1',
          summary: '系统记录到一条自动记忆',
          sourceType: 'chat',
          sourceLane: 'inferred_extraction',
          evidenceMissing: false,
          evidenceRefs: const [],
          evidenceScore: 0.8,
          correctionCount: 0,
          occurredAt: DateTime(2026, 4, 21),
        ),
      ];

  @override
  Future<List<PendingCommitmentItem>> getPendingCommitments() async => [];

  @override
  Future<List<RecentSceneSummaryItem>> getRecentScenes() async => [];

  @override
  Future<ForesightHintSummaryItem?> getForesightHintSummary() async => null;

  @override
  Future<List<UnresolvedConflictItem>> getUnresolvedConflicts() async => [
        UnresolvedConflictItem(
          id: 'conflict_1',
          conflictKey: 'commitment:probability',
          status: 'pending_user',
          leftCandidate: UnresolvedConflictCandidate(
            summary: '准备今晚复习概率论',
            lane: 'inferred_extraction',
            evidenceToken: 'turn-left',
          ),
          rightCandidate: UnresolvedConflictCandidate(
            summary: '今晚先刷概率论错题',
            lane: 'inferred_extraction',
            evidenceToken: 'turn-right',
          ),
        ),
      ];

  @override
  Future<UnresolvedConflictItem> arbitrateUnresolvedConflict(
    String id, {
    required String selection,
  }) async {
    lastSelection = selection;
    return UnresolvedConflictItem(
      id: id,
      conflictKey: 'commitment:probability',
      status: 'resolved',
      selectedSide: selection,
      leftCandidate: UnresolvedConflictCandidate(
          summary: 'A', lane: 'inferred_extraction'),
      rightCandidate: UnresolvedConflictCandidate(
          summary: 'B', lane: 'inferred_extraction'),
    );
  }

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
  testWidgets('memory panel shows unresolved conflicts and handles arbitration',
      (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 2200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    AppFeatureFlags.enableMemoryPanelV2 = false;
    final api = _MemoryPanelApiService();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(api),
        ],
        child: testMaterialApp(home: MemoryPanelScreen()),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('AI 自动记忆'), findsOneWidget);
    expect(find.text('待你确认'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('选 A'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(find.text('选 A'));
    expect(find.text('选 A'), findsOneWidget);

    await tester.tap(find.text('选 A'));
    await tester.pumpAndSettle();

    expect(api.lastSelection, 'left');
    expect(find.text('待你确认'), findsNothing);
  });
}
