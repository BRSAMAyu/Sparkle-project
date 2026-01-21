import 'package:uuid/uuid.dart';

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

  static final TracingService instance = TracingService._internal();

  final Uuid _uuid = const Uuid();

  Future<void> initialize({Uri? collectorUri}) async {
    // 移除了opentelemetry初始化
  }

  MockSpan startSpan(String name) => MockSpan(name);

  String createTraceId({String spanName = 'trace.generate'}) {
    // 直接返回UUID，不再使用opentelemetry
    return _uuid.v4();
  }

  void recordException(MockSpan span, Object error, StackTrace stackTrace) {
    // 空实现，移除了opentelemetry依赖
    span.recordException(error, stackTrace: stackTrace);
  }
}
