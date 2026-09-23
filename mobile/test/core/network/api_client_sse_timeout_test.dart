import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_interceptor.dart';
import 'package:sparkle/core/network/api_timeouts.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

/// A11Y-BATCH2（wt258 移交 · SSE 3 消费方 receiveTimeout 豁免）：
///
/// task_monitor（`/background-tasks/stream/events`）、simulation（两条
/// `/simulation/**/stream`）、enhanced_galaxy（事件流）全部经
/// ApiClient.getStream/postStream。三消费方此前未接流式豁免，静默 >30s
/// 会被全局 receiveTimeout（dio 按数据块间隔计时）掐断为
/// DioException.receiveTimeout。
///
/// 修复：getStream/postStream 请求级 `receiveTimeout:
/// ApiTimeouts.sseReceiveTimeout`。注意该常量是 **Duration.zero** 而非
/// null——dio 5.9.0 `Options.compose` 合并规则为
/// `perRequest ?? baseOptions.receiveTimeout`，显式 null 会回落全局 30s
/// （旧 null 先例实为无效豁免）；`handleResponseStream` 对
/// `receiveTimeout <= Duration.zero` 不挂接收看门，零值才是「关闭」的
/// 有效表示（N37 登记：core/network/api_timeouts.dart）。
///
/// 验收（卡面）：三方 SSE 请求带豁免（代码断言）+ 静默 >30s 不断流
/// （dio 运行时行为钉死）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late ProviderContainer container;
  late ApiClient client;
  late _RecordingAdapter adapter;

  setUp(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final prefs = await SharedPreferences.getInstance();
    adapter = _RecordingAdapter(
      ResponseBody.fromString(
        'data: {"ok": true}\n\n'
        'event: done\n'
        'data: {}\n\n',
        200,
        headers: <String, List<String>>{
          Headers.contentTypeHeader: <String>['text/event-stream'],
        },
      ),
    );
    container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
        activeGoalHeaderProvider.overrideWithValue('goal-1'),
        authInterceptorProvider.overrideWith(
          (ref) => AuthInterceptor(ref, retryDioForTesting: Dio()),
        ),
      ],
    );
    client = container.read(apiClientProvider);
    client.dio.httpClientAdapter = adapter;
  });

  tearDown(() => container.dispose());

  group('SSE 消费方 receiveTimeout 豁免（A11Y-BATCH2）', () {
    test('getStream（task_monitor / enhanced_galaxy 路径）请求级豁免生效',
        () async {
      final events = await client.getStream('/background-tasks/stream/events')
          .toList();

      expect(adapter.records, hasLength(1));
      // 合并后（post-compose）的实际生效值：零值=dio 不挂接收看门。
      expect(
        adapter.records.single.receiveTimeout,
        ApiTimeouts.sseReceiveTimeout,
      );
      expect(adapter.records.single.receiveTimeout, Duration.zero);
      // 对照：豁免不是靠回落全局 30s 达成的。
      expect(
        adapter.records.single.receiveTimeout,
        isNot(ApiTimeouts.defaultReceiveTimeout),
      );
      expect(
        adapter.records.single.headers['Accept'],
        'text/event-stream',
      );
      expect(events, isNotEmpty);
    });

    test('postStream（simulation 两条流式端点路径）请求级豁免生效', () async {
      final events = await client
          .postStream(
            '/simulation/run/stream',
            data: <String, dynamic>{'session_id': 's-1'},
          )
          .toList();

      expect(adapter.records, hasLength(1));
      expect(adapter.records.single.method, 'POST');
      expect(adapter.records.single.receiveTimeout, Duration.zero);
      expect(
        adapter.records.single.receiveTimeout,
        isNot(ApiTimeouts.defaultReceiveTimeout),
      );
      expect(events, isNotEmpty);
    });

    test('对照：普通 GET 仍带全局 30s receiveTimeout（保护语义零变化）', () async {
      adapter.enqueueResponse(
        ResponseBody.fromString(
          '{"ok": true}',
          200,
          headers: <String, List<String>>{
            Headers.contentTypeHeader: <String>['application/json'],
          },
        ),
      );
      await client.get<Map<String, dynamic>>('/chat/sessions');

      expect(adapter.records, hasLength(1));
      expect(
        adapter.records.single.receiveTimeout,
        ApiTimeouts.defaultReceiveTimeout,
      );
    });
  });

  group('dio 运行时行为（zero 值豁免 = 静默 >30s 不断流）', () {
    // testWidgets 的 fake-time zone：tester.pump(Duration) 推进 dio 的
    // 接收看门 Timer，等价真实时间流逝，无需引入 fake_async 依赖。
    testWidgets('静默 45s 后流仍存活且收满数据（修复目标场景）', (tester) async {
      final controller = StreamController<Uint8List>();
      addTearDown(() => unawaited(controller.close()));
      final dio = Dio(
        BaseOptions(
          baseUrl: 'https://api.example.test',
          // 与 ApiClient 全局同值：全局 receiveTimeout 30s。
          receiveTimeout: ApiTimeouts.defaultReceiveTimeout,
        ),
      )..httpClientAdapter = _PushAdapter(
          ResponseBody(controller.stream, 200),
        );

      final buffer = StringBuffer();
      Object? error;
      unawaited(
        dio
            .get<ResponseBody>(
          '/background-tasks/stream/events',
          options: Options(
            responseType: ResponseType.stream,
            // 与 getStream 请求级完全同形：ApiTimeouts.sseReceiveTimeout。
            receiveTimeout: ApiTimeouts.sseReceiveTimeout,
            headers: {'Accept': 'text/event-stream'},
          ),
        )
            .then((response) {
          response.data!.stream.cast<List<int>>().transform(utf8.decoder).listen(
                buffer.write,
                onError: (Object e) => error = e,
              );
        }),
      );
      await tester.pump();

      controller.add(utf8.encode('data: first\n\n'));
      await tester.pump();
      // 静默期 45s > 全局 30s：豁免生效则看门未挂，流不断。
      await tester.pump(const Duration(seconds: 45));
      controller.add(utf8.encode('data: second\n\n'));
      await tester.pump();

      expect(error, isNull);
      expect(buffer.toString(), contains('first'));
      expect(buffer.toString(), contains('second'));
    });

    testWidgets('对照：同场景下全局 30s 看门会把静默流掐断（钉住 bug 机理）',
        (tester) async {
      final controller = StreamController<Uint8List>();
      final dio = Dio(
        BaseOptions(
          baseUrl: 'https://api.example.test',
          receiveTimeout: ApiTimeouts.defaultReceiveTimeout,
        ),
      )..httpClientAdapter = _PushAdapter(
          ResponseBody(controller.stream, 200),
        );
      addTearDown(() => unawaited(controller.close()));

      Object? error;
      unawaited(
        dio
            .get<ResponseBody>(
          '/background-tasks/stream/events',
          options: Options(responseType: ResponseType.stream),
        )
            .then((response) {
          response.data!.stream.cast<List<int>>().listen(
                (_) {},
                onError: (Object e) => error = e,
              );
        }),
      );
      await tester.pump();

      controller.add(utf8.encode('data: first\n\n'));
      await tester.pump();
      await tester.pump(const Duration(seconds: 45));

      expect(error, isA<DioException>());
      expect(
        (error! as DioException).type,
        DioExceptionType.receiveTimeout,
      );
    });
  });
}

/// 记录到达 adapter 的 RequestOptions（即 compose 合并后的实际生效值），
/// 并按队列回放响应（照 api_client_p2_10_test 的 _SequenceAdapter 形制）。
class _RecordingAdapter implements HttpClientAdapter {
  _RecordingAdapter(this.defaultResponse);

  final ResponseBody defaultResponse;
  final List<ResponseBody> _extra = <ResponseBody>[];
  final List<RequestOptions> records = <RequestOptions>[];

  void enqueueResponse(ResponseBody body) => _extra.add(body);

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    records.add(options);
    if (_extra.isNotEmpty) {
      return _extra.removeAt(0);
    }
    return defaultResponse;
  }
}

/// 由测试驱动推送数据块的响应体（行为测试用）。
class _PushAdapter implements HttpClientAdapter {
  _PushAdapter(this.body);

  final ResponseBody body;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async => body;
}

class _FakeAuthRepository implements AuthRepository {
  @override
  Future<String?> getAccessToken() async => 'access-token';

  @override
  Future<String?> getToken() async => 'access-token';

  @override
  Future<String?> getRefreshToken() async => 'refresh-token';

  @override
  Future<TokenResponse> refreshToken() async =>
      TokenResponse(accessToken: 'access-token', refreshToken: 'refresh-token');

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
