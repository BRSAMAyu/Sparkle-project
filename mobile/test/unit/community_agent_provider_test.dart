import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';

UserBrief _user(String id, String name) => UserBrief(
      id: id,
      username: name,
      nickname: name,
    );

MessageInfo _groupMessage(String id, String content, UserBrief sender) =>
    MessageInfo(
      id: id,
      messageType: MessageType.text,
      sender: sender,
      content: content,
      createdAt: DateTime(2024),
      updatedAt: DateTime(2024),
    );

PrivateMessageInfo _privateMessage(
  String id,
  String content,
  UserBrief sender,
  UserBrief receiver,
) =>
    PrivateMessageInfo(
      id: id,
      sender: sender,
      receiver: receiver,
      messageType: MessageType.text,
      isRead: true,
      content: content,
      createdAt: DateTime(2024),
      updatedAt: DateTime(2024),
    );

void main() {
  test('buildGroupAgentPrompt filters agent messages and limits context', () {
    final alice = _user('u1', 'Alice');
    final bob = _user('u2', 'Bob');

    final messages = [
      _groupMessage('7', 'msg-7', alice),
      _groupMessage('6', 'msg-6', bob),
      _groupMessage('5', 'msg-5', alice),
      _groupMessage('4', 'msg-4', bob),
      _groupMessage('3', 'msg-3', alice),
      _groupMessage('2', 'msg-2', bob),
      MessageInfo(
        id: 'agent',
        messageType: MessageType.text,
        sender: buildCommunityAgentUser(),
        content: 'AGENT_SHOULD_NOT_APPEAR',
        contentData: {kAgentMetadataKey: true},
        createdAt: DateTime(2024),
        updatedAt: DateTime(2024),
      ),
      _groupMessage('1', 'msg-1', alice),
    ];

    final prompt = buildGroupAgentPrompt(
      input: 'Hello',
      recentMessages: messages,
      groupName: 'TestGroup',
    );

    expect(prompt.contains('TestGroup'), isTrue);
    expect(prompt.contains('Hello'), isTrue);
    expect(prompt.contains('AGENT_SHOULD_NOT_APPEAR'), isFalse);
    expect(prompt.contains('msg-1'), isFalse);
    expect(prompt.contains('msg-7'), isTrue);
  });

  test('buildPrivateAgentPrompt compresses long content', () {
    final alice = _user('u1', 'Alice');
    final bob = _user('u2', 'Bob');
    final longContent = 'a' * 200;
    final messages = [
      _privateMessage('1', longContent, alice, bob),
    ];

    final prompt = buildPrivateAgentPrompt(
      input: 'Reply',
      recentMessages: messages,
      friendName: 'Bob',
    );

    final expected = '${'a' * 160}…';
    expect(prompt.contains(expected), isTrue);
    expect(prompt.contains('Bob'), isTrue);
  });

  test('normalizeCommunityAgentOutput strips common markdown wrappers', () {
    const raw = '''
# 今日安排

1. 先复习线代
2. **晚上** 做题

`记得打卡`
''';

    final normalized = normalizeCommunityAgentOutput(raw);

    expect(normalized.contains('#'), isFalse);
    expect(normalized.contains('1.'), isFalse);
    expect(normalized.contains('**'), isFalse);
    expect(normalized, contains('今日安排'));
    expect(normalized, contains('先复习线代'));
    expect(normalized, contains('晚上 做题'));
    expect(normalized, contains('记得打卡'));
  });
}
