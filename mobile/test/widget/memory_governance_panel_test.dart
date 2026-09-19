// memory-governance-mvp: 记忆面板情景记忆的用户治理动作（确认/纠正/删除）与来源标注。
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_panel_screen.dart';
import '../shared/i18n_test_helper.dart';

class _GovernanceMemoryApiService implements MemoryApiService {
  _GovernanceMemoryApiService(this.memories);

  List<EpisodicMemoryItem> memories;
  final List<(String id, String action)> correctionCalls = [];

  @override
  Future<List<MemoryPreferenceItem>> getPreferences() async => [];

  @override
  Future<List<MemoryPreferenceHistoryItem>> getPreferenceHistory(
    String prefKey,
  ) async =>
      [];

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
      memories;

  @override
  Future<EpisodicMemoryPage> getEpisodicPage({
    DateTime? start,
    DateTime? end,
    int limit = 20,
    int offset = 0,
  }) async {
    final items = await getEpisodic(start: start, end: end, limit: limit);
    return EpisodicMemoryPage(
      items: offset == 0 ? items : const [],
      total: items.length,
      hasMore: false,
    );
  }

  @override
  Future<EpisodicMemoryItem> correctEpisodicMemory(
    String id, {
    required String action,
    String? reason,
  }) async {
    correctionCalls.add((id, action));
    if (action == 'confirm') {
      final target =
          memories.firstWhere((entry) => entry.id == id);
      final updated = EpisodicMemoryItem(
        id: target.id,
        summary: target.summary,
        sourceType: target.sourceType,
        evidenceMissing: target.evidenceMissing,
        evidenceRefs: target.evidenceRefs,
        evidenceScore: target.evidenceScore + 0.05,
        correctionCount: target.correctionCount,
        sourceLane: target.sourceLane,
        occurredAt: target.occurredAt,
        confidence: (target.confidence ?? 0) + 0.05,
        tags: target.tags,
        sourceTurnId: target.sourceTurnId,
        sourceLabel: target.sourceLabel,
      );
      memories = [
        for (final entry in memories) if (entry.id == id) updated else entry,
      ];
      return updated;
    }
    memories = [
      for (final entry in memories)
        if (entry.id != id) entry,
    ];
    return EpisodicMemoryItem(
      id: id,
      summary: 'removed',
      sourceType: 'chat',
      evidenceMissing: false,
      evidenceRefs: const [],
      evidenceScore: 0,
      correctionCount: 1,
      revokedAt: DateTime(2026, 9, 19),
    );
  }

  @override
  Future<List<PendingCommitmentItem>> getPendingCommitments() async => [];

  @override
  Future<PendingCommitmentItem> resolvePendingCommitment(String id) async =>
      throw UnimplementedError();

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
      throw UnimplementedError();

  @override
  Future<WorkingMemorySessionModel> getWorkingMemorySession({
    String? sessionId,
  }) async =>
      WorkingMemorySessionModel(sessionId: null, items: const []);

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
      throw UnimplementedError();

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
      throw UnimplementedError();

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

EpisodicMemoryItem _chatMemory({
  required String id,
  required String summary,
  String sourceLane = 'direct_capture',
}) =>
    EpisodicMemoryItem(
      id: id,
      summary: summary,
      sourceType: 'chat',
      sourceLane: sourceLane,
      confidence: 0.6,
      tags: const ['微积分'],
      sourceTurnId: 'turn_abcd1234',
      sourceLabel: '对话记录',
      writtenAt: DateTime(2026, 9, 18),
      evidenceMissing: false,
      evidenceRefs: [
        EvidenceRefModel(type: 'chat_turn', id: 'turn_abcd1234'),
      ],
      evidenceScore: 0.8,
      correctionCount: 0,
      occurredAt: DateTime(2026, 9, 18),
    );

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('episodic card shows source annotation, tags and governance actions', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 2200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    AppFeatureFlags.enableMemoryPanelV2 = false;
    AppFeatureFlags.enableEvidenceViewer = false;
    AppFeatureFlags.enableMemoryExplain = false;

    final api = _GovernanceMemoryApiService([
      _chatMemory(id: 'ep_1', summary: '用户正在准备微积分考试'),
    ]);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [memoryApiServiceProvider.overrideWithValue(api)],
        child: testMaterialApp(theme: AppThemes.lightTheme, home: const MemoryPanelScreen()),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 2));

    // 来源标注：模块 + 对话轮次 + 写入时间
    expect(find.textContaining('来源：对话记录'), findsOneWidget);
    expect(find.textContaining('对话 turn_ab'), findsOneWidget);
    expect(find.textContaining('写入于 2026-09-18'), findsOneWidget);
    // 标签
    expect(find.text('微积分'), findsOneWidget);
    // 每条操作
    expect(find.text('确认无误'), findsOneWidget);
    expect(find.text('纠正'), findsOneWidget);
    expect(find.text('删除'), findsOneWidget);
  });

  testWidgets('delete correction removes the episodic card and calls the API', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 2200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    AppFeatureFlags.enableMemoryPanelV2 = false;
    AppFeatureFlags.enableEvidenceViewer = false;
    AppFeatureFlags.enableMemoryExplain = false;

    final api = _GovernanceMemoryApiService([
      _chatMemory(id: 'ep_del', summary: '要被删除的记忆'),
    ]);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [memoryApiServiceProvider.overrideWithValue(api)],
        child: testMaterialApp(theme: AppThemes.lightTheme, home: const MemoryPanelScreen()),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 2));
    expect(find.text('要被删除的记忆'), findsOneWidget);

    await tester.tap(find.text('删除'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(api.correctionCalls, contains(('ep_del', 'delete')));
    expect(find.text('要被删除的记忆'), findsNothing);
  });

  testWidgets('confirm correction keeps the card and calls the API', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 2200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    AppFeatureFlags.enableMemoryPanelV2 = false;
    AppFeatureFlags.enableEvidenceViewer = false;
    AppFeatureFlags.enableMemoryExplain = false;

    final api = _GovernanceMemoryApiService([
      _chatMemory(id: 'ep_ok', summary: '被确认的记忆'),
    ]);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [memoryApiServiceProvider.overrideWithValue(api)],
        child: testMaterialApp(theme: AppThemes.lightTheme, home: const MemoryPanelScreen()),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 2));

    await tester.tap(find.text('确认无误'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(api.correctionCalls, contains(('ep_ok', 'confirm')));
    expect(find.text('被确认的记忆'), findsOneWidget);
  });

  testWidgets('correction sheet offers wrong/outdated and submits reason', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 2200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    AppFeatureFlags.enableMemoryPanelV2 = false;
    AppFeatureFlags.enableEvidenceViewer = false;
    AppFeatureFlags.enableMemoryExplain = false;

    final api = _GovernanceMemoryApiService([
      _chatMemory(id: 'ep_fix', summary: '要纠正的记忆'),
    ]);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [memoryApiServiceProvider.overrideWithValue(api)],
        child: testMaterialApp(theme: AppThemes.lightTheme, home: const MemoryPanelScreen()),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(seconds: 2));

    await tester.tap(find.text('纠正'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('这条记忆哪里不对？'), findsOneWidget);
    expect(find.text('记错了'), findsOneWidget);
    expect(find.text('不再是这样了'), findsOneWidget);

    await tester.enterText(
      find.widgetWithText(TextField, '补充说明（可选）').first,
      '其实我没说过',
    );
    await tester.tap(find.text('记错了'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(api.correctionCalls, hasLength(1));
    expect(api.correctionCalls.first.$1, 'ep_fix');
    expect(api.correctionCalls.first.$2, 'wrong');
    expect(find.text('要纠正的记忆'), findsNothing);
  });
}
