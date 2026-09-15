import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/providers/core_keep_alive_provider.dart';
import 'package:sparkle/core/services/session_refresh_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';

final _sessionRefreshInvokerProvider =
    Provider<void>(SessionRefreshService.refreshSessionBoundProviders);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('core chat state survives tab switch unmounts', (tester) async {
    final chatRepository = _FakeChatRepository();
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(chatRepository),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const _Shell(showChatTab: true),
      ),
    );

    final message = _message(
      conversationId: 'session-keepalive',
      content: 'still here',
    );
    final notifier = container.read(chatProvider.notifier);
    notifier.state = notifier.state.copyWith(
      conversationId: 'session-keepalive',
      messages: [message],
    );
    await tester.pump();

    expect(find.text('session-keepalive'), findsOneWidget);
    expect(find.text('still here'), findsOneWidget);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const _Shell(showChatTab: false),
      ),
    );
    expect(find.text('other-tab'), findsOneWidget);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const _Shell(showChatTab: true),
      ),
    );

    expect(find.text('session-keepalive'), findsOneWidget);
    expect(find.text('still here'), findsOneWidget);
    expect(chatRepository.disposeCount, 0);
  });

  testWidgets('session refresh clears user-scoped keepAlive providers',
      (tester) async {
    final chatRepository = _FakeChatRepository();
    final container = ProviderContainer(
      overrides: [
        chatRepositoryProvider.overrideWithValue(chatRepository),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const _Shell(showChatTab: true),
      ),
    );

    final notifier = container.read(chatProvider.notifier);
    notifier.state = notifier.state.copyWith(
      conversationId: 'logout-session',
      messages: [
        _message(
          conversationId: 'logout-session',
          content: 'clear me',
        ),
      ],
    );
    await tester.pump();
    expect(find.text('logout-session'), findsOneWidget);

    container.read(_sessionRefreshInvokerProvider);
    await tester.pump();

    expect(chatRepository.disposeCount, 1);
    expect(container.read(chatProvider).conversationId, isNull);
    expect(container.read(chatProvider).messages, isEmpty);
  });

  testWidgets('core registry marks only app-level providers as keepAlive',
      (tester) async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final keepAliveProviders = container.read(coreKeepAliveProvidersProvider);

    expect(keepAliveProviders, contains(chatProvider));
    expect(keepAliveProviders, contains(planListProvider));
    expect(keepAliveProviders.length, greaterThanOrEqualTo(6));
    expect(keepAliveProviders, isNot(contains(planDetailProvider)));
  });

  testWidgets('page-level plan details still auto-dispose', (tester) async {
    final detailProvider = planDetailProvider('plan-1');
    expect(detailProvider, isA<AutoDisposeFutureProvider<PlanModel>>());
  });
}

class _Shell extends StatelessWidget {
  const _Shell({required this.showChatTab});

  final bool showChatTab;

  @override
  Widget build(BuildContext context) => MaterialApp(
        home: showChatTab
            ? const _ChatStateProbe()
            : const Scaffold(body: Text('other-tab')),
      );
}

class _ChatStateProbe extends ConsumerWidget {
  const _ChatStateProbe();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final chatState = ref.watch(chatProvider);
    return Scaffold(
      body: Column(
        textDirection: TextDirection.ltr,
        children: [
          Text(chatState.conversationId ?? 'no-session'),
          for (final message in chatState.messages) Text(message.content),
        ],
      ),
    );
  }
}

class _FakeChatRepository extends ChatRepository {
  _FakeChatRepository() : super(Dio(), container: ProviderContainer());

  final _connectionController = StreamController<WsConnectionState>.broadcast();
  int disposeCount = 0;

  @override
  Stream<WsConnectionState> get connectionStateStream =>
      _connectionController.stream;

  @override
  WsConnectionState get connectionState => WsConnectionState.disconnected;

  @override
  void dispose() {
    disposeCount += 1;
    unawaited(_connectionController.close());
  }
}

ChatMessageModel _message({
  required String conversationId,
  required String content,
}) =>
    ChatMessageModel(
      id: 'message-$content',
      userId: 'user-1',
      conversationId: conversationId,
      role: MessageRole.assistant,
      content: content,
      createdAt: DateTime.utc(2026, 5),
    );
