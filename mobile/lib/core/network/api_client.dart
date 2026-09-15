import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/api_interceptor.dart';
import 'package:sparkle/core/network/http_client_pinning.dart';
import 'package:sparkle/core/network/idempotency_interceptor.dart';

final apiClientProvider = Provider<ApiClient>(ApiClient.new);

class ApiClient {
  ApiClient(this._ref) {
    final options = BaseOptions(
      baseUrl: ApiEndpoints.baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      contentType: 'application/json',
    );
    _dio = Dio(options);
    configureDioForPinning(_dio, ApiConstants.apiCertSha256);
    _dio.interceptors.add(_ref.read(authInterceptorProvider));
    _dio.interceptors.add(_ref.read(retryInterceptorProvider(_dio)));
    _dio.interceptors.add(_ref.read(loggingInterceptorProvider));
    _dio.interceptors.add(IdempotencyInterceptor());
  }
  final Ref _ref;
  late final Dio _dio;

  /// 获取 Dio 实例 (用于需要直接访问的场景)
  Dio get dio => _dio;

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.get(path, queryParameters: queryParameters);
  }

  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.post(path, data: data, queryParameters: queryParameters);
  }

  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.put(path, data: data, queryParameters: queryParameters);
  }

  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.patch(path, data: data, queryParameters: queryParameters);
  }

  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.delete(path, queryParameters: queryParameters);
  }

  /// SSE 流式 GET 请求
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) async* {
    try {
      final response = await _dio.get<ResponseBody>(
        path,
        queryParameters: queryParameters,
        options: Options(
          responseType: ResponseType.stream,
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
            ...?headers,
          },
        ),
      );

      final stream = response.data?.stream;
      if (stream == null) {
        yield SSEEvent(event: 'error', data: '{"message": "No stream data"}');
        return;
      }

      var buffer = StringBuffer();

      await for (final chunk in stream.cast<List<int>>().transform(utf8.decoder)) {
        buffer.write(chunk);
        yield* _parseSSEBuffer(buffer);
      }
    } on DioException catch (e) {
      yield SSEEvent(
        event: 'error',
        data: '{"message": "${e.message ?? "Connection lost"}", "error_code": "CONNECTION_ERROR"}',
      );
    } catch (e) {
      yield SSEEvent(
        event: 'error',
        data: '{"message": "An error occurred", "error_code": "STREAM_ERROR"}',
      );
    }
  }

  /// Yield SSE events from buffer, handling both \n\n and \r\n\r\n delimiters.
  Stream<SSEEvent> _parseSSEBuffer(StringBuffer buffer) async* {
    var bufferStr = buffer.toString();
    while (true) {
      final doubleNewline = bufferStr.indexOf('\n\n');
      final doubleCRLF = bufferStr.indexOf('\r\n\r\n');
      final eventEnd = (doubleNewline >= 0 && (doubleCRLF < 0 || doubleNewline < doubleCRLF))
          ? doubleNewline
          : doubleCRLF;
      if (eventEnd < 0) {
        buffer
          ..clear()
          ..write(bufferStr);
        break;
      }
      final delimLen = eventEnd == doubleCRLF ? 4 : 2;
      final eventStr = bufferStr.substring(0, eventEnd);
      bufferStr = bufferStr.substring(eventEnd + delimLen);
      final event = _parseSSEEvent(eventStr);
      if (event != null) {
        yield event;
        if (event.event == 'done' || event.event == 'error') {
          return;
        }
      }
    }
  }

  /// SSE 流式 POST 请求
  ///
  /// 返回一个 Stream，每次 yield 一个 SSE 事件
  /// 支持容错：网络断开时不会抛出异常，而是优雅地结束流
  Stream<SSEEvent> postStream(String path, {Object? data}) async* {
    try {
      final response = await _dio.post<ResponseBody>(
        path,
        data: data,
        options: Options(
          responseType: ResponseType.stream,
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
        ),
      );

      final stream = response.data?.stream;
      if (stream == null) {
        yield SSEEvent(event: 'error', data: '{"message": "No stream data"}');
        return;
      }

      var buffer = StringBuffer();

      await for (final chunk in stream.cast<List<int>>().transform(utf8.decoder)) {
        buffer.write(chunk);
        yield* _parseSSEBuffer(buffer);
      }

      final remaining = buffer.toString();
      if (remaining.isNotEmpty) {
        final event = _parseSSEEvent(remaining);
        if (event != null) {
          yield event;
        }
      }
    } on DioException catch (e) {
      // 🚨 网络错误时不抛出异常，返回错误事件
      yield SSEEvent(
        event: 'error',
        data: '{"message": "${e.message ?? "Connection lost"}", "error_code": "CONNECTION_ERROR"}',
      );
    } catch (e) {
      yield SSEEvent(
        event: 'error',
        data: '{"message": "An error occurred", "error_code": "STREAM_ERROR"}',
      );
    }
  }

  /// 解析单个 SSE 事件
  SSEEvent? _parseSSEEvent(String eventStr) {
    String? id;
    String? event;
    String? data;

    for (final line in eventStr.split(RegExp(r'\r?\n'))) {
      if (line.startsWith('id:')) {
        id = line.substring(3).trim();
      } else if (line.startsWith('event:')) {
        event = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        data = line.substring(5).trim();
      }
    }

    if (data != null) {
      return SSEEvent(id: id, event: event ?? 'message', data: data);
    }
    return null;
  }
}

/// SSE 事件数据类
class SSEEvent {
  SSEEvent({required this.event, required this.data, this.id});
  final String? id;
  final String event;
  final String data;

  /// 解析 data 为 JSON Map
  Map<String, dynamic>? get jsonData {
    try {
      return json.decode(data) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  @override
  String toString() => 'SSEEvent(event: $event, data: $data)';
}
