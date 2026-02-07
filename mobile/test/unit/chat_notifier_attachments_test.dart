import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/file/file.dart';

class _MockChatRepository extends Mock implements ChatRepository {
  @override
  Stream<WsConnectionState> get connectionStateStream =>
      Stream.value(WsConnectionState.connected);

  @override
  void dispose() {}
}

StoredFile _file(String id) => StoredFile(
      id: id,
      userId: 'u1',
      fileName: '$id.txt',
      mimeType: 'text/plain',
      fileSize: 10,
      bucket: 'b',
      objectKey: 'o/$id',
      status: 'ready',
      visibility: 'private',
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

void main() {
  test('ChatNotifier attachment operations are idempotent', () {
    final repo = _MockChatRepository();
    final container = ProviderContainer(
      overrides: [chatRepositoryProvider.overrideWithValue(repo)],
    );

    final notifier = container.read(chatProvider.notifier);

    final f1 = _file('f1');
    notifier.addAttachment(f1);
    notifier.addAttachment(f1); // duplicate should be ignored

    var state = container.read(chatProvider);
    expect(state.attachedFiles.length, 1);

    notifier.addAttachment(_file('f2'));
    notifier.removeAttachment('f1');

    state = container.read(chatProvider);
    expect(state.attachedFiles.length, 1);
    expect(state.attachedFiles.first.id, 'f2');

    notifier.clearAttachments();
    state = container.read(chatProvider);
    expect(state.attachedFiles, isEmpty);
  });
}
