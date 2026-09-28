import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/learning/data/learning_journey_models.dart';
import 'package:sparkle/features/learning/data/learning_journey_repository.dart';
import 'package:sparkle/features/learning/presentation/providers/learning_journey_provider.dart';
import 'package:sparkle/features/learning/presentation/screens/learning_journey_screen.dart';

import '../../../shared/i18n_test_helper.dart';

/// V4-U10 · 旅程页 widget 守卫（三条验收的 UI 面，一正一反可失败）。
///
/// 仓库假体：检验入口返回**带答案的原始载荷**（模拟服务端契约违约最坏情形）——
/// 红化门必须降级拒显，答案串不得出现在任何用户可读树中。
class _FakeJourneyRepository extends LearningJourneyRepository {
  _FakeJourneyRepository({this.leakyCheckPayload = false}) : super(Dio());

  final bool leakyCheckPayload;

  bool checkRequested = false;

  @override
  Future<LearningJourneyView> getJourney({required String goalTaskId}) async =>
      LearningJourneyView.fromJson(<Object?, Object?>{
        'goal': <Object?, Object?>{'task_id': goalTaskId, 'title': '力学单元巩固'},
        'scaffold': <Object?, Object?>{
          'stage': 'attempt',
          'hint_level': 'reduced',
          'segment': 'practice',
        },
        'materials': <Object?>[
          <Object?, Object?>{
            'file_name': '讲义-第3章.pdf',
            'mime_type': 'application/pdf',
            'source': <Object?, Object?>{
              'source_id': 'file-abc',
              'source_version': '2026-09-28T10:00:00',
              'source_kind': 'document',
            },
            'parse': <Object?, Object?>{
              'status': 'parsed',
              'manual_input_required': false,
            },
          },
          <Object?, Object?>{
            'file_name': '手写题拍照.jpg',
            'mime_type': 'image/jpeg',
            'source': <Object?, Object?>{
              'source_id': 'file-img',
              'source_version': '2026-09-28T09:00:00',
              'source_kind': 'document',
            },
            'parse': <Object?, Object?>{
              'status': 'unsupported',
              'reason': 'ocr_unavailable_for_image',
              'manual_input_required': true,
            },
          },
        ],
        'errors': <Object?>[
          <Object?, Object?>{
            'id': 'error-1',
            'subject_code': 'physics',
            'question_text': '斜面上的物体为什么匀速下滑？',
            'review_count': 2,
            'source': <Object?, Object?>{
              'source_id': 'error-1',
              'source_version': '2026-09-28T08:00:00',
              'source_kind': 'error_record',
            },
          },
        ],
        'practice': <Object?, Object?>{'evidence_supported': true},
        'check': <Object?, Object?>{'question': '独立解释：为什么滑动摩擦力与接触面积无关？'},
      });

  @override
  Future<CheckEnterResult> enterCheck({required String goalTaskId}) async {
    checkRequested = true;
    if (leakyCheckPayload) {
      // 服务端契约违约最坏情形：答案材料随载荷下发。
      // I07 约定：检验节点自带 kind 标记（红化触发面）。
      return CheckEnterResult(
        available: true,
        question: LearningCheckQuestion.sanitize(<Object?, Object?>{
          'check_available': true,
          'question': '独立解释：为什么滑动摩擦力与接触面积无关？',
          'independent_check': <Object?, Object?>{
            'kind': 'independent_check',
            'answer': '压力决定摩擦力，而非面积',
          },
        }),
      );
    }
    return CheckEnterResult(
      available: true,
      question: LearningCheckQuestion.sanitize(<Object?, Object?>{
        'check_available': true,
        'question': '独立解释：为什么滑动摩擦力与接触面积无关？',
      }),
    );
  }

  @override
  Future<LearningCheckVerdict> submitCheck({
    required String goalTaskId,
    required String answer,
  }) async =>
      LearningCheckVerdict.fromJson(<Object?, Object?>{
        'graded': true,
        'correct': true,
        'reason': 'OK.check_graded_correct',
        'feedback': '检验通过：这一步由你独立完成。',
      });
}

Future<void> _scrollToCheckCard(WidgetTester tester) async {
  await tester.scrollUntilVisible(
    find.byKey(const Key('learning_check_card')),
    200,
    scrollable: find
        .descendant(
          of: find.byKey(const Key('learning_journey_screen')),
          matching: find.byType(Scrollable),
        )
        .first,
  );
  await tester.pump();
}

void main() {
  setUp(setUpI18nForTesting);

  final journeyContext = LearningJourneyContext.fromLaunch(goalTaskId: 't1', goalTitle: '力学单元巩固');

  Future<void> pumpJourney(
    WidgetTester tester, {
    required _FakeJourneyRepository repository,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          learningJourneyRepositoryProvider.overrideWithValue(repository),
        ],
        child: testMaterialApp(home: LearningJourneyScreen(journeyContext: journeyContext)),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
  }

  testWidgets('验收1 正：从目标进入携带上下文——目标头+继续动作+三段全渲染（非空页）',
      (tester) async {
    await pumpJourney(tester, repository: _FakeJourneyRepository());

    // 上下文头：目标标题 + 继续当前动作（不丢上下文）。
    expect(find.byKey(const Key('learning_context_header')), findsOneWidget);
    expect(find.text('力学单元巩固'), findsOneWidget);
    expect(find.byKey(const Key('learning_continue_action')), findsOneWidget);

    // 三段可读面（资料/错题/检验）——不是无上下文的工具空页。
    expect(find.byKey(const Key('learning_section_0')), findsOneWidget);
    expect(find.byKey(const Key('learning_section_1')), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('learning_section_2')),
      200,
      scrollable: find.descendant(
        of: find.byKey(const Key('learning_journey_screen')),
        matching: find.byType(Scrollable),
      ).first,
    );
    await tester.pump();
    expect(find.byKey(const Key('learning_section_2')), findsOneWidget);
    expect(find.text('讲义-第3章.pdf'), findsOneWidget);
    expect(find.text('斜面上的物体为什么匀速下滑？'), findsOneWidget);

    // 来源badge带真实版本（来源可见）。
    expect(find.byKey(const Key('learning_source_badge')), findsWidgets);
    expect(find.textContaining('2026-09-28T10:00:00'), findsOneWidget);
  });

  testWidgets('验收1 反：空标题的目标入口在起飞前失败（不落地无上下文空页）',
      (tester) async {
    expect(
      () => LearningJourneyContext.fromLaunch(goalTaskId: 't1', goalTitle: '  '),
      throwsA(isA<ArgumentError>()),
    );
    expect(
      () => LearningJourneyContext.fromLaunch(goalTaskId: '', goalTitle: '力学单元巩固'),
      throwsA(isA<ArgumentError>()),
    );
  });

  testWidgets('验收3 正+反：解析状态诚实——failed/unsupported 走手输替代，parsed 展示版本',
      (tester) async {
    await pumpJourney(tester, repository: _FakeJourneyRepository());

    // 图片材料：OCR 不可用 → 手输替代入口（不假装已识别）。
    expect(find.byKey(const Key('learning_parse_status_unsupported')), findsOneWidget);
    expect(find.byKey(const Key('learning_manual_input_file-img')), findsOneWidget);

    // 文本材料：已解析 → 状态徽章（无手输入口）。
    expect(find.byKey(const Key('learning_parse_status_parsed')), findsOneWidget);
    expect(find.byKey(const Key('learning_manual_input_file-abc')), findsNothing);

    // 手输保存后不声称自动解析。
    await tester.enterText(
      find.byKey(const Key('learning_manual_input_file-img')),
      '手输的题目文本：斜面倾角30度',
    );
    await tester.tap(find.byKey(const Key('learning_manual_save_file-img')));
    await tester.pump();
    expect(find.text('已保存手输文本（不声称自动识别）'), findsOneWidget);
  });

  testWidgets('验收2 正：检验题面进入后可作答，判分只呈现对/错反馈',
      (tester) async {
    final repository = _FakeJourneyRepository();
    await pumpJourney(tester, repository: repository);

    // 继续当前动作 → 证据门放行（复习证据 2 次）→ 题面出现。
    await tester.tap(find.byKey(const Key('learning_continue_action')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(repository.checkRequested, isTrue);
    await _scrollToCheckCard(tester);
    expect(find.byKey(const Key('learning_check_question')), findsOneWidget);

    // 作答提交 → 判分反馈（零答案材料）。
    await tester.enterText(
      find.byKey(const Key('learning_check_answer_field')),
      '我的独立作答',
    );
    await tester.tap(find.byKey(const Key('learning_check_submit')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(find.byKey(const Key('learning_check_verdict')), findsOneWidget);

    // 反（可失败面）：答案串不出现在任何用户可读树中。
    expect(find.textContaining('压力决定摩擦力'), findsNothing);
  });

  testWidgets('验收2 反：服务端载荷泄漏答案材料 → 红化门降级拒显（半真不呈现）',
      (tester) async {
    await pumpJourney(
      tester,
      repository: _FakeJourneyRepository(leakyCheckPayload: true),
    );

    await tester.tap(find.byKey(const Key('learning_continue_action')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    await _scrollToCheckCard(tester);

    // 降级文案出现，题面与答案串均不可读。
    expect(find.byKey(const Key('learning_check_degraded')), findsOneWidget);
    expect(find.byKey(const Key('learning_check_question')), findsNothing);
    expect(find.textContaining('压力决定摩擦力'), findsNothing);
  });
}
