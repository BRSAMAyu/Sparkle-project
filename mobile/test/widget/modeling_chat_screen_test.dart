import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/modeling_chat_screen.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class _QueuedChatRepository extends ChatRepository {
  _QueuedChatRepository() : super(Dio(), container: ProviderContainer());

  final List<_SentChatRequest> sentRequests = <_SentChatRequest>[];
  final List<StreamController<ChatStreamEvent>> _controllers =
      <StreamController<ChatStreamEvent>>[];

  void enqueueController(StreamController<ChatStreamEvent> controller) {
    _controllers.add(controller);
  }

  @override
  Stream<ChatStreamEvent> chatStream(
    String message,
    String? conversationId, {
    String? userId,
    String? requestId,
    String? nickname,
    Map<String, dynamic>? extraContext,
    String? token,
    List<String>? fileIds,
    bool includeReferences = false,
    String? chatMode,
  }) {
    if (_controllers.isEmpty) {
      fail('No queued stream controller for message: $message');
    }

    sentRequests.add(
      _SentChatRequest(
        message: message,
        conversationId: conversationId,
        requestId: requestId,
        extraContext: extraContext,
      ),
    );

    return _controllers.removeAt(0).stream;
  }

  @override
  void dispose() {}
}

class _SentChatRequest {
  const _SentChatRequest({
    required this.message,
    required this.conversationId,
    required this.requestId,
    required this.extraContext,
  });

  final String message;
  final String? conversationId;
  final String? requestId;
  final Map<String, dynamic>? extraContext;
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository({this.token})
      : super(_NoopApiClient(), const FlutterSecureStorage());

  final String? token;

  @override
  Future<String?> getAccessToken() async => token;
}

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedRef implements Ref<Object?> {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported provider read: $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier()
      : super(_UnusedRef(), _FakeAuthRepository(token: 'test-token')) {
    state = AuthState(
      isAuthenticated: true,
      user: UserModel(
        id: 'user-1',
        username: 'aurora',
        email: 'aurora@example.com',
        flameLevel: 1,
        flameBrightness: 1,
        depthPreference: 0.5,
        curiosityPreference: 0.5,
        isActive: true,
        createdAt: DateTime(2025),
        updatedAt: DateTime(2025),
      ),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _FakeOnboardingCompletedNotifier extends OnboardingCompletedNotifier {
  _FakeOnboardingCompletedNotifier(super.ref);

  @override
  Future<void> syncForUser(UserModel? user) async {
    state = false;
  }

  @override
  Future<void> setCompleted(bool value) async {
    state = value;
  }
}

Future<void> _pumpModelingScreen(
  WidgetTester tester, {
  required _QueuedChatRepository repository,
}) async {
  SharedPreferences.setMockInitialValues(<String, Object>{});

  final router = GoRouter(
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const ModelingChatScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const Scaffold(
          body: Center(child: Text('HOME')),
        ),
      ),
      GoRoute(
        path: '/chat',
        builder: (context, state) => const Scaffold(
          body: Center(child: Text('CHAT')),
        ),
      ),
    ],
  );

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        chatRepositoryProvider.overrideWithValue(repository),
        authProvider.overrideWith((ref) => _FakeAuthNotifier()),
        authRepositoryProvider.overrideWithValue(
          _FakeAuthRepository(token: 'test-token'),
        ),
        onboardingCompletedProvider.overrideWith(
          _FakeOnboardingCompletedNotifier.new,
        ),
      ],
      child: MaterialApp.router(routerConfig: router),
    ),
  );
  await tester.pump();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ModelingChatScreen', () {
    late _QueuedChatRepository repository;
    late List<StreamController<ChatStreamEvent>> controllers;

    setUp(() {
      repository = _QueuedChatRepository();
      controllers = <StreamController<ChatStreamEvent>>[];
    });

    tearDown(() async {
      for (final controller in controllers) {
        await controller.close();
      }
    });

    testWidgets('modeling_complete metadata replaces old turn-count heuristic',
        (tester) async {
      final onboardingController = StreamController<ChatStreamEvent>();
      controllers.add(onboardingController);
      repository.enqueueController(onboardingController);

      await _pumpModelingScreen(tester, repository: repository);

      expect(repository.sentRequests.single.message, '_onboarding_start_');
      expect(
        repository.sentRequests.single.extraContext?['aurora_surface'],
        'aurora_modeling',
      );
      expect(
        repository.sentRequests.single.extraContext?['mode'],
        'onboarding_modeling',
      );

      onboardingController
        ..add(
          TextEvent(
            content: '我们先定个调。',
            metadata: const {
              'aurora_surface': 'aurora_modeling',
              'aurora_runtime_enabled': true,
              'modeling_complete': true,
            },
          ),
        )
        ..add(DoneEvent(finishReason: 'STOP'));

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('开始规划'), findsOneWidget);
      expect(find.text('我们先定个调。'), findsOneWidget);
    });

    testWidgets('ignores modeling_complete metadata from non-modeling surfaces',
        (tester) async {
      final onboardingController = StreamController<ChatStreamEvent>();
      controllers.add(onboardingController);
      repository.enqueueController(onboardingController);

      await _pumpModelingScreen(tester, repository: repository);

      onboardingController
        ..add(
          TextEvent(
            content: '这条不该触发完成。',
            metadata: const {
              'aurora_surface': 'aurora_checkpoint',
              'aurora_runtime_enabled': true,
              'modeling_complete': true,
            },
          ),
        )
        ..add(DoneEvent(finishReason: 'STOP'));

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('这条不该触发完成。'), findsOneWidget);
      expect(find.text('进入主界面'), findsNothing);
      expect(find.byType(TextField), findsOneWidget);
    });

    testWidgets('allows sending another message during CONTINUE',
        (tester) async {
      final onboardingController = StreamController<ChatStreamEvent>();
      final interjectionController = StreamController<ChatStreamEvent>();
      controllers.addAll([onboardingController, interjectionController]);
      repository
        ..enqueueController(onboardingController)
        ..enqueueController(interjectionController);

      await _pumpModelingScreen(tester, repository: repository);

      onboardingController
        ..add(TextEvent(content: '先从轻松的问题开始。'))
        ..add(
          ContinueEvent(
            finishReason: 'CONTINUE',
            sessionId: 'conv-modeling-1',
          ),
        );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 30));

      await tester.enterText(find.byType(TextField), '我插一句');
      await tester.tap(find.byIcon(Icons.send_rounded));
      await tester.pump();

      expect(
        repository.sentRequests.map((request) => request.message),
        ['_onboarding_start_', '我插一句'],
      );
      expect(repository.sentRequests.last.conversationId, 'conv-modeling-1');
    });

    testWidgets(
        'renders multi-part Aurora messages without duplicates or reordering',
        (tester) async {
      final onboardingController = StreamController<ChatStreamEvent>();
      controllers.add(onboardingController);
      repository.enqueueController(onboardingController);

      await _pumpModelingScreen(tester, repository: repository);

      onboardingController
        ..add(TextEvent(content: '第'))
        ..add(TextEvent(content: '一条'))
        ..add(ContinueEvent(finishReason: 'CONTINUE'))
        ..add(TextEvent(content: '第二'))
        ..add(TextEvent(content: '条'))
        ..add(DoneEvent(finishReason: 'STOP'));

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      final firstBubble = find.text('第一条');
      final secondBubble = find.text('第二条');

      expect(firstBubble, findsOneWidget);
      expect(secondBubble, findsOneWidget);
      expect(
        tester.getTopLeft(firstBubble).dy,
        lessThan(tester.getTopLeft(secondBubble).dy),
      );
    });
  });
}
