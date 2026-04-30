import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/evidence_resolve_service.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_panel_screen.dart';
import '../shared/i18n_test_helper.dart';

class _AutoMemoryApiService implements MemoryApiService {
  String? lastRetractedId;
  String? lastResolvedId;

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
          summary: '这周我要赶论文 ddl，今晚先把提纲补完',
          sourceType: 'chat',
          sourceLane: 'inferred_extraction',
          declarationLabel: 'AI 推断',
          decayPolicy: '7d',
          evidenceToken: 'turn_1',
          evidenceMissing: false,
          evidenceRefs: [
            EvidenceRefModel(type: 'chat_turn', id: 'turn_1'),
          ],
          evidenceScore: 0.9,
          correctionCount: 0,
          occurredAt: DateTime(2026, 4, 20),
        ),
      ];

  @override
  Future<List<PendingCommitmentItem>> getPendingCommitments() async => [
        PendingCommitmentItem(
          id: 'commit_1',
          summary: '明天前补完提纲',
          dueAt: DateTime(2026, 4, 20),
          subjectType: 'commitment',
        ),
      ];

  @override
  Future<List<RecentSceneSummaryItem>> getRecentScenes() async => [];

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
  Future<PendingCommitmentItem> resolvePendingCommitment(String id) async {
    lastResolvedId = id;
    return PendingCommitmentItem(
      id: id,
      summary: 'resolved',
      dueAt: DateTime(2026, 4, 20),
      subjectType: 'commitment',
      resolvedAt: DateTime(2026, 4, 20, 18),
    );
  }

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
  }) async {
    lastRetractedId = id;
  }

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

class _FakeEvidenceResolveService implements EvidenceResolveService {
  @override
  Future<List<EvidenceResolveItem>> resolveEvidence(
    List<EvidenceRefModel> refs,
  ) async =>
      [
        EvidenceResolveItem(
          type: 'chat_turn',
          id: 'turn_1',
          status: 'ok',
          payload: const {
            'chat_turn': {
              'id': 'turn_1',
              'session_id': 'session-1',
              'role': 'user',
              'content': '这周我要赶论文 ddl，今晚先把提纲补完',
            },
          },
        ),
      ];
}

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('memory panel exposes AI auto memory section and revoke action', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 2200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    AppFeatureFlags.enableMemoryPanelV2 = false;
    AppFeatureFlags.enableEvidenceViewer = true;
    AppFeatureFlags.enableMemoryExplain = false;

    final api = _AutoMemoryApiService();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(api),
          evidenceResolveServiceProvider
              .overrideWithValue(_FakeEvidenceResolveService()),
        ],
        child: testMaterialApp(home: MemoryPanelScreen()),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('AI 自动记忆'), findsOneWidget);
    expect(find.text('待跟进承诺'), findsOneWidget);
    expect(find.text('撤销此条'), findsOneWidget);
    expect(find.text('已完成'), findsOneWidget);

    await tester.tap(find.text('撤销此条'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('已完成'));
    await tester.pumpAndSettle();

    expect(api.lastRetractedId, 'auto_1');
    expect(api.lastResolvedId, 'commit_1');
    expect(find.text('这周我要赶论文 ddl，今晚先把提纲补完'), findsNothing);
  });
}
