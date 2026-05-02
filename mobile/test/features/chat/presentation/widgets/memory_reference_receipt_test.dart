import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/models/memory_models.dart';
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
}
