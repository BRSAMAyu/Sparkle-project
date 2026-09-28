import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/learning/data/learning_check_redaction.dart';

/// V4-U10 · 检验答案红化门（移动端消费侧）守卫。
///
/// 锚定 I07 `INDEPENDENT_CHECK_ANSWER_KEYS` v1 冻结集：键集漂移在此先红——
/// 服务端扩展键集时本测试必须同步跟随（contract-owner 变更信号）。
void main() {
  group('答案键封闭集（I07 v1 逐键镜像）', () {
    test('键集恰为 I07 v1 的 11 键', () {
      expect(
        kIndependentCheckAnswerKeys,
        equals(<String>{
          'answer',
          'correct_answer',
          'expected_answer',
          'reference_answer',
          'model_answer',
          'solution',
          'solution_steps',
          'answer_key',
          'explanation',
          'correct_option',
          'correct',
        }),
      );
    });

    test('标记词与服务端同词', () {
      expect(kIndependentCheckKind, 'independent_check');
      expect(kIndependentCheckFlagKey, 'independent_check');
    });
  });

  group('验收2 面：答案不泄漏到检验用户可读状态', () {
    test('正：kind 标记节点内的答案键被剥除，题面保留', () {
      final payload = <String, Object?>{
        'kind': 'independent_check',
        'question': '为什么滑动摩擦力与接触面积无关？',
        'answer': '压力决定摩擦力',
        'explanation': 'μN 不含面积项',
      };
      final (Object? clean, List<String> removed) = redactIndependentCheck(payload);
      expect(removed, containsAll(<String>['answer', 'explanation']));
      final cleanMap = clean! as Map<Object?, Object?>;
      expect(cleanMap['question'], '为什么滑动摩擦力与接触面积无关？');
      expect(cleanMap.containsKey('answer'), isFalse);
    });

    test('正：independent_check=true 旗标节点同样触发', () {
      final payload = <String, Object?>{
        'independent_check': true,
        'question': 'Q?',
        'correct_option': 'C',
      };
      final (Object? clean, List<String> removed) = redactIndependentCheck(payload);
      expect(removed, <String>['correct_option']);
      expect((clean! as Map<Object?, Object?>)['question'], 'Q?');
    });

    test('正：非标记节点的用户自有材料（correct_answer）不动', () {
      final payload = <String, Object?>{
        'error_record': <String, Object?>{
          'question_text': '错题面',
          'correct_answer': '用户自有错题答案',
        },
      };
      final (Object? clean, List<String> removed) = redactIndependentCheck(payload);
      expect(removed, isEmpty);
      final errorNode =
          (clean! as Map<Object?, Object?>)['error_record']! as Map<Object?, Object?>;
      expect(errorNode['correct_answer'], '用户自有错题答案');
    });

    test('反（可失败面）：泄漏探针在残留答案时为真', () {
      final leaked = <String, Object?>{
        'kind': 'independent_check',
        'answer': '答案X',
      };
      expect(containsIndependentCheckAnswer(leaked), isTrue);
      final cleanPayload = <String, Object?>{'question': 'Q?'};
      expect(containsIndependentCheckAnswer(cleanPayload), isFalse);
    });

    test('纯函数：输入不改写（零副作用投影）', () {
      final payload = <String, Object?>{
        'kind': 'independent_check',
        'answer': '答案X',
        'question': 'Q?',
      };
      redactIndependentCheck(payload);
      expect(payload['answer'], '答案X');
    });
  });
}
