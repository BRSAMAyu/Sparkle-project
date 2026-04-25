import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_completion_screen.dart';

void main() {
  testWidgets(
    'sprint completion screen renders mastered and repaired counts',
    (tester) async {
      await _useTallSurface(tester);
      await tester.pumpWidget(
        _buildApp(
          SprintCompletionScreen(
            planId: 'plan-1',
            subjectName: '计算机网络',
            initialSummary: _summary(),
          ),
        ),
      );

      await tester.pump(const Duration(milliseconds: 950));

      expect(find.text('你的 7 天备考成果'), findsOneWidget);
      expect(find.text('32'), findsOneWidget);
      expect(find.text('8'), findsOneWidget);
      expect(find.text('知识节点'), findsOneWidget);
      expect(find.text('错误模式'), findsOneWidget);
      expect(find.text('最强项：'), findsOneWidget);
      expect(find.text('TCP/IP 协议栈'), findsOneWidget);
    },
  );

  testWidgets('share button invokes system share flow with hashtag',
      (tester) async {
    await _useTallSurface(tester);
    var shared = false;
    var sharedText = '';

    await tester.pumpWidget(
      _buildApp(
        SprintCompletionScreen(
          planId: 'plan-1',
          subjectName: '计算机网络',
          initialSummary: _summary(),
          shareImageBuilder: () async => File('/tmp/sparkle-share-test.png'),
          shareLauncher: (imageFile, text) async {
            shared = true;
            sharedText = text;
          },
        ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 950));
    await tester.tap(find.byKey(const ValueKey('sprint-completion-share')));
    await tester.pump();
    await tester.pump();

    expect(shared, isTrue);
    expect(sharedText, contains('#Sparkle备考'));
  });

  testWidgets('close falls back to learning portfolio when opened directly',
      (tester) async {
    await _useTallSurface(tester);
    final router = GoRouter(
      initialLocation: '/completion',
      routes: [
        GoRoute(
          path: '/exam-sprint/portfolio',
          builder: (context, state) =>
              const Scaffold(body: Center(child: Text('PORTFOLIO'))),
        ),
        GoRoute(
          path: '/completion',
          builder: (context, state) => SprintCompletionScreen(
            planId: 'plan-1',
            subjectName: '计算机网络',
            initialSummary: _summary(),
          ),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp.router(
          theme: AppThemes.lightTheme,
          routerConfig: router,
        ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 950));
    await tester.tap(find.byIcon(Icons.close_rounded));
    await tester.pumpAndSettle();

    expect(find.text('PORTFOLIO'), findsOneWidget);
  });
}

Future<void> _useTallSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(900, 1500));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

Widget _buildApp(Widget child) => ProviderScope(
      child: MaterialApp(
        theme: AppThemes.lightTheme,
        home: child,
      ),
    );

SprintCompletionSummary _summary() => const SprintCompletionSummary(
      masteredNodesCount: 32,
      repairedErrorsCount: 8,
      completedTasksCount: 14,
      strongestArea: 'TCP/IP 协议栈',
      growthArea: '子网划分',
    );
