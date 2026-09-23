import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
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
import 'package:sparkle/features/chat/presentation/widgets/chat_run_phase_indicator.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/modeling_chat_screen.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import '../shared/i18n_test_helper.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';

class _QueuedChatRepository extends ChatRepository {
  _QueuedChatRepository() : super(Dio(), container: ProviderContainer());

  final List<_SentChatRequest> sentRequests = <_SentChatRequest>[];
  final List<Stream<ChatStreamEvent>> _streams = <Stream<ChatStreamEvent>>[];

  void enqueueController(StreamController<ChatStreamEvent> controller) {
    _streams.add(controller.stream);
  }

  void enqueueEvents(List<ChatStreamEvent> events) {
    _streams.add(_eventStream(events));
  }

  Stream<ChatStreamEvent> _eventStream(List<ChatStreamEvent> events) async* {
    for (final event in events) {
      yield event;
    }
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
    bool? useDocumentContext,
  }) {
    if (_streams.isEmpty) {
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

    return _streams.removeAt(0);
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
      : super(_NoopApiClient(), SecureTokenStorage(storage: const FlutterSecureStorage()));

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

Future<GoRouter> _pumpModelingScreen(
  WidgetTester tester, {
  required _QueuedChatRepository repository,
  required SharedPreferences sharedPrefs,
  String initialLocation = '/',
  bool useShellPlanRoute = false,
}) async {

  final router = GoRouter(
    initialLocation: initialLocation,
    routes: [
      if (useShellPlanRoute)
        StatefulShellRoute.indexedStack(
          builder: (context, state, navigationShell) => Scaffold(
            body: Column(
              children: [
                Expanded(child: navigationShell),
                const Text('BOTTOM_TAB_SENTINEL'),
              ],
            ),
          ),
          branches: [
            StatefulShellBranch(
              routes: [
                GoRoute(
                  path: '/home',
                  pageBuilder: (context, state) => const NoTransitionPage<void>(
                    child: Center(child: Text('HOME')),
                  ),
                ),
                GoRoute(
                  path: '/plans/:id',
                  pageBuilder: (context, state) => NoTransitionPage<void>(
                    child: Center(
                      child: Text('PLAN ${state.pathParameters['id']}'),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      GoRoute(
        path: '/',
        builder: (context, state) => const ModelingChatScreen(),
      ),
      GoRoute(
        path: '/onboarding/modeling-chat',
        builder: (context, state) => const ModelingChatScreen(),
      ),
      GoRoute(
        path: '/onboarding/persona',
        builder: (context, state) => const Scaffold(
          body: Center(child: Text('PERSONA')),
        ),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const Scaffold(
          body: Center(child: Text('HOME')),
        ),
      ),
      if (!useShellPlanRoute)
        GoRoute(
          path: '/plans/:id',
          builder: (context, state) => Scaffold(
            body: Center(child: Text('PLAN ${state.pathParameters['id']}')),
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
        sharedPreferencesProvider.overrideWithValue(sharedPrefs),
        chatRepositoryProvider.overrideWithValue(repository),
        authProvider.overrideWith((ref) => _FakeAuthNotifier()),
        authRepositoryProvider.overrideWithValue(
          _FakeAuthRepository(token: 'test-token'),
        ),
        onboardingCompletedProvider.overrideWith(
          _FakeOnboardingCompletedNotifier.new,
        ),
      ],
      child: MaterialApp.router(
        routerConfig: router,
        locale: const Locale('zh'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );
  await tester.pump();
  return router;
}

void main() {

  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});

  group('ModelingChatScreen', () {
    late _QueuedChatRepository repository;
    late List<StreamController<ChatStreamEvent>> controllers;
    late SharedPreferences sharedPrefs;

    setUp(() async {
      setUpI18nForTesting();
      sharedPrefs = await SharedPreferences.getInstance();
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
      repository
        ..enqueueController(onboardingController)
        ..enqueueEvents([
          const MetaEvent(
            meta: {
              'plan_id': 'plan-1',
              'plan_route': '/plans/plan-1',
            },
          ),
          DoneEvent(finishReason: 'STOP'),
        ]);

      final router = await _pumpModelingScreen(
        tester,
        repository: repository,
        sharedPrefs: sharedPrefs,
        useShellPlanRoute: true,
      );

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
              'modeling_output_json':
                  '{"cold_start_context":{"subject":"计算机网络","exam_scope":"传输层","knowledge_baseline":"完全没学过","time_available":"每天约 2 小时"}}',
            },
          ),
        )
        ..add(
          DoneEvent(finishReason: 'STOP'),
        );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(repository.sentRequests.last.message, '开始规划');

      await tester.pump();
      await tester.pump(const Duration(seconds: 1));
      await tester.pump();

      expect(
        repository.sentRequests.last.extraContext?['modeling_output'],
        isA<Map<String, dynamic>>(),
      );
      expect(router.routeInformationProvider.value.uri.path, '/plans/plan-1');
      expect(find.text('PLAN plan-1'), findsOneWidget);
      expect(find.text('BOTTOM_TAB_SENTINEL'), findsOneWidget);
      expect(find.textContaining('计划生成遇到问题'), findsNothing);
    });

    testWidgets('ignores modeling_complete metadata from non-modeling surfaces',
        (tester) async {
      final onboardingController = StreamController<ChatStreamEvent>();
      controllers.add(onboardingController);
      repository.enqueueController(onboardingController);

      await _pumpModelingScreen(tester, repository: repository, sharedPrefs: sharedPrefs);

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

      await _pumpModelingScreen(tester, repository: repository, sharedPrefs: sharedPrefs);

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

      await _pumpModelingScreen(tester, repository: repository, sharedPrefs: sharedPrefs);

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

    testWidgets(
        'V13 B-02: phase capsule shows during active run and can cancel it',
        (tester) async {
      final onboardingController = StreamController<ChatStreamEvent>();
      final nextController = StreamController<ChatStreamEvent>();
      controllers.addAll([onboardingController, nextController]);
      repository
        ..enqueueController(onboardingController)
        ..enqueueController(nextController);

      await _pumpModelingScreen(tester, repository: repository, sharedPrefs: sharedPrefs);

      // 初始 run 在跑、尚无任何帧——胶囊必须在场（长思考等待期可见），
      // 阶段位停在「思考中」而不是什么都没有。
      expect(find.byType(ChatRunPhaseIndicator), findsOneWidget);
      expect(find.text('思考中'), findsOneWidget);

      // 用户可从胶囊直接取消该 run，输入框恢复可用。
      await tester.tap(find.byTooltip('取消'));
      await tester.pump();

      expect(find.byType(ChatRunPhaseIndicator), findsNothing);
      expect(find.text('思考中'), findsNothing);

      await tester.enterText(find.byType(TextField), '继续聊');
      await tester.tap(find.byIcon(Icons.send_rounded));
      await tester.pump();

      expect(
        repository.sentRequests.last.message,
        '继续聊',
      );
    });

    testWidgets(
        'V13 B-02: mid-turn silence escalates to visible error with retry',
        (tester) async {
      final onboardingController = StreamController<ChatStreamEvent>();
      final replyController = StreamController<ChatStreamEvent>();
      final retryController = StreamController<ChatStreamEvent>();
      controllers.addAll([
        onboardingController,
        replyController,
        retryController,
      ]);
      repository
        ..enqueueController(onboardingController)
        ..enqueueController(replyController)
        ..enqueueController(retryController);

      await _pumpModelingScreen(tester, repository: repository, sharedPrefs: sharedPrefs);

      // 先让初始 run 正常结束（回一条 + Done），避免其看门狗干扰本场景。
      onboardingController
        ..add(TextEvent(content: '你好，我是 Aurora。'))
        ..add(DoneEvent(finishReason: 'STOP'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
      expect(find.byType(ChatRunPhaseIndicator), findsNothing);

      // 用户发送一条消息（重试语义必须有真实用户消息可重发）。
      await tester.enterText(find.byType(TextField), '我卡在图论了');
      await tester.tap(find.byIcon(Icons.send_rounded));
      await tester.pump();

      // Aurora 只回了半句就静默（多消息回合中段，V13 实测 50s+ 无帧）。
      replyController.add(TextEvent(content: '我先把瓶颈整理出来…'));

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('我先把瓶颈整理出来…'), findsOneWidget);

      // 75s 中段无任何帧 → 必须从「无反馈」升级为可见错误 + 重试。
      await tester.pump(const Duration(seconds: 77));
      await tester.pump(const Duration(milliseconds: 100));
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.textContaining('建模对话暂时失败'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);

      // 重试 = 重发最近一条用户消息。
      await tester.tap(find.text('重试'), warnIfMissed: false);
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(repository.sentRequests.last.message, '我卡在图论了');
    });
  });
}
