import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

/// Dio 拦截器 - 自动添加幂等键 (v2.1)
class IdempotencyInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    // 对 POST/PUT/PATCH 请求自动添加幂等键
    if (['POST', 'PUT', 'PATCH'].contains(options.method.toUpperCase())) {
      // 检查是否已有幂等键
      if (!options.headers.containsKey('X-Idempotency-Key')) {
        options.headers['X-Idempotency-Key'] = const Uuid().v4();
      }
    }
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    // 记录是否是重放响应
    if (response.headers.value('X-Idempotency-Replayed') == 'true') {
      debugPrint(
        'Idempotency replay detected for ${response.requestOptions.path}',
      );
    }
    handler.next(response);
  }
}
