import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';
import 'package:sparkle/features/aurora/data/services/aurora_core_session_service.dart';
import 'package:sparkle/features/aurora/presentation/widgets/aurora_core_session_sheet.dart';
import 'package:sparkle/features/chat/presentation/widgets/aurora_nudge_entry.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';
import 'package:sparkle/features/task/presentation/widgets/stuck_help_sheet.dart';
import 'package:sparkle/shared/entities/task_model.dart';

import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    setUpI18nForTesting();
  });
  tearDown(tearDownI18n);

  testWidgets('status entry starts one unified Core Session sheet',
      (tester) async {
    final fake = _FakeCoreSessionClient(
      startResult: _session(
        messages: [
          const AuroraCoreMessage(
            role: 'aurora',
            content: '我注意到你最近任务超时。现在聊这个是因为需要校准。'
                '这大概需要 4 分钟，你也可以随时暂停或跳过。',
            stage: 'declare',
            timestamp: '2026-05-01T00:00:00',
          ),
        ],
      ),
    );
    final entryReason = AuroraCoreSessionEntryReason(
      triggerSource: 'status_bar',
      observedSignals: const ['任务超时'],
      suggestedAgendaPreview: const ['确认状态带里的判断'],
      whyNow: '需要校准',
      estimatedMinutes: 4,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [auroraCoreSessionServiceProvider.overrideWithValue(fake)],
        child: testMaterialApp(
          home: Builder(
            builder: (context) => Scaffold(
              body: TextButton(
                onPressed: () => showAuroraCoreSession(
                  context: context,
                  bandStatus: 'risk_found',
                  wakeReasons: const ['task_time_overrun'],
                  entryReason: entryReason,
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('open'));
    await tester.pumpAndSettle();

    expect(fake.lastEntryReason?.triggerSource, 'status_bar');
    expect(find.text('Aurora 深度校准'), findsOneWidget);
    expect(find.textContaining('这大概需要 4 分钟'), findsOneWidget);
  });

  testWidgets('freeform correction sends typed text through the session client',
      (tester) async {
    final fake = _FakeCoreSessionClient(
      startResult: _session(
        optionGroups: [
          _simpleGroup(),
        ],
      ),
      respondResult: _session(
        messages: [
          const AuroraCoreMessage(
            role: 'user',
            content: '不是任务太大，是我还不会。',
            stage: 'await_user',
            timestamp: '2026-05-01T00:01:00',
            isFreeform: true,
          ),
        ],
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [auroraCoreSessionServiceProvider.overrideWithValue(fake)],
        child: testMaterialApp(
          home: const Scaffold(
            body: AuroraCoreSessionSheet(
              bandStatus: 'needs_confirm',
              wakeReasons: ['standard_layer_uncertainty'],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('都不对，我解释一下'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), '不是任务太大，是我还不会。');
    await tester.tap(find.text('发送'));
    await tester.pumpAndSettle();

    expect(fake.lastContent, '不是任务太大，是我还不会。');
    expect(fake.lastIsFreeform, isTrue);
  });

  testWidgets(
      'completed session shows summary, state patches, and next changes',
      (tester) async {
    final fake = _FakeCoreSessionClient(
      startResult: _session(
        status: 'completed',
        calibrationResult: const AuroraCalibrationResult(
          updatesApplied: [],
          summary: '这次我们确认了任务颗粒度。',
          userVisibleSummary: '这次我们确认了任务颗粒度。',
          scopeCompleted: '任务颗粒度',
          strategyChanges: ['后续任务颗粒度调小'],
          statePatches: [
            {
              'state_key': 'task_granularity_fit',
              'new_value': 'smaller',
            },
          ],
          nextChanges: ['接下来的计划会更轻一点'],
          sessionId: 'session-1',
          completedAt: '2026-05-01T00:02:00',
        ),
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [auroraCoreSessionServiceProvider.overrideWithValue(fake)],
        child: testMaterialApp(
          home: const Scaffold(
            body: AuroraCoreSessionSheet(
              bandStatus: 'calibration_available',
              wakeReasons: ['plan_drift'],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('校准完成'), findsOneWidget);
    expect(find.text('已更新的状态'), findsOneWidget);
    expect(find.text('接下来会变化什么'), findsOneWidget);
  });

  testWidgets('checkpoint nudge exposes the unified deep calibration entry',
      (tester) async {
    final fake = _FakeCoreSessionClient(startResult: _session());
    await tester.pumpWidget(
      ProviderScope(
        overrides: [auroraCoreSessionServiceProvider.overrideWithValue(fake)],
        child: testMaterialApp(
          home: const Scaffold(
            body: AuroraNudgeEntry(
              data: {
                'checkpoint_description': 'checkpoint 完成率只有 50%',
                'debrief_context': {'day': 2},
              },
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('深入校准'));
    await tester.pumpAndSettle();

    expect(fake.lastEntryReason?.triggerSource, 'checkpoint_card');
  });

  testWidgets('task stuck sheet keeps chat and adds Core Session entry',
      (tester) async {
    var coreTapped = false;
    var chatTapped = false;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: StuckHelpSheet(
            task: _task(),
            onChatPressed: () => chatTapped = true,
            onCoreSessionPressed: () => coreTapped = true,
          ),
        ),
      ),
    );

    expect(find.text('和Sparkle聊聊这个问题'), findsOneWidget);
    await tester.tap(find.text('和 Aurora 深度校准'));
    await tester.pump();

    expect(coreTapped, isTrue);
    expect(chatTapped, isFalse);
  });

  testWidgets('paused session shows resume entry and resumes with history',
      (tester) async {
    final paused = _session(
      status: 'paused',
      resumeToken: 'acs_paused',
      messages: const [
        AuroraCoreMessage(
          role: 'aurora',
          content: '我们先暂停在这里。',
          stage: 'process_response',
          timestamp: '2026-05-01T00:01:00',
        ),
      ],
    );
    final resumed = _session(
      status: 'active',
      resumeToken: 'acs_resumed',
      messages: const [
        AuroraCoreMessage(
          role: 'aurora',
          content: '我们从刚才暂停的地方继续。',
          stage: 'process_response',
          timestamp: '2026-05-01T00:02:00',
        ),
      ],
    );
    final fake = _FakeCoreSessionClient(
      startResult: paused,
      resumeResult: resumed,
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [auroraCoreSessionServiceProvider.overrideWithValue(fake)],
        child: testMaterialApp(
          home: const Scaffold(
            body: AuroraCoreSessionSheet(
              bandStatus: 'calibration_available',
              wakeReasons: ['plan_drift'],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('继续上次的深度对话'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();

    expect(fake.lastResumeToken, 'acs_paused');
    expect(find.textContaining('从刚才暂停的地方继续'), findsOneWidget);
  });

  testWidgets('expired session shows friendly restart choices', (tester) async {
    final fake = _FakeCoreSessionClient(
      startResult: _session(
        status: 'expired',
        resumeToken: '',
        calibrationResult: const AuroraCalibrationResult(
          updatesApplied: [],
          summary: '上次我们围绕任务节奏聊了 1 轮。',
          userVisibleSummary: '上次我们围绕任务节奏聊了 1 轮。',
          scopeCompleted: '任务节奏',
          strategyChanges: [],
          statePatches: [],
          nextChanges: [],
          sessionId: 'session-1',
          completedAt: '2026-05-01T00:20:00',
        ),
      ),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [auroraCoreSessionServiceProvider.overrideWithValue(fake)],
        child: testMaterialApp(
          home: const Scaffold(
            body: AuroraCoreSessionSheet(
              bandStatus: 'calibration_available',
              wakeReasons: ['plan_drift'],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('上次的深度对话已结束'), findsOneWidget);
    expect(find.text('上次摘要'), findsOneWidget);
    expect(find.text('只是聊天'), findsOneWidget);
    expect(find.text('开始新的深度对话'), findsOneWidget);
  });
}

class _FakeCoreSessionClient implements AuroraCoreSessionClient {
  _FakeCoreSessionClient({
    required this.startResult,
    AuroraCoreSession? respondResult,
    this.resumeResult,
  }) : respondResult = respondResult ?? startResult;

  final AuroraCoreSession startResult;
  final AuroraCoreSession respondResult;
  final AuroraCoreSession? resumeResult;
  AuroraCoreSessionEntryReason? lastEntryReason;
  String? lastContent;
  String? lastResumeToken;
  bool lastIsFreeform = false;

  @override
  Future<AuroraCoreSession> startSession({
    String? conversationId,
    String surface = 'aurora_modeling',
    String sessionType = 'user_initiated',
    String? scope,
    List<String> wakeReasons = const [],
    String bandStatus = 'calibration_available',
    AuroraCoreSessionEntryReason? entryReason,
    String? resumeToken,
  }) async {
    lastEntryReason = entryReason;
    return startResult;
  }

  @override
  Future<AuroraCoreSession> respond({
    required String sessionId,
    required String content,
    String? optionId,
    String? semanticValue,
    Map<String, dynamic>? modelWriteEffect,
    bool isFreeform = false,
  }) async {
    lastContent = content;
    lastIsFreeform = isFreeform;
    return respondResult;
  }

  @override
  Future<AuroraCoreSession?> getCurrentSession() async => null;

  @override
  Future<AuroraCoreSession> resumeSession(String resumeToken) async {
    lastResumeToken = resumeToken;
    return resumeResult ?? startResult;
  }

  @override
  Future<AuroraCoreSession> pauseSession(
    String sessionId, {
    String reason = 'user_request',
  }) async =>
      startResult;

  @override
  Future<AuroraCoreSession> closeSession(String sessionId) async => startResult;
}

AuroraCoreSession _session({
  String status = 'active',
  String resumeToken = 'session-1',
  List<AuroraCoreMessage> messages = const [
    AuroraCoreMessage(
      role: 'aurora',
      content: '我注意到你最近计划偏离。',
      stage: 'declare',
      timestamp: '2026-05-01T00:00:00',
    ),
  ],
  List<AuroraPredictedReplyGroup> optionGroups = const [],
  AuroraCalibrationResult? calibrationResult,
}) {
  return AuroraCoreSession(
    sessionId: 'session-1',
    userId: 'u1',
    conversationId: 'c1',
    surface: 'aurora_modeling',
    status: status,
    stage: 'await_user',
    scope: '当前策略与你的实际情况',
    sessionType: 'user_initiated',
    entryReason: null,
    agenda: null,
    resumeToken: resumeToken,
    messages: messages,
    calibrationResult: calibrationResult,
    userTurnCount: 0,
    auroraMessageCount: messages.where((message) => message.isAurora).length,
    pendingOptionGroups: optionGroups,
    createdAt: '2026-05-01T00:00:00',
    lastActivityAt: '2026-05-01T00:00:00',
    expiresAt: '2026-05-01T00:30:00',
  );
}

AuroraPredictedReplyGroup _simpleGroup() => const AuroraPredictedReplyGroup(
      groupId: 'simple',
      question: '更接近哪一种？',
      questionType: 'assumption_check',
      contextNote: '',
      options: [
        AuroraPredictedReplyOption(
          id: 'freeform_correction',
          label: '都不对，我解释一下',
          semanticValue: 'freeform_correction',
          replyType: 'freeform',
          confidence: 0,
          modelWriteEffect: null,
          isDisconfirming: true,
          isFreeform: true,
          contextSource: 'simple',
          telemetryId: 'simple_freeform',
        ),
      ],
    );

TaskModel _task() {
  final now = DateTime(2026, 5);
  return TaskModel(
    id: 'local-task',
    userId: 'u1',
    title: '整理 TCP 错题原因',
    type: TaskType.learning,
    tags: const ['network'],
    estimatedMinutes: 15,
    difficulty: 2,
    energyCost: 1,
    status: TaskStatus.stuck,
    priority: 1,
    createdAt: now,
    updatedAt: now,
    guideJson: const {
      'if_stuck': ['先定位卡住的具体步骤'],
    },
  );
}
