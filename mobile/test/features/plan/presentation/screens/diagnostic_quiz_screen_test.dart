import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';
import 'package:sparkle/features/plan/presentation/screens/diagnostic_quiz_screen.dart';
import '../../../../shared/i18n_test_helper.dart';

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeDiagnosticRepository extends ExamSprintRepository {
  _FakeDiagnosticRepository({this.generated, this.graded})
      : super(_NoopApiClient());

  final DiagnosticGenerateResult? generated;
  final DiagnosticGradeResult? graded;

  int generateCalls = 0;
  int gradeCalls = 0;
  String? lastDiagnosticId;
  List<DiagnosticAnswerInput>? lastAnswers;

  @override
  Future<DiagnosticGenerateResult> generateDiagnostic({
    required String subject,
    int questionCount = 10,
  }) async {
    generateCalls += 1;
    final result = generated;
    if (result == null) {
      throw Exception('generate failed');
    }
    return result;
  }

  @override
  Future<DiagnosticGradeResult> gradeDiagnostic({
    required String subject,
    required String diagnosticId,
    required List<DiagnosticAnswerInput> answers,
  }) async {
    gradeCalls += 1;
    lastDiagnosticId = diagnosticId;
    lastAnswers = answers;
    return graded!;
  }
}

DiagnosticGenerateResult _makeGenerated() => const DiagnosticGenerateResult(
      diagnosticId: 'diag-test-1',
      subject: '计算机网络',
      questionCount: 2,
      estimatedMinutes: 2,
      questions: [
        DiagnosticQuestion(
          questionId: 'q1',
          domain: 'TCP 可靠传输',
          questionType: 'single_choice',
          stem: 'TCP 提供可靠传输服务吗？',
          choices: ['可靠', '不可靠'],
        ),
        DiagnosticQuestion(
          questionId: 'q2',
          domain: 'HTTP / DNS',
          questionType: 'short_answer',
          stem: '简述 DNS 的作用。',
          choices: [],
        ),
      ],
    );

DiagnosticGradeResult _makeGraded() => const DiagnosticGradeResult(
      estimatedScoreNow: 80,
      passProbability: 0.9,
      recommendedPath: 'score_max',
      topBottlenecks: [
        DiagnosticBottleneckResult(
          nodeName: 'TCP 可靠传输',
          domain: 'TCP 可靠传输',
          mastery: 40,
          reason: '相关题得分偏低',
        ),
      ],
    );

Widget _wrapScreen(ExamSprintRepository repository) => ProviderScope(
      overrides: [
        examSprintRepositoryProvider.overrideWithValue(repository),
      ],
      child: testMaterialApp(
        theme: ThemeData.light().copyWith(
          extensions: [SparkleThemeExtension.light()],
        ),
        home: const DiagnosticQuizScreen(),
      ),
    );

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('loads questions, collects answers and grades via diagnostic_id',
      (tester) async {
    final repository = _FakeDiagnosticRepository(
      generated: _makeGenerated(),
      graded: _makeGraded(),
    );

    await tester.pumpWidget(_wrapScreen(repository));
    await tester.pumpAndSettle();

    // questions rendered
    expect(find.text('TCP 提供可靠传输服务吗？'), findsOneWidget);
    expect(find.text('简述 DNS 的作用。'), findsOneWidget);
    expect(repository.generateCalls, 1);

    // answer the single choice
    await tester.tap(find.text('可靠'));
    await tester.pump();

    // answer the short answer
    await tester.enterText(find.byType(TextField), '域名解析');
    await tester.pump();

    // submit (scroll the button into view first)
    await tester.scrollUntilVisible(
      find.text('交卷并查看结果'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('交卷并查看结果'));
    await tester.pumpAndSettle();

    expect(repository.gradeCalls, 1);
    expect(repository.lastDiagnosticId, 'diag-test-1');
    expect(repository.lastAnswers, hasLength(2));
    expect(repository.lastAnswers![0].answer, '可靠');

    // result view rendered
    expect(find.text('当前估分 80.0 分'), findsOneWidget);
    expect(find.text('过考概率 90%'), findsOneWidget);
    expect(find.text('TCP 可靠传输'), findsOneWidget);
  });

  testWidgets('shows retry state when generation fails', (tester) async {
    final repository = _FakeDiagnosticRepository();

    await tester.pumpWidget(_wrapScreen(repository));
    await tester.pumpAndSettle();

    expect(find.text('诊断加载失败，请稍后重试'), findsOneWidget);
  });
}
