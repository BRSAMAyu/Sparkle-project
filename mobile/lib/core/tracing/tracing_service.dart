import 'package:flutter/foundation.dart';
import 'package:opentelemetry/api.dart' show Span;

import 'package:sparkle/core/tracing/tracing_service_impl_io.dart'
    if (dart.library.html) 'tracing_service_impl_web.dart';

abstract class TracingServiceBase {
  Future<void> initialize({Uri? collectorUri});
  Span startSpan(String name);
  String createTraceId({String spanName = 'trace.generate'});
  void recordException(Span span, Object error, StackTrace stackTrace);
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
