import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/recovery/data/models/stuck_journey_models.dart';
import 'package:sparkle/features/recovery/data/repositories/stuck_journey_repository.dart';
import 'package:sparkle/features/recovery/presentation/widgets/stuck_journey_sheet.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// J-05 ·「我卡住了」统一恢复旅程——sheet 行为契约：
/// ① 最多一个问题（问题 + 分支选项渲染，点选即答）；
/// ② 主 intervention 展示（含 uncertain 标注）；
/// ③ 「不是这个原因」纠正 → correct 调用携带被纠正类型 → 纠正后的
///    旅程输出立即可见（反馈环不静默）。
class _FakeRepository implements StuckJourneyRepository {  _FakeRepository(this.startPayload);

  final Map<String, dynamic> startPayload;

  final List<Map<String, dynamic>> startCalls = <Map<String, dynamic>>[];
  final List<Map<String, dynamic>> answerCalls = <Map<String, dynamic>>[];
  final List<Map<String, dynamic>> correctCalls = <Map<String, dynamic>>[];

  Map<String, dynamic> answerPayload = <String, dynamic>{};
  Map<String, dynamic> correctResponse = <String, dynamic>{};

  @override
  Future<StuckJourneyPayload> startJourney({
    required String surface,
    String? goalId,
    String? taskId,
  }) async {
    startCalls.add({
      'surface': surface,
      'goal_id': goalId,
      'task_id': taskId,
    });
    return StuckJourneyPayload.fromJson(startPayload);
  }

  @override
  Future<StuckJourneyPayload> answerQuestion({
    required String surface,
    required String questionId,
    required String branchKey,
    String? goalId,
    String? taskId,
  }) async {
    answerCalls.add({
      'surface': surface,
      'question_id': questionId,
      'branch_key': branchKey,
    });
    return StuckJourneyPayload.fromJson(answerPayload);
  }

  @override
  Future<StuckJourneyCorrectionResult> correct({
    required String surface,
    required String frictionType,
    String? interventionKey,
    String? goalId,
    String? taskId,
    String? reasonText,
  }) async {
    correctCalls.add({
      'surface': surface,
      'friction_type': frictionType,
      'intervention_key': interventionKey,
    });
    return StuckJourneyCorrectionResult.fromJson(correctResponse);
  }
}

Map<String, dynamic> questionPayload() => <String, dynamic>{
      'version': 'stuck_journey.v1',
      'surface': 'action',
      'outcome': 'ask',
      'friction_type': 'unknown',
      'question': <String, dynamic>{
        'question_id': 'q_tried_and_checked',
        'text': '自己完整试过一遍了吗？做出来的部分，有把握是对的？',
        'branch_options': <dynamic>[
          <String, dynamic>{'key': 'not_tried', 'label': '还没试过'},
          <String, dynamic>{'key': 'tried_unsure', 'label': '试过，没把握'},
          <String, dynamic>{'key': 'tried_confident', 'label': '试过，也对，就是推进慢'},
        ],
      },
      'main_intervention': null,
      'uncertain': false,
      'context': <String, dynamic>{
        'goal': <String, dynamic>{'id': 'g1', 'title': '线代一轮复习'},
        'task': <String, dynamic>{'id': 't1', 'title': '特征值练习'},
        'recent_failures': <String, dynamic>{'count': 3, 'titles': <String>[]},
        'days_since_progress': 6,
      },
      'receipt': <String, dynamic>{},
      'annotations': <String, dynamic>{},
    };

Map<String, dynamic> interventionPayload() => <String, dynamic>{
      ...questionPayload(),
      'outcome': 'act',
      'friction_type': 'skill',
      'question': null,
      'main_intervention': <String, dynamic>{
        'type': 'practice',
        'nominated': <String>['practice', 'explain'],
        'friction_type': 'skill',
        'uncertain': false,
        'adjusted_by_correction': false,
      },
    };

Map<String, dynamic> correctedInterventionPayload() => <String, dynamic>{
      ...interventionPayload(),
      'main_intervention': <String, dynamic>{
        'type': 'split',
        'nominated': <String>['split', 'practice'],
        'friction_type': 'entry',
        'uncertain': false,
        'adjusted_by_correction': true,
      },
      'receipt': <String, dynamic>{'correction_active': true},
      'annotations': <String, dynamic>{'corrected_this_turn': true},
    };

Widget _harness(Widget child, List<Override> overrides) => ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        theme: ThemeData(extensions: [SparkleThemeExtension.light()]),
        locale: const Locale('zh'),
        supportedLocales: const [Locale('en'), Locale('zh')],
        localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
        home: Scaffold(body: child),
      ),
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets('renders the single question with branch options', (tester) async {
    final repo = _FakeRepository(questionPayload());
    await tester.pumpWidget(
      _harness(
        const StuckJourneySheetBody(
          request: StuckJourneyRequest(surface: 'action', taskId: 't1'),
        ),
        [stuckJourneyRepositoryProvider.overrideWithValue(repo)],
      ),
    );
    await tester.pumpAndSettle();

    // 单问：问题文本 + 全部分支选项，且没有第二问。
    expect(
      find.text('自己完整试过一遍了吗？做出来的部分，有把握是对的？'),
      findsOneWidget,
    );
    expect(find.text('还没试过'), findsOneWidget);
    expect(find.text('试过，没把握'), findsOneWidget);
    expect(find.text('试过，也对，就是推进慢'), findsOneWidget);
    // 真实 context 锚点随 sheet 展示。
    expect(find.textContaining('特征值练习'), findsWidgets);
  });

  testWidgets('answering calls back with question id and branch key',
      (tester) async {
    final repo = _FakeRepository(questionPayload())
      ..answerPayload = interventionPayload();
    await tester.pumpWidget(
      _harness(
        const StuckJourneySheetBody(
          request: StuckJourneyRequest(surface: 'action', taskId: 't1'),
        ),
        [stuckJourneyRepositoryProvider.overrideWithValue(repo)],
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('还没试过'));
    await tester.pumpAndSettle();

    expect(repo.answerCalls, hasLength(1));
    expect(repo.answerCalls.first['question_id'], 'q_tried_and_checked');
    expect(repo.answerCalls.first['branch_key'], 'not_tried');
    // 回答后收敛到主 intervention。
    expect(find.text('用一个练习把方法跑一遍'), findsOneWidget);
  });

  testWidgets('「不是这个原因」correction reaches backend and shows updated output',
      (tester) async {
    final repo = _FakeRepository(questionPayload())
      ..answerPayload = interventionPayload()
      ..correctResponse = <String, dynamic>{
        'correction_id': 'c1',
        'receipt': <String, dynamic>{},
        'journey': correctedInterventionPayload(),
      };
    await tester.pumpWidget(
      _harness(
        const StuckJourneySheetBody(
          request: StuckJourneyRequest(surface: 'action', taskId: 't1'),
        ),
        [stuckJourneyRepositoryProvider.overrideWithValue(repo)],
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('还没试过'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('不是这个原因'));
    await tester.pumpAndSettle();

    expect(repo.correctCalls, hasLength(1));
    expect(repo.correctCalls.first['friction_type'], 'skill');
    expect(repo.correctCalls.first['intervention_key'], 'practice');
    // 纠正后的旅程输出立即可见：主判断换成垫后方向 + 纠正回执文案。
    expect(find.text('把这一步拆成更小的几步'), findsOneWidget);
    expect(find.text('收到，之后这类原因会往后放'), findsOneWidget);
  });
}
