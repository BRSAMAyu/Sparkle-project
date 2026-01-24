import 'package:opentelemetry/api.dart' show Span, globalTracerProvider;
import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:uuid/uuid.dart';

class NoopTracingService implements TracingServiceBase {
  final Uuid _uuid = const Uuid();

  @override
  Future<void> initialize({Uri? collectorUri}) async {}

  @override
  Span startSpan(String name) =>
      globalTracerProvider.getTracer('sparkle-mobile').startSpan(name);

  @override
  String createTraceId({String spanName = 'trace.generate'}) => _uuid.v4();

  @override
  void recordException(Span span, Object error, StackTrace stackTrace) {}
}
