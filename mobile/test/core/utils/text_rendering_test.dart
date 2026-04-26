import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/utils/text_rendering.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

void main() {
  group('sanitizeDisplayText', () {
    test('removes replacement and invisible characters', () {
      expect(
        sanitizeDisplayText('hello\u200B\uFFFDworld\uFEFF'),
        'helloworld',
      );
    });

    test('preserves joined emoji and color presentation selectors', () {
      expect(
        sanitizeDisplayText('👨‍💻 ❤️'),
        '👨‍💻 ❤️',
      );
    });
  });

  test('sanitizeTextMap sanitizes nested widget payload strings', () {
    final payload = WidgetPayload.fromJson({
      'type': 'task_card',
      'data': {
        'title': '任务\uFFFD标题',
        'summary': '第一行\u200B\n第二行',
        'steps': [
          {'label': '步骤\uFEFF一'}
        ],
      },
    });

    expect(payload.type, 'task_card');
    expect(payload.data['title'], '任务标题');
    expect(payload.data['summary'], '第一行\n第二行');
    final steps = payload.data['steps'] as List<dynamic>;
    expect((steps.first as Map<String, dynamic>)['label'], '步骤一');
  });

  test('entity payload sanitizes compact card copy', () {
    final entity = EntityCardPayload.fromRaw({
      'entity_type': 'plan',
      'id': 'plan-1',
      'title': '学习\uFFFD计划',
      'description': '适合\u200B今晚执行',
    });

    expect(entity.title, '学习计划');
    expect(entity.summary, '适合今晚执行');
    expect(entity.share?.title, '学习计划');
    expect(entity.share?.subtitle, '适合今晚执行');
  });
}
