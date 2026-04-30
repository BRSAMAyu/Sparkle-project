import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_settings_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

class _MemorySettingsApiStub implements MemoryApiService {
  _MemorySettingsApiStub(this.settings, this.pushSettings);

  MemorySettingsModel settings;
  PushOptInSettingsModel pushSettings;
  MemorySettingsModel? lastUpdate;
  PushOptInSettingsModel? lastPushUpdate;

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
  Future<MemorySettingsModel> getMemorySettings() async => settings;

  @override
  Future<MemorySettingsModel> updateMemorySettings(
    MemorySettingsModel settings,
  ) async {
    lastUpdate = settings;
    return settings;
  }

  @override
  Future<PushOptInSettingsModel> getPushSettings() async => pushSettings;

  @override
  Future<PushOptInSettingsModel> updatePushSettings(
    PushOptInSettingsModel settings,
  ) async {
    lastPushUpdate = settings;
    return settings;
  }
}

void main() {

  setUp(setUpI18nForTesting);
  tearDown(() {
    AppFeatureFlags.enableUserMemoryControls = false;
  });

  testWidgets('Memory settings screen renders and saves',
      (WidgetTester tester) async {
    AppFeatureFlags.enableUserMemoryControls = true;
    final stub = _MemorySettingsApiStub(
      MemorySettingsModel(
        enabled: true,
        allowPreferences: true,
        allowGoals: true,
        allowEpisodic: true,
        allowInferredEpisodic: true,
        captureLevel: 'medium',
        blockedPrefKeys: const [],
        blockedSources: const [],
      ),
      PushOptInSettingsModel(
        enabled: false,
        allowCommitmentFollowUp: false,
        allowEngagementRecovery: false,
        quietHoursStart: '22:00',
        quietHoursEnd: '08:00',
        timezone: 'Asia/Shanghai',
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(stub),
        ],
        child: testMaterialApp(
          home: MemorySettingsScreen(),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: Locale('zh'),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('记忆控制'), findsWidgets);
    expect(find.text('自我记忆'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('主动提醒'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('主动提醒'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('保存设置'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('保存设置'));
    await tester.pumpAndSettle();

    expect(stub.lastUpdate, isNotNull);
    expect(stub.lastPushUpdate, isNotNull);
  });
}
