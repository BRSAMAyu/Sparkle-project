import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/api_interceptor.dart';
import 'package:sparkle/core/network/http_client_pinning.dart';

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
  }
  final Ref _ref;
  late final Dio _dio;

  /// 获取 Dio 实例 (用于需要直接访问的场景)
  Dio get dio => _dio;

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      return await _dio.get(path, queryParameters: queryParameters);
    } on DioException {
      // Handle error
      rethrow;
    }
  }

  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      return await _dio.post(path, data: data, queryParameters: queryParameters);
    } on DioException {
      // Handle error
      rethrow;
    }
  }

  Future<Response<T>> put<T>(String path, {Object? data}) async {
    try {
      return await _dio.put(path, data: data);
    } on DioException {
      // Handle error
      rethrow;
    }
  }

  Future<Response<T>> patch<T>(String path, {Object? data}) async {
    try {
      return await _dio.patch(path, data: data);
    } on DioException {
      rethrow;
    }
  }

  Future<Response<T>> delete<T>(String path) async {
    try {
      return await _dio.delete(path);
    } on DioException {
      // Handle error
      rethrow;
    }
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

      await for (final chunk in stream) {
        buffer.write(utf8.decode(chunk));
        var bufferStr = buffer.toString();

        while (bufferStr.contains('\n\n')) {
          final eventEnd = bufferStr.indexOf('\n\n');
          final eventStr = bufferStr.substring(0, eventEnd);
          bufferStr = bufferStr.substring(eventEnd + 2);

          final event = _parseSSEEvent(eventStr);
          if (event != null) {
            yield event;
            if (event.event == 'done' || event.event == 'error') {
              return;
            }
          }
        }
        buffer = StringBuffer()..write(bufferStr);
      }
    } on DioException catch (e) {
      yield SSEEvent(
        event: 'error',
        data: '{"message": "${e.message ?? "网络连接中断"}"}',
      );
    } catch (e) {
      yield SSEEvent(
        event: 'error',
        data: '{"message": "发生错误: $e"}',
      );
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

      await for (final chunk in stream) {
        buffer.write(utf8.decode(chunk));
        var bufferStr = buffer.toString();

        // 解析 SSE 事件 (以双换行分隔)
        while (bufferStr.contains('\n\n')) {
          final eventEnd = bufferStr.indexOf('\n\n');
          final eventStr = bufferStr.substring(0, eventEnd);
          bufferStr = bufferStr.substring(eventEnd + 2);

          final event = _parseSSEEvent(eventStr);
          if (event != null) {
            yield event;

            // 如果是 done 或 error 事件，结束流
            if (event.event == 'done' || event.event == 'error') {
              return;
            }
          }
        }
        buffer = StringBuffer()..write(bufferStr);
      }

      // 处理剩余的 buffer
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
        data: '{"message": "${e.message ?? "网络连接中断"}"}',
      );
    } catch (e) {
      yield SSEEvent(
        event: 'error',
        data: '{"message": "发生错误: $e"}',
      );
    }
  }

  /// 解析单个 SSE 事件
  SSEEvent? _parseSSEEvent(String eventStr) {
    String? id;
    String? event;
    String? data;

    for (final line in eventStr.split('\n')) {
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
