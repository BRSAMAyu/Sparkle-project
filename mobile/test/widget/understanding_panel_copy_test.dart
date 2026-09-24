import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/home/presentation/widgets/understanding_panel.dart';
import '../shared/i18n_test_helper.dart';

/// U-03 黑话移除：home「Sparkle 懂我」面板不得以「N 条判断 · X% 高置信」
/// 等无来源精确数字做主呈现（COPY_TONE / acceptance ①）。
class _SnapshotApiClient implements ApiClient {
  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async => Response<T>(
      requestOptions: RequestOptions(path: path),
      data: <String, dynamic>{
        'claims': [
          {
            'claim_id': 'task_duration_fit',
            'claim': '你在晚上更容易专注',
            'confidence': 0.8,
            'confidence_label': 'high',
            'evidence_summary': '基于近期的任务完成记录。',
            'scope': '学习习惯',
            'user_can_correct': true,
          },
        ],
        'recently_corrected': [],
        'memory_declarations': [],
        'envelope_style': const <String, String>{
          'current_tone': '温和直接',
          'current_verbosity': '中等简洁',
          'reason_for_style': '当前策略命中率读数稳定。',
        },
        'last_update_time': '2026-09-21T08:00:00',
        'total_claims': 1,
        'high_confidence_ratio': 1.0,
      } as T,
    );

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Dio get dio => throw UnimplementedError();
}

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('understanding panel subtitle uses plain language, no counters',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(_SnapshotApiClient()),
        ],
        child: testMaterialApp(
          home: const Scaffold(
            body: SingleChildScrollView(
              child: UnderstandingPanel(initiallyExpanded: true),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    expect(find.text('Sparkle 懂我'), findsOneWidget);
    // 用户语言说明出现。
    expect(find.textContaining('每一项都可以纠正'), findsOneWidget);
    // 黑话计数主呈现不再出现（定性层级词「高置信」允许，百分比数字不允许）。
    expect(find.textContaining('条判断'), findsNothing);
    expect(find.textContaining('%'), findsNothing);
    // 判断内容与置信层级（词而非百分比）正常渲染。
    expect(find.textContaining('你在晚上更容易专注'), findsOneWidget);
    expect(find.text('高置信'), findsOneWidget);
    expect(find.textContaining('80%'), findsNothing);
  });
}
