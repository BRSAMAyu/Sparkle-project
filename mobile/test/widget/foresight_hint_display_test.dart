import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_panel_screen.dart';
import '../shared/i18n_test_helper.dart';

class _ForesightMemoryApiService implements MemoryApiService {
  _ForesightMemoryApiService({this.foresightHint});

  final ForesightHintSummaryItem? foresightHint;

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
  Future<List<RecentSceneSummaryItem>> getRecentScenes() async => [];

  @override
  Future<ForesightHintSummaryItem?> getForesightHintSummary() async =>
      foresightHint;

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
          summary: 'A',
          lane: 'inferred_extraction',
        ),
        rightCandidate: UnresolvedConflictCandidate(
          summary: 'B',
          lane: 'inferred_extraction',
        ),
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

Widget _buildApp(MemoryApiService service) => ProviderScope(
      overrides: [
        memoryApiServiceProvider.overrideWithValue(service),
      ],
      child: testMaterialApp(home: MemoryPanelScreen()),
    );

void main() {

  setUp(setUpI18nForTesting);
  setUp(() {
    AppFeatureFlags.enableMemoryPanelV2 = false;
  });

  testWidgets('shows foresight hint content on memory panel', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _buildApp(
        _ForesightMemoryApiService(
          foresightHint: ForesightHintSummaryItem(
            hintText: '你最近学习节奏低于常态，先把目标缩成 15 分钟再启动。',
            generatedAt: DateTime(2026, 4, 21, 9, 0),
            deviationCount: 2,
            attractorConfidences: const [],
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('前瞻提示'), findsWidgets);
    expect(find.text('你最近学习节奏低于常态，先把目标缩成 15 分钟再启动。'), findsOneWidget);
    expect(find.textContaining('检测到 2 个偏离'), findsOneWidget);
  });

  testWidgets('shows mapped attractor confidence chips', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _buildApp(
        _ForesightMemoryApiService(
          foresightHint: ForesightHintSummaryItem(
            hintText: '你最近有些偏离原计划，先把今天的主线重新钉住。',
            generatedAt: DateTime(2026, 4, 21, 9, 0),
            deviationCount: 1,
            attractorConfidences: [
              ForesightConfidenceItem(dim: 'study_pace', confidence: 0.81),
              ForesightConfidenceItem(dim: 'plan_adherence', confidence: 0.74),
            ],
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('节奏 0.81'), findsOneWidget);
    expect(find.text('计划跟随 0.74'), findsOneWidget);
  });

  testWidgets('hides foresight section when hint is absent', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _buildApp(_ForesightMemoryApiService()),
    );

    await tester.pumpAndSettle();

    expect(find.text('前瞻提示'), findsNothing);
  });
}
