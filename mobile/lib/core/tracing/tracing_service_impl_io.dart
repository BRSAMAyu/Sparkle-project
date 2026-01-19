import 'package:flutter/foundation.dart';
import 'package:opentelemetry/api.dart' show Span, StatusCode, globalTracerProvider, registerGlobalTracerProvider;
import 'package:opentelemetry/sdk.dart'
    show
        BatchSpanProcessor,
        CollectorExporter,
        ConsoleExporter,
        SimpleSpanProcessor,
        SpanProcessor,
        TracerProviderBase;
import 'package:uuid/uuid.dart';

import 'package:sparkle/core/tracing/tracing_service.dart';

class TracingServiceImpl implements TracingServiceBase {
  final Uuid _uuid = const Uuid();
  bool _initialized = false;

  @override
  Future<void> initialize({Uri? collectorUri}) async {
    if (_initialized) return;

    final processors = <SpanProcessor>[];
    if (collectorUri != null) {
      processors.add(BatchSpanProcessor(CollectorExporter(collectorUri)));
    }
    if (kDebugMode) {
      processors.add(SimpleSpanProcessor(ConsoleExporter()));
    }

    final tracerProvider = TracerProviderBase(processors: processors);
    registerGlobalTracerProvider(tracerProvider);
    _initialized = true;
  }

  @override
  Span startSpan(String name) =>
      globalTracerProvider.getTracer('sparkle-mobile').startSpan(name);

  @override
  String createTraceId({String spanName = 'trace.generate'}) {
    if (!_initialized) {
      return _uuid.v4();
    }
    final span = startSpan(spanName);
    final traceId = span.spanContext.traceId.toString();
    span.end();
    return traceId;
  }

  @override
  void recordException(Span span, Object error, StackTrace stackTrace) {
    span
      ..recordException(error, stackTrace: stackTrace)
      ..setStatus(StatusCode.error, error.toString());
  }
}

TracingServiceBase createTracingService() => TracingServiceImpl();
