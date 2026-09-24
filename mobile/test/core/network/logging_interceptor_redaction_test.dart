// M6-14 regression: the debug LoggingInterceptor must never log sensitive
// credential fields (passwords / tokens) from request bodies.
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/network/api_interceptor.dart';

class _MemoryOutput extends LogOutput {
  final List<String> lines = <String>[];

  @override
  void output(OutputEvent event) {
    lines.addAll(event.lines);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('M6-14 LoggingInterceptor credential redaction', () {
    test('passwords never appear in request logs', () async {
      final output = _MemoryOutput();
      final interceptor = LoggingInterceptor(
        logger: Logger(
          output: output,
          printer: SimplePrinter(),
          level: Level.debug,
        ),
      );

      final options = RequestOptions(
        path: '/auth/login',
        method: 'POST',
        data: <String, dynamic>{
          'username': 'alice',
          'password': 'super-secret-password',
        },
      );

      interceptor.onRequest(options, RequestInterceptorHandler());
      await Future<void>.delayed(Duration.zero);

      final logged = output.lines.join('\n');
      expect(
        logged,
        isNot(contains('super-secret-password')),
        reason: 'Login passwords must be masked before reaching debug logs',
      );
      expect(logged, contains('alice'),
          reason: 'Non-sensitive fields stay visible for debugging',);
    });
  });
}
