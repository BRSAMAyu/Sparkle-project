import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
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
import 'package:sparkle/l10n/app_localizations.dart';

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

  testWidgets(
    'reduce-motion：复盘纸屑覆盖层首帧即静止终态，泵进不位移（G01/S01 判例）',
    (tester) async {
      final offsets = await _pumpReviewAndCollectConfetti(
        tester,
        disableAnimations: true,
      );
      expect(offsets.before, isNotEmpty, reason: '纸屑覆盖层必须挂载');
      expect(
        offsets.before,
        offsets.afterWindow,
        reason: 'reduce-motion 下纸屑两段隐式动画必须直落静止终态'
            '（S01 判例：不制造动画帧，视觉等价）',
      );
    },
  );

  testWidgets(
    '常规路径对照：纸屑随泵进位移（探针有判别力）',
    (tester) async {
      final offsets = await _pumpReviewAndCollectConfetti(tester);
      expect(offsets.before, isNotEmpty);
      expect(
        offsets.before,
        isNot(offsets.afterWindow),
        reason: '常规路径纸屑必须随泵进位移（控制组证明静态分支有判别力）',
      );
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

/// V4-G01 reduce-motion 判例泵制：填表提交触发纸屑覆盖层，读全部
/// auto_awesome_rounded 图标（6 纸屑粒 + 1 中心卡）纵向位置——读一次、
/// 泵进完整动画窗口（最长粒 620+5×70=970ms）再读一次，返回两批位置。
/// `disableAnimations` 走 S01 双源判例（MediaQuery.disableAnimations）。
Future<({List<Offset> before, List<Offset> afterWindow})>
    _pumpReviewAndCollectConfetti(
  WidgetTester tester, {
  bool disableAnimations = false,
}) async {
  await _useTallSurface(tester);
  await tester.pumpWidget(
    _buildApp(
      repository: _RecordingExamSprintRepository(),
      child: MediaQuery(
        data: MediaQueryData(disableAnimations: disableAnimations),
        child: PostExamReviewScreen(
          planId: 'plan-g01-rm',
          subjectName: '高数',
          // 拉长成功延迟以保持覆盖层挂载供观测；收尾泵过计时器防 pending。
          successDelay: const Duration(seconds: 30),
          onSuccess: () {},
        ),
      ),
    ),
  );
  await tester.pump();
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
  await tester.pump(const Duration(milliseconds: 16));

  List<Offset> collectTops() {
    final elements = find
        .byWidgetPredicate(
          (w) => w is Icon && w.icon == Icons.auto_awesome_rounded,
        )
        .evaluate()
        .toList();
    return elements
        .map(
          (e) => tester.getTopLeft(
            find.byElementPredicate((other) => identical(other, e)),
          ),
        )
        .toList();
  }

  final before = collectTops();
  await tester.pump(const Duration(milliseconds: 1000));
  final afterWindow = collectTops();

  // 冲掉 successDelay 的 pending timer（onSuccess 空转，不导航）。
  await tester.pump(const Duration(seconds: 30));
  await tester.pump();
  return (before: before, afterWindow: afterWindow);
}

Widget _buildApp({
  required _RecordingExamSprintRepository repository,
  required Widget child,
}) =>
    ProviderScope(
      overrides: [
        examSprintRepositoryProvider.overrideWithValue(repository),
      ],
      child: testMaterialApp(
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
