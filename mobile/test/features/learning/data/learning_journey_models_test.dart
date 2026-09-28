import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/learning/data/learning_journey_models.dart';

/// V4-U10 · 载荷模型守卫（解析诚实 / 来源可见 / 答案隔离）。
void main() {
  group('验收3 面：解析诚实（failed/unsupported 无文本 + 手输替代）', () {
    test('正：failed 面挂手输替代标记', () {
      final parse = JourneyMaterialParse.fromJson(<Object?, Object?>{
        'status': 'failed',
        'reason': 'ocr timeout',
        'manual_input_required': true,
      });
      expect(parse.status, JourneyParseStatus.failed);
      expect(parse.needsManualInput, isTrue);
      expect(parse.reason, 'ocr timeout');
    });

    test('正：unsupported 面（图片 OCR 不可用）挂手输替代标记', () {
      final parse = JourneyMaterialParse.fromJson(<Object?, Object?>{
        'status': 'unsupported',
        'reason': 'ocr_unavailable_for_image',
        'manual_input_required': true,
      });
      expect(parse.needsManualInput, isTrue);
    });

    test('反（可失败面）：failed 面缺手输替代标记 → 断言失败', () {
      expect(
        () => JourneyMaterialParse.fromJson(<Object?, Object?>{
          'status': 'failed',
          'manual_input_required': false,
        }),
        throwsA(isA<AssertionError>()),
      );
    });

    test('反（可失败面）：状态面携带 text 键 → 断言失败（伪造解析不可能存在）', () {
      expect(
        () => JourneyMaterialParse.fromJson(<Object?, Object?>{
          'status': 'failed',
          'manual_input_required': true,
          'text': '假装识别出了全文',
        }),
        throwsA(isA<AssertionError>()),
      );
    });

    test('未知状态按 unsupported 处理（不宣称已解析）', () {
      final parse = JourneyMaterialParse.fromJson(<Object?, Object?>{
        'status': 'magically_parsed',
        'manual_input_required': true,
      });
      expect(parse.status, JourneyParseStatus.unsupported);
      expect(parse.needsManualInput, isTrue);
    });
  });

  group('来源可见（版本从真实行读出）', () {
    test('正：id + 版本齐备', () {
      final ref = JourneySourceRef.fromJson(<Object?, Object?>{
        'source_id': 'file-123',
        'source_version': '2026-09-28T10:00:00',
        'fragment_anchor': 'para-3',
        'source_kind': 'document',
      });
      expect(ref.sourceId, 'file-123');
      expect(ref.sourceVersion, '2026-09-28T10:00:00');
      expect(ref.fragmentAnchor, 'para-3');
    });

    test('反（可失败面）：缺版本 → 断言失败（来源版本不得伪造）', () {
      expect(
        () => JourneySourceRef.fromJson(<Object?, Object?>{
          'source_id': 'file-123',
        }),
        throwsA(isA<AssertionError>()),
      );
    });
  });

  group('旅程段映射（不跳进检验空页）', () {
    test('正：attempt → practice', () {
      expect(learningSegmentFromName('attempt'), LearningSegment.practice);
      expect(learningSegmentFromName('example'), LearningSegment.practice);
    });

    test('正：independent_check → 检验段', () {
      expect(learningSegmentFromName('independent_check'), LearningSegment.independentCheck);
    });

    test('反（可失败面）：脏值回落 practice，绝不检验', () {
      expect(learningSegmentFromName('garbage'), LearningSegment.practice);
      expect(learningSegmentFromName(null), LearningSegment.practice);
    });
  });

  group('目标上下文入口守卫（验收1）', () {
    test('正：非空 id + 标题放行并裁剪空白', () {
      final context = LearningJourneyContext.fromLaunch(goalTaskId: ' t1 ', goalTitle: ' 力学单元 ');
      expect(context.goalTaskId, 't1');
      expect(context.goalTitle, '力学单元');
    });

    test('反（可失败面）：空 id / 空标题在起飞前抛 ArgumentError', () {
      expect(
        () => LearningJourneyContext.fromLaunch(goalTaskId: '', goalTitle: '力学单元'),
        throwsA(isA<ArgumentError>()),
      );
      expect(
        () => LearningJourneyContext.fromLaunch(goalTaskId: 't1', goalTitle: '  '),
        throwsA(isA<ArgumentError>()),
      );
      expect(
        () => LearningJourneyContext.fromLaunch(goalTaskId: null, goalTitle: null),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  group('检验题面红化门（LearningCheckQuestion.sanitize）', () {
    test('正：干净载荷放行题面', () {
      final question = LearningCheckQuestion.sanitize(<Object?, Object?>{
        'check_available': true,
        'question': '为什么滑动摩擦力与接触面积无关？',
      });
      expect(question.degraded, isFalse);
      expect(question.question, '为什么滑动摩擦力与接触面积无关？');
    });

    test('反（可失败面）：载荷检出答案材料 → 降级拒显（不做半真呈现）', () {
      final question = LearningCheckQuestion.sanitize(<Object?, Object?>{
        'check_available': true,
        'question': 'Q?',
        // I07 约定：检验节点自带 kind 标记（红化触发面）。
        'independent_check': <Object?, Object?>{
          'kind': 'independent_check',
          'answer': '压力决定摩擦力',
        },
      });
      expect(question.degraded, isTrue);
      expect(question.question, isEmpty);
    });
  });

  group('检验判分面（零答案材料）', () {
    test('正：干净判分面解析', () {
      final verdict = LearningCheckVerdict.fromJson(<Object?, Object?>{
        'graded': true,
        'correct': false,
        'reason': 'OK.check_graded_incorrect',
        'feedback': '回到练习段再试一次。',
      });
      expect(verdict.graded, isTrue);
      expect(verdict.correct, isFalse);
      expect(verdict.feedback, '回到练习段再试一次。');
    });

    test('反（可失败面）：判分面携带答案键 → 断言失败', () {
      expect(
        () => LearningCheckVerdict.fromJson(<Object?, Object?>{
          'graded': true,
          'correct': true,
          'reason': 'OK.check_graded_correct',
          'answer': '压力决定摩擦力',
        }),
        throwsA(isA<AssertionError>()),
      );
    });
  });

  group('旅程视图装配', () {
    test('正：materials/errors/scaffold/check 全量解析', () {
      final view = LearningJourneyView.fromJson(<Object?, Object?>{
        'schema_version': 'learning_journey.v1',
        'goal': <Object?, Object?>{'task_id': 't1', 'title': '力学单元巩固'},
        'scaffold': <Object?, Object?>{
          'stage': 'attempt',
          'hint_level': 'reduced',
          'segment': 'practice',
        },
        'materials': <Object?>[
          <Object?, Object?>{
            'file_name': 'notes.pdf',
            'mime_type': 'application/pdf',
            'source': <Object?, Object?>{'source_id': 'f1', 'source_version': 'v1'},
            'parse': <Object?, Object?>{'status': 'parsed', 'manual_input_required': false},
          },
        ],
        'errors': <Object?>[
          <Object?, Object?>{
            'id': 'e1',
            'subject_code': 'physics',
            'question_text': '斜面受力？',
            'review_count': 2,
            'source': <Object?, Object?>{'source_id': 'e1', 'source_version': 'v1', 'source_kind': 'error_record'},
          },
        ],
        'practice': <Object?, Object?>{'evidence_supported': true},
        'check': <Object?, Object?>{'question': 'Q?'},
      });
      expect(view.goalTaskId, 't1');
      expect(view.goalTitle, '力学单元巩固');
      expect(view.scaffold.segment, LearningSegment.practice);
      expect(view.materials.single.fileName, 'notes.pdf');
      expect(view.errors.single.reviewCount, 2);
      expect(view.evidenceSupported, isTrue);
      expect(view.checkQuestion, 'Q?');
    });

    test('warnings 透传（policy 降级不静默）', () {
      final view = LearningJourneyView.fromJson(
        const <Object?, Object?>{},
        warnings: <String>['policy_block_missing'],
      );
      expect(view.warnings, <String>['policy_block_missing']);
      expect(view.degraded, isFalse);
    });
  });
}
