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
}
