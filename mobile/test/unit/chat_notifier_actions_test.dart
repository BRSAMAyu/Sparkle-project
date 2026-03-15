import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';

class _MockChatRepository extends Mock implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream =>
      Stream.value(WsConnectionState.connected);

  @override
  void dispose() {}
}

void main() {
  late _MockChatRepository repo;
  late ProviderContainer container;
  late ChatNotifier notifier;

  setUp(() {
    repo = _MockChatRepository();
    container = ProviderContainer(
      overrides: [chatRepositoryProvider.overrideWithValue(repo)],
    );
    notifier = container.read(chatProvider.notifier);
    clearInteractions(repo);
  });

  tearDown(() {
    container.dispose();
  });

  test('confirmAction sends confirm feedback for tool result action', () {
    final action = WidgetPayload(
      type: 'task_card',
      data: {'tool_result_id': 'tool-123'},
    );

    notifier.confirmAction(action);

    verify(repo.sendActionFeedback(
      action: 'confirm',
      toolResultId: 'tool-123',
      widgetType: 'task_card',
    ),).called(1);
  });

  test('dismissAction sends intervention reject feedback for intervention', () {
    final action = WidgetPayload(
      type: 'intervention',
      data: {'intervention_id': 'int-789'},
    );

    notifier.dismissAction(action);

    verify(repo.sendInterventionFeedback(
      requestId: 'int-789',
      feedbackType: 'reject',
      extraData: {'widget_type': 'intervention'},
    ),).called(1);
    verifyNoMoreInteractions(repo);
  });

  test('sendResponseFeedback skips when responseId is empty', () {
    final message = ChatMessageModel(
      id: 'm-1',
      userId: 'u-1',
      conversationId: 'c-1',
      role: MessageRole.assistant,
      content: 'hello',
      createdAt: DateTime.now(),
    );

    notifier.sendResponseFeedback(message, 'thumbs_up');

    verifyZeroInteractions(repo);
  });
}
