import 'package:flutter/foundation.dart';
import 'package:opentelemetry/api.dart' show Span;

import 'tracing_service_impl_io.dart'
    if (dart.library.html) 'tracing_service_impl_web.dart';
import 'noop_tracing_service.dart';

abstract class TracingServiceBase {
  Future<void> initialize({Uri? collectorUri});
  Span startSpan(String name);
  String createTraceId({String spanName = 'trace.generate'});
  void recordException(Span span, Object error, StackTrace stackTrace);
}

// 简化的Span类替代
class MockSpan {
  final String name;
  MockSpan(this.name);
  void end() {} // 空实现
  void recordException(Object error, {StackTrace? stackTrace}) {} // 空实现
  void setStatus(Object status, String description) {} // 空实现
  void setAttribute(String key, Object value) {} // 空实现
}

class TracingService {
  TracingService._internal();

  static TracingServiceBase _instance = createTracingService();

  static TracingServiceBase get instance => _instance;

  @visibleForTesting
  static void overrideForTest(TracingServiceBase service) {
    _instance = service;
  }
}
