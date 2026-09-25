import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/memory_reference_receipt.dart';
import '../../../../shared/i18n_test_helper.dart';

class _MemoryReceiptApiService implements MemoryApiService {
  int correctionCalls = 0;
  String? lastAction;
  String? lastId;

  @override
  Future<MemoryCorrectionResult> correctMemory({
    required String type,
    required String id,
    required String action,
    String? reason,
  }) async {
    correctionCalls += 1;
    lastAction = action;
    lastId = id;
    return MemoryCorrectionResult(
      id: id,
      evidenceRefs: const [],
      evidenceMissing: false,
      evidenceScore: 0.5,
      correctionCount: correctionCalls,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Widget _buildReceipt({
  required MemoryApiService service,
  required Map<String, dynamic> receipt,
  ValueChanged<String>? onActionSelected,
}) =>
    ProviderScope(
      overrides: [
        memoryApiServiceProvider.overrideWithValue(service),
      ],
      child: testMaterialApp(
        home: Scaffold(
          body: MemoryReferenceReceipt(
            rawMetadata: {
              'memory_reference_receipt': json.encode(receipt),
            },
            onActionSelected: onActionSelected,
          ),
        ),
      ),
    );

Map<String, dynamic> _receipt({int count = 2}) => {
      'receipt_type': 'memory_reference_receipt',
      'response_id': 'resp-1',
      'used_count': count,
      'decision_reason': 'Aurora 引用了和本轮有关的记忆。',
      'referenced_memories': List.generate(
        count,
        (index) => {
          'id': 'mem-$index',
          'type': 'episodic',
          'content': index == 0 ? '明天考高数' : '最近更适合短冲刺',
          'time_ago': index == 0 ? '昨天' : '3天前',
          'source': index == 0 ? '你告诉我的' : '从对话里推断的',
          'confidence': index == 0 ? 0.91 : 0.63,
          'user_confirmed': index == 0,
        },
      ),
    };

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('shows quiet memory receipt and detail sheet', (tester) async {
    await tester.pumpWidget(
      _buildReceipt(
        service: _MemoryReceiptApiService(),
        receipt: _receipt(),
      ),
    );

    expect(find.text('引用了 2 条相关记忆'), findsOneWidget);

    await tester.tap(find.text('引用了 2 条相关记忆'));
    await tester.pumpAndSettle();

    expect(find.text('相关记忆'), findsOneWidget);
    expect(find.text('明天考高数'), findsOneWidget);
    expect(find.text('最近更适合短冲刺'), findsOneWidget);
    expect(find.text('不对'), findsWidgets);
  });

  testWidgets('not right action lowers confidence and emits correction prompt',
      (tester) async {
    final service = _MemoryReceiptApiService();
    String? selectedPrompt;

    await tester.pumpWidget(
      _buildReceipt(
        service: service,
        receipt: _receipt(count: 1),
        onActionSelected: (prompt) => selectedPrompt = prompt,
      ),
    );

    await tester.tap(find.text('引用了 1 条相关记忆'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('不对'));
    await tester.pumpAndSettle();

    expect(service.correctionCalls, 1);
    expect(service.lastAction, 'lower_confidence');
    expect(service.lastId, 'mem-0');
    expect(selectedPrompt, contains('明天考高数'));
  });

  testWidgets('M-10 copy: receipt meta uses qualitative tier, no raw percent',
      (tester) async {
    await tester.pumpWidget(
      _buildReceipt(
        service: _MemoryReceiptApiService(),
        receipt: _receipt(),
      ),
    );

    await tester.tap(find.text('引用了 2 条相关记忆'));
    await tester.pumpAndSettle();

    // 内部置信参数（91%/63%）不再出现在用户面；与理解面同一套定性层级词。
    expect(find.textContaining('置信度 9'), findsNothing);
    expect(find.textContaining('%'), findsNothing);
    expect(find.textContaining('高置信'), findsWidgets);
    expect(find.textContaining('中置信'), findsWidgets);
  });

  testWidgets('M-10 deep link: why-this opens the corresponding understanding',
      (tester) async {
    final api = _WhyThisApiClient();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          memoryApiServiceProvider.overrideWithValue(_MemoryReceiptApiService()),
          apiClientProvider.overrideWithValue(api),
        ],
        child: testMaterialApp(
          home: Scaffold(
            body: MemoryReferenceReceipt(
              rawMetadata: {
                'memory_reference_receipt': json.encode(_receipt(count: 1)),
              },
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('引用了 1 条相关记忆'));
    await tester.pumpAndSettle();

    // 深链：引用行 → 对应理解条目的 why-this receipt（M-08 真实 API）。
    await tester.tap(find.text('为什么有这条').first);
    await tester.pumpAndSettle();

    expect(api.whyThisPosts, 1);
    expect(api.lastMemoryRef, 'memory://episodic/mem-0');
    expect(find.text('为什么 Sparkle 用了这条'), findsOneWidget);
    expect(find.text('这条记忆仍在使用中'), findsOneWidget);
  });
}

/// M-10：计数型 ApiClient，捕获 why-this 请求并返回可解析的回执 payload。
class _WhyThisApiClient implements ApiClient {
  int whyThisPosts = 0;
  String? lastMemoryRef;

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    if (path == '/memory/provenance/why-this') {
      whyThisPosts++;
      lastMemoryRef =
          (data as Map<String, dynamic>)['memory_ref']?.toString();
    }
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: <String, dynamic>{
        'memory': {
          'kind': 'episodic',
          'id': 'mem-0',
          'ref': 'memory://episodic/mem-0',
          'content': '明天考高数',
          'status_now': 'active',
          'still_in_use': true,
          'paused': false,
        },
        'why_included': [
          {
            'reason': 'matched_topic',
            'reason_known': true,
            'reason_label': '与当前对话主题相关',
            'section': 'retrieval',
            'id': 'r1',
          },
        ],
        'usage_decision': {
          'internal_only': <Map<String, dynamic>>[],
          'receipt_version': 'v1',
          'receipt_version_known': true,
        },
        'source': {
          'source_known': true,
          'source_label': '你告诉我的',
          'evidence_count': 2,
          'evidence_missing': false,
          'correction_count': 0,
          'confidence_tier_label': '高置信',
          'governance_history': <Map<String, dynamic>>[],
        },
        'correction': {
          'update': '/memory/provenance/items/episodic/mem-0/update',
          'revoke': '/memory/provenance/items/episodic/mem-0/revoke',
          'scope': '/memory/provenance/items/episodic/mem-0/scope',
        },
        'recent_uses': <Map<String, dynamic>>[],
      } as T,
    );
  }

  @override
  Future<Response<T>> get<T>(
    String path, {
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
    Object? data,
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
