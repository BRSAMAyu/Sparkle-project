import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/plan/presentation/screens/post_exam_review_screen.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('renders all post-exam review fields and submit button',
      (tester) async {
    await _useTallSurface(tester);
    await tester.pumpWidget(
      _buildApp(
        repository: _RecordingExamSprintRepository(),
        child: const PostExamReviewScreen(
          planId: 'plan-1',
          subjectName: '高数',
        ),
      ),
    );

    expect(find.text('考试复盘 · 高数'), findsWidgets);
    expect(find.text('考试结果'), findsOneWidget);
    expect(find.text('星级评分'), findsOneWidget);
    expect(find.text('大概考了多少分？'), findsOneWidget);
    expect(find.text('最大挑战'), findsOneWidget);
    expect(find.text('考试中遇到的最大困难是什么？'), findsOneWidget);
    expect(find.text('策略感受'), findsOneWidget);
    expect(find.text('回头看，复习策略有什么需要改进的？'), findsOneWidget);
    expect(find.text('给未来自己的建议'), findsWidgets);
    expect(
      find.byKey(const ValueKey('post-exam-review-submit')),
      findsOneWidget,
    );
  });

  testWidgets(
    'submits result_rating 4 with expected review payload',
    (tester) async {
      await _useTallSurface(tester);
      var navigatedHome = false;
      final repository = _RecordingExamSprintRepository();

      await tester.pumpWidget(
        _buildApp(
          repository: repository,
          child: PostExamReviewScreen(
            planId: 'plan-42',
            subjectName: '计算机网络',
            successDelay: Duration.zero,
            onSuccess: () => navigatedHome = true,
          ),
        ),
      );

      await tester.tap(
        find.byKey(const ValueKey('post-exam-review-rating-star-4')),
      );
      await tester.enterText(
        find.byKey(const ValueKey('post-exam-review-result-description')),
        '估计 82 分',
      );
      await tester.enterText(
        find.byKey(const ValueKey('post-exam-review-challenge')),
        '证明题时间不够',
      );
      await tester.enterText(
        find.byKey(const ValueKey('post-exam-review-strategy')),
        '真题训练应该更早开始',
      );
      await tester.enterText(
        find.byKey(const ValueKey('post-exam-review-self-advice')),
        '考前两天只做错题和公式',
      );

      await tester.tap(find.byKey(const ValueKey('post-exam-review-submit')));
      await tester.pump();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1));

      expect(repository.requests, hasLength(1));
      expect(repository.requests.single.toJson(), <String, dynamic>{
        'plan_id': 'plan-42',
        'result_rating': 4,
        'result_description': '估计 82 分',
        'biggest_challenge': '证明题时间不够',
        'strategy_feedback': '真题训练应该更早开始',
        'self_advice': '考前两天只做错题和公式',
      });
      expect(navigatedHome, isTrue);
    },
  );

  testWidgets('/exam-sprint/review navigates to post-exam review screen',
      (tester) async {
    await _useTallSurface(tester);
    final router = GoRouter(
      navigatorKey: navigatorKey,
      initialLocation:
          '/exam-sprint/review?plan_id=plan-route&subject=%E8%8B%B1%E8%AF%AD',
      routes: [
        GoRoute(
          path: '/home',
          builder: (context, state) => const Scaffold(body: Text('home')),
        ),
        ...PlanRoutes.routes,
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp.router(
          routerConfig: router,
          theme: AppThemes.lightTheme,
        ),
      ),
    );

    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byType(PostExamReviewScreen), findsOneWidget);
    expect(find.text('考试复盘 · 英语'), findsWidgets);
    expect(find.text('考试结果'), findsOneWidget);
  });
}

Future<void> _useTallSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(900, 1800));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

Widget _buildApp({
  required _RecordingExamSprintRepository repository,
  required Widget child,
}) =>
    ProviderScope(
      overrides: [
        examSprintRepositoryProvider.overrideWithValue(repository),
      ],
      child: MaterialApp(
        theme: AppThemes.lightTheme,
        home: child,
      ),
    );

class _RecordingExamSprintRepository extends ExamSprintRepository {
  _RecordingExamSprintRepository() : super(_NoopApiClient());

  final List<PostExamReviewRequest> requests = <PostExamReviewRequest>[];

  @override
  Future<void> submitPostExamReview(PostExamReviewRequest request) async {
    requests.add(request);
  }
}

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
