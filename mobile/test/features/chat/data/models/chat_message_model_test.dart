import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';

void main() {
  test('chat message carries structured cognitive adjustments', () {
    final message = ChatMessageModel(
      conversationId: 'conv-1',
      role: MessageRole.assistant,
      content: 'ok',
      rawMetadata: const <String, dynamic>{
        'structured_cognitive_adjustments': [
          {
            'dimension': 'explanation_depth',
            'value': 'step_by_step',
          },
        ],
      },
      structuredCognitiveAdjustments: const [
        {
          'dimension': 'explanation_depth',
          'value': 'step_by_step',
        },
      ],
    );

    expect(message.structuredCognitiveAdjustments, hasLength(1));
    expect(
      message.structuredCognitiveAdjustments.first['dimension'],
      'explanation_depth',
    );
    expect(
      message.copyWith().structuredCognitiveAdjustments.first['value'],
      'step_by_step',
    );
  });
}
