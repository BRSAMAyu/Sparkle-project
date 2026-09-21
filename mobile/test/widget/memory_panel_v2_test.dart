import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_panel_screen.dart';
import '../shared/i18n_test_helper.dart';

/// U-03：V2 主呈现 = 四组理解视图（provenance API）。旧类型/证据筛选 chips
/// 与计数主呈现已移除，测试改为断言四组分组与用户语言来源。
class _V2MemoryApiService implements MemoryApiService {
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
    int offset = 0,
  }) async =>
      [];

  @override
  Future<EpisodicMemoryPage> getEpisodicPage({
    DateTime? start,
    DateTime? end,
    int limit = 20,
    int offset = 0,
  }) async =>
      EpisodicMemoryPage(items: const [], total: 0, hasMore: false);

  @override
  Future<EpisodicMemoryItem> correctEpisodicMemory(
    String id, {
    required String action,
    String? reason,
  }) async =>
      throw UnimplementedError();

  @override
  Future<List<PendingCommitmentItem>> getPendingCommitments() async => [];

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

class _FakeProvenanceRepository implements MemoryProvenanceRepository {
  final List<ProvenanceMemoryItem> items;

  _FakeProvenanceRepository(this.items);

  @override
  Future<ProvenanceListResult> listItems({
    UnderstandingBucket? bucket,
    String? kind,
    int limit = 200,
    int offset = 0,
    bool includeInactive = false,
  }) async =>
      ProvenanceListResult(
        items: List.of(items),
        total: items.length,
        hasMore: false,
        scanCapped: false,
      );

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError(
        '${invocation.memberName} not stubbed in _FakeProvenanceRepository',
      );
}

ProvenanceMemoryItem _item({
  required String id,
  required String bucket,
  required String label,
  required String content,
}) {
  final bucketEnum = understandingBucketFromName(bucket)!;
  return ProvenanceMemoryItem(
    kind: 'episodic',
    id: id,
    ref: 'memory://episodic/$id',
    bucket: bucketEnum,
    bucketLabel: label,
    content: content,
    status: 'active',
    scope: const {'level': 'global'},
    correctionCount: 0,
    evidenceMissing: false,
    confidenceTier: 'confirmed',
    confidenceTierLabel: '已确认',
    sourceLabel: '你告诉我的',
    sourceKnown: true,
    actions: const ['update', 'revoke', 'view_source', 'pause'],
  );
}

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('V2 panel presents the four understanding groups in user language',
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
          memoryProvenanceRepositoryProvider.overrideWithValue(
            _FakeProvenanceRepository([
              _item(
                id: 'told-1',
                bucket: 'told',
                label: '你告诉我的',
                content: '我在准备离散数学期末考试',
              ),
              _item(
                id: 'unc-1',
                bucket: 'uncertain',
                label: '我还不确定的',
                content: '推测你喜欢小步拆解任务',
              ),
            ]),
          ),
        ],
        child: testMaterialApp(home: MemoryPanelScreen()),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 四组分组以用户语言呈现（空组不出现）。
    expect(find.text('你告诉我的'), findsOneWidget);
    expect(find.text('我还不确定的'), findsOneWidget);
    expect(find.text('我从你的行动中观察到的'), findsNothing);
    expect(find.text('我在准备离散数学期末考试'), findsOneWidget);

    // 黑话移除断言：旧类型/证据筛选 chips 与计数主呈现不再出现。
    expect(find.text('证据全部'), findsNothing);
    expect(find.textContaining('条判断'), findsNothing);
    expect(find.textContaining('% 高置信'), findsNothing);
  });
}
