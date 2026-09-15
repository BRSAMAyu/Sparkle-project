import 'package:sparkle/core/tracing/tracing_service.dart';
import 'package:uuid/uuid.dart';

class TracingServiceImpl implements TracingServiceBase {
  final Uuid _uuid = const Uuid();
  bool _initialized = false;

  @override
  Future<void> initialize({Uri? collectorUri}) async {
    if (_initialized) return;
    // Simplified web implementation - OpenTelemetry removed
    // In production, you would set up actual tracing here
    _initialized = true;
  }

  @override
  Span startSpan(String name) => Span(name);

  @override
  String createTraceId({String spanName = 'trace.generate'}) {
    if (!_initialized) {
      return _uuid.v4();
    }
    final span = startSpan(spanName);
    // For simplified implementation, just generate a UUID
    span.end();
    return _uuid.v4();
  }

  @override
  void recordException(Span span, Object error, StackTrace stackTrace) {
    span
      ..recordException(error, stackTrace: stackTrace)
      ..setStatus('error', error.toString());
  }
}

TracingServiceBase createTracingService() => TracingServiceImpl();
