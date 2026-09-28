import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';

/// V4-U03 · 回执读面 provider 测试——I06
/// `GET /experience/context-receipts/latest` 三态语义的移动端投影
/// （off/shadow 读关闭、live 无回执、live 有回执、断网、版本不支持；
/// 每面一正一反，全部可失败）。
class _StubApiClient implements ApiClient {
  _StubApiClient(this.response);

  /// GET 响应体。
  Object? response;

  /// 非空时 GET 直接抛出（模拟断网/HTTP 错误）。
  DioException? getError;

  final List<String> paths = <String>[];

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    paths.add(path);
    final error = getError;
    if (error != null) {
      throw error;
    }
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: response as T,
    );
  }

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Dio get dio => throw UnimplementedError();
}

Map<String, dynamic> _liveReceiptPayload() => {
      'mode': 'live',
      'schema_version': 'context_selection_receipt.v1',
      'receipt': {
        'schema_version': 'context_selection_receipt.v1',
        'receipt_id': 'csr_01ARZ3NDEKTSV4RRFFQ69G5FAV',
        'selection_role': 'chat_context',
        'decision_id': null,
        'input_versions': {
          'memory_epoch': 7,
          'selector_version': 'context_pack.v4-i06.v1',
        },
        'candidates': [
          {
            'ref': 'memory://episodic/aaaa',
            'status': 'selected',
            'reason_code': null,
            'note': 'DEBUG_ONLY',
          },
          {
            'ref': 'memory://goal/bbbb',
            'status': 'rejected',
            'reason_code': 'budget_exhausted',
            'note': null,
          },
        ],
        'budget': {'candidate_scan_limit': 12, 'selected_max': 6, 'clarifications_used': 0},
        'why_now': {
          'statement': '你最近在准备这场考试',
          'basis_refs': ['memory://episodic/aaaa'],
          'expires_at': null,
          'confidence_band': 'high',
        },
      },
      'source_verification': [
        {'ref': 'memory://episodic/aaaa', 'resolution': 'resolved', 'status_code': 'ok'},
      ],
      'resolved_selected_count': 1,
    };

Future<ContextReceiptState> _loadWith(_StubApiClient api) async {
  final notifier = ContextReceiptNotifier(api);
  await notifier.load();
  return notifier.state;
}

void main() {
  test('正：live + 回执 → ready，且请求路径为 I06 读面', () async {
    final api = _StubApiClient(_liveReceiptPayload());

    final state = await _loadWith(api);

    expect(api.paths.single, ApiEndpoints.experienceContextReceiptLatest);
    expect(state.phase, ContextReceiptPhase.ready);
    expect(state.view, isNotNull);
    expect(state.view!.selectedCount, 1);
    expect(state.view!.resolvedSelectedCount, 1);
    expect(state.view!.calibratableMemories().single.id, 'aaaa');
    expect(state.view!.budgetLimited, isTrue);
  });

  test('正：off/shadow → modeGated（写先行读未开，receipt=null 如实投影）', () async {
    final off = await _loadWith(
      _StubApiClient({
        'mode': 'off',
        'schema_version': 'context_selection_receipt.v1',
        'receipt': null,
      }),
    );
    final shadow = await _loadWith(
      _StubApiClient({
        'mode': 'shadow',
        'schema_version': 'context_selection_receipt.v1',
        'receipt': null,
      }),
    );

    expect(off.phase, ContextReceiptPhase.modeGated);
    expect(off.mode, 'off');
    expect(shadow.phase, ContextReceiptPhase.modeGated);
    expect(shadow.mode, 'shadow');
  });

  test('正：live + 无回执 → empty（本轮未发生选择，诚实空态）', () async {
    final state = await _loadWith(
      _StubApiClient({
        'mode': 'live',
        'schema_version': 'context_selection_receipt.v1',
        'receipt': null,
      }),
    );

    expect(state.phase, ContextReceiptPhase.empty);
    expect(state.view, isNull);
  });

  test('反：live 回执版本不支持 → unsupported（不当数据渲染，不炸）', () async {
    final payload = _liveReceiptPayload();
    (payload['receipt'] as Map<String, dynamic>)['schema_version'] =
        'context_selection_receipt.v9';

    final state = await _loadWith(_StubApiClient(payload));

    expect(state.phase, ContextReceiptPhase.unsupported);
    expect(state.view, isNull);
  });

  test('反：断网（连接错误）→ offline，绝不降级成 empty/modeGated', () async {
    final api = _StubApiClient(null)
      ..getError = DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.connectionError,
      );

    final state = await _loadWith(api);

    expect(state.phase, ContextReceiptPhase.offline);
    expect(state.view, isNull);
  });

  test('反：读面 5xx（detail 缺失）→ offline 带通用错误', () async {
    final api = _StubApiClient(null)
      ..getError = DioException(
        requestOptions: RequestOptions(path: '/x'),
        response: Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/x'),
          statusCode: 500,
          data: {'detail': 'boom'},
        ),
      );

    final state = await _loadWith(api);

    expect(state.phase, ContextReceiptPhase.offline);
    expect(state.errorMessage, 'boom');
  });
}
