import 'dart:io';

import 'package:flutter/material.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/screens/milestone_celebration_screen.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('milestone celebration screen renders mock milestone stats',
      (tester) async {
    await _useTallSurface(tester);
    await tester.pumpWidget(
      _buildApp(
        const MilestoneCelebrationScreen(
          payload: MilestoneCelebrationPayload(
            milestoneId: '30_day_learner',
            celebrationValue: 30,
            studyDays: 30,
            masteredNodes: 67,
            completedSprints: 2,
            errorCount: 23,
            shareHashtag: '#30天打卡',
          ),
        ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 1500));

    expect(find.text('你已经坚持学习 30 天了'), findsOneWidget);
    expect(find.byKey(const ValueKey('milestone-big-number')), findsOneWidget);
    expect(find.text('学习天数'), findsOneWidget);
    expect(find.text('掌握节点'), findsOneWidget);
    expect(find.text('完成冲刺'), findsOneWidget);
    expect(find.text('30'), findsWidgets);
    expect(find.text('67'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
  });

  testWidgets('milestone celebration share text includes hashtag',
      (tester) async {
    await _useTallSurface(tester);
    var shared = false;
    var sharedText = '';

    await tester.pumpWidget(
      _buildApp(
        MilestoneCelebrationScreen(
          payload: const MilestoneCelebrationPayload(
            milestoneId: '30_day_learner',
            celebrationValue: 30,
            studyDays: 30,
            masteredNodes: 67,
            completedSprints: 2,
            errorCount: 23,
            shareHashtag: '#30天打卡',
          ),
          shareImageBuilder: () async =>
              File('/tmp/sparkle-milestone-test.png'),
          shareLauncher: (imageFile, text) async {
            shared = true;
            sharedText = text;
          },
        ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 1500));
    await tester.tap(find.byKey(const ValueKey('milestone-share')));
    await tester.pump();
    await tester.pump();

    expect(shared, isTrue);
    expect(sharedText, contains('#30天打卡'));
    expect(sharedText, contains('67 个知识节点'));
  });

  testWidgets(
      'milestone celebration payload from query parameters renders route data',
      (tester) async {
    await _useTallSurface(tester);
    final payload = MilestoneCelebrationPayload.fromQueryParameters(
      '30_day_learner',
      const <String, String>{
        'study_days': '30',
        'mastered_nodes': '67',
        'completed_sprints': '2',
        'error_count': '23',
        'share_hashtag': '#30天打卡',
        'celebration_value': '30',
      },
    );

    await tester.pumpWidget(
      _buildApp(
        MilestoneCelebrationScreen(payload: payload),
      ),
    );

    await tester.pump(const Duration(milliseconds: 1500));

    expect(find.text('你已经坚持学习 30 天了'), findsOneWidget);
    expect(find.text('67'), findsOneWidget);
    expect(find.text('2'), findsOneWidget);
    expect(find.text('23'), findsOneWidget);
  });

  testWidgets('close falls back to achievements when opened directly',
      (tester) async {
    await _useTallSurface(tester);
    final router = GoRouter(
      initialLocation: '/milestone',
      routes: [
        GoRoute(
          path: '/achievements',
          builder: (context, state) =>
              const Scaffold(body: Center(child: Text('ACHIEVEMENTS'))),
        ),
        GoRoute(
          path: '/milestone',
          builder: (context, state) => const MilestoneCelebrationScreen(
            payload: MilestoneCelebrationPayload(
              milestoneId: '30_day_learner',
              celebrationValue: 30,
              studyDays: 30,
              masteredNodes: 67,
              completedSprints: 2,
              errorCount: 23,
              shareHashtag: '#30天打卡',
            ),
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
        locale: const Locale('zh'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
              ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 1500));
    await tester.tap(find.byIcon(Icons.close_rounded));
    await tester.pumpAndSettle();

    expect(find.text('ACHIEVEMENTS'), findsOneWidget);
  });
}

Future<void> _useTallSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(900, 1500));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

Widget _buildApp(Widget child) => ProviderScope(
      child: testMaterialApp(
        theme: AppThemes.lightTheme,
        home: child,
      ),
    );
