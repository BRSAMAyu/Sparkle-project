import 'package:flutter/foundation.dart';
import 'package:opentelemetry/api.dart' show globalTracerProvider, registerGlobalTracerProvider;
import 'package:opentelemetry/api.dart' show Span, StatusCode;
import 'package:opentelemetry/sdk.dart'
    show
        BatchSpanProcessor,
        CollectorExporter,
        ConsoleExporter,
        SimpleSpanProcessor,
        SpanProcessor,
        TracerProviderBase;
import 'package:opentelemetry/web_sdk.dart' as web_sdk;
import 'package:uuid/uuid.dart';

class TracingService {
  TracingService._internal();

  static final TracingService instance = TracingService._internal();

  final Uuid _uuid = const Uuid();
  bool _initialized = false;

  Future<void> initialize({Uri? collectorUri}) async {
    if (_initialized) return;

    final processors = <SpanProcessor>[];
    if (collectorUri != null) {
      processors.add(
        BatchSpanProcessor(CollectorExporter(collectorUri)),
      );
    }
    if (kDebugMode) {
      processors.add(SimpleSpanProcessor(ConsoleExporter()));
    }

    final tracerProvider = kIsWeb
        ? web_sdk.WebTracerProvider(
            processors: processors,
            timeProvider: web_sdk.WebTimeProvider(),
          )
        : TracerProviderBase(processors: processors);
    registerGlobalTracerProvider(tracerProvider);
    _initialized = true;
  }

  Span startSpan(String name) => globalTracerProvider.getTracer('sparkle-mobile').startSpan(name);

  String createTraceId({String spanName = 'trace.generate'}) {
    if (!_initialized) {
      return _uuid.v4();
    }
    final span = startSpan(spanName);
    final traceId = span.spanContext.traceId;
    span.end();
    return traceId;
  }

  void recordException(Span span, Object error, StackTrace stackTrace) {
    span
      ..recordException(error, stackTrace: stackTrace)
      ..setStatus(StatusCode.error, error.toString());
  }
}
