import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/sparkle_motion_primitives.dart';
import 'package:sparkle/features/aurora/data/models/aurora_comeback_context.dart';
import 'package:sparkle/features/chat/presentation/widgets/comeback_banner.dart';

import '../../../../shared/i18n_test_helper.dart';

AuroraComebackContext _context({
  List<AuroraComebackItem> items = const [],
  String resumeToken = '',
}) =>
    AuroraComebackContext(
      comebackKind: 'light_resume',
      title: '接着刚才的线',
      message: '继续上次的「函数极限」。上次 Aurora 问的是：「先看夹逼准则吗？」',
      shouldShowMessage: true,
      lastActiveAt: '2026-05-01T10:00:00',
      inactiveMinutes: 120,
      daysAway: 0,
      daysRemaining: 4,
      subject: '函数极限',
      nextTaskTitle: '夹逼准则复盘',
      recentTaskSummary: '夹逼准则',
      lightRestartSuggestion: '先开一个 30 分钟保底版。',
      planId: 'plan-1',
      conversationId: 'conversation-1',
      lastMessageId: 'message-2',
      topicSummary: '函数极限',
      pendingQuestion: '先看夹逼准则吗？',
      activeCoreSession:
          resumeToken.isEmpty ? const {} : {'resume_token': resumeToken},
      resumeToken: resumeToken,
      unfinishedItems: items,
      calendarNote: '',
    );

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('renders comeback message and unfinished items', (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ComebackBanner(
            contextData: _context(
              items: const [
                AuroraComebackItem(
                  type: 'pending_question',
                  title: '上次的问题还挂着',
                  subtitle: '先看夹逼准则吗？',
                  actionLabel: '回答',
                  route: '',
                  resumeToken: '',
                ),
              ],
            ),
          ),
        ),
      ),
    );

    expect(find.text('接着刚才的线'), findsOneWidget);
    expect(find.textContaining('函数极限'), findsOneWidget);
    expect(find.text('上次的问题还挂着'), findsOneWidget);
  });

  testWidgets('stages comeback title, summary, and unfinished items',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ComebackBanner(
            contextData: _context(
              items: const [
                AuroraComebackItem(
                  type: 'task',
                  title: '夹逼准则复盘',
                  subtitle: '30 分钟',
                  actionLabel: '继续',
                  route: '/tasks/task-1/execute',
                  resumeToken: '',
                ),
              ],
            ),
          ),
        ),
      ),
    );

    expect(find.byType(SparkleStaggerItem), findsNWidgets(3));
  });

  testWidgets('pointer down skips staged comeback entrance animation',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ComebackBanner(contextData: _context()),
        ),
      ),
    );

    expect(find.byType(SparkleStaggerItem), findsNWidgets(2));

    await tester.tap(find.text('接着刚才的线'));
    await tester.pump();

    expect(find.byType(SparkleStaggerItem), findsNothing);
  });

  testWidgets('dismiss button calls callback', (tester) async {
    var dismissed = false;
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ComebackBanner(
            contextData: _context(),
            onDismiss: () => dismissed = true,
          ),
        ),
      ),
    );

    await tester.tap(find.byIcon(Icons.close_rounded));
    expect(dismissed, isTrue);
  });

  testWidgets('resume and item actions are exposed', (tester) async {
    var resumed = false;
    AuroraComebackItem? selected;
    const taskItem = AuroraComebackItem(
      type: 'task',
      title: '夹逼准则复盘',
      subtitle: '30 分钟',
      actionLabel: '去看看',
      route: '/tasks/task-1/execute',
      resumeToken: '',
    );

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ComebackBanner(
            contextData: _context(items: const [taskItem], resumeToken: 's1'),
            onResumeCoreSession: () => resumed = true,
            onItemSelected: (item) => selected = item,
          ),
        ),
      ),
    );

    await tester.tap(find.byIcon(Icons.play_arrow_rounded));
    expect(resumed, isTrue);

    await tester.tap(find.text('夹逼准则复盘'));
    expect(selected?.route, '/tasks/task-1/execute');
  });

  // ── A-07: goal-state restore + low-stimulation interaction ────────────────

  testWidgets('renders real goal state instead of template-only greeting',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: ComebackBanner(contextData: _contextWithGoalState()),
        ),
      ),
    );

    // 目标标题 + 任务账本口径进度（与任务板/多目标看板同行同数）。
    expect(find.text('期末计算机网络冲 85 分'), findsOneWidget);
    expect(find.text('1/2'), findsOneWidget);
  });

  testWidgets('low-stimulation: entrance motion attenuated, goal state stays',
      (tester) async {
    await tester.pumpWidget(
      testMaterialApp(
        // 低刺激档经 EmotionResponsiveAppWrapper 落到 MediaQuery 关动效；
        // 这里直接模拟该运行面。
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: Scaffold(
            body: ComebackBanner(contextData: _contextWithGoalState()),
          ),
        ),
      ),
    );
    await tester.pump();

    // 动效减法：无分步入场动画；事实内容（真实目标状态）完整保留。
    expect(find.byType(SparkleStaggerItem), findsNothing);
    expect(find.text('期末计算机网络冲 85 分'), findsOneWidget);
    expect(find.text('1/2'), findsOneWidget);
  });
}

AuroraComebackContext _contextWithGoalState() {
  final base = _context();
  return AuroraComebackContext(
    comebackKind: base.comebackKind,
    title: base.title,
    message: base.message,
    shouldShowMessage: base.shouldShowMessage,
    lastActiveAt: base.lastActiveAt,
    inactiveMinutes: base.inactiveMinutes,
    daysAway: base.daysAway,
    daysRemaining: base.daysRemaining,
    subject: base.subject,
    nextTaskTitle: base.nextTaskTitle,
    recentTaskSummary: base.recentTaskSummary,
    lightRestartSuggestion: base.lightRestartSuggestion,
    planId: base.planId,
    conversationId: base.conversationId,
    lastMessageId: base.lastMessageId,
    topicSummary: base.topicSummary,
    pendingQuestion: base.pendingQuestion,
    activeCoreSession: base.activeCoreSession,
    resumeToken: base.resumeToken,
    unfinishedItems: base.unfinishedItems,
    calendarNote: base.calendarNote,
    goalState: const AuroraComebackGoalState(
      goalId: 'goal-1',
      title: '期末计算机网络冲 85 分',
      status: 'active',
      progress: 0,
      ledgerCompleted: 1,
      ledgerTotal: 2,
    ),
  );
}
