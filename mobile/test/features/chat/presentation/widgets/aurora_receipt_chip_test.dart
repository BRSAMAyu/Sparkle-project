import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/aurora_receipt_api_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/aurora_receipt_chip.dart';
import '../../../../shared/i18n_test_helper.dart';

class _FakeReceiptApiService implements AuroraReceiptApiService {
  int respondCalls = 0;
  String? lastAction;
  String? lastId;
  String? lastResponseType;

  @override
  Future<void> respond({
    required String type,
    required String id,
    required String action,
    String? correctedContent,
    String? reason,
    String? responseId,
  }) async {
    respondCalls += 1;
    lastAction = action;
    lastId = id;
    lastResponseType = type;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Widget _buildChip({
  required AuroraReceiptApiService service,
  required Map<String, dynamic> receipt,
  ValueChanged<String>? onActionSelected,
}) =>
    ProviderScope(
      overrides: [
        auroraReceiptApiServiceProvider.overrideWithValue(service),
      ],
      child: testMaterialApp(
        home: Scaffold(
          body: ListView(
            children: [
              AuroraReceiptChip(
                receipt: receipt,
                onActionSelected: onActionSelected,
              ),
            ],
          ),
        ),
      ),
    );

Map<String, dynamic> _receipt({
  List<Map<String, dynamic>>? memories,
  List<Map<String, dynamic>> uncertainties = const [],
  List<String> knowledgeRefs = const [],
}) =>
    {
      'receipt_type': 'memory_reference_receipt',
      'receipt_id': 'calreceipt_test',
      'response_id': 'resp-1',
      'used_count': memories?.length ?? 1,
      'summary': '这次回应参考了 1 条你的记忆。',
      'decision_reason': '这次回应参考了 1 条你的记忆。',
      'rationale_summary': '这次回应参考了 1 条你的记忆。',
      'surface': {'decision': 'surfaced', 'reason': 'uncertain_reference_within_budget'},
      'referenced_memories': memories ??
          [
            {
              'id': 'mem-0',
              'type': 'episodic',
              'content': '明天考高数',
              'time_ago': '昨天',
              'source': '你告诉我的',
              'confidence': 0.4,
              'user_confirmed': false,
              'uncertain': true,
              'actions': ['not_relevant', 'wrong', 'change_scope', 'delete'],
            },
          ],
      'uncertainties': uncertainties,
      'knowledge_refs': knowledgeRefs,
    };

void main() {
  setUp(() async {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  tearDown(tearDownI18n);

  testWidgets('calibration receipt renders four correction actions per memory',
      (tester) async {
    final service = _FakeReceiptApiService();
    await tester.pumpWidget(
      _buildChip(
        service: service,
        receipt: _receipt(),
      ),
    );
    await tester.pumpAndSettle();

    // 折叠态一行摘要可见 → 点开详情 sheet
    await tester.tap(find.byType(AuroraReceiptChip));
    await tester.pumpAndSettle();

    expect(find.text('不相关'), findsOneWidget);
    expect(find.text('不对'), findsOneWidget);
    expect(find.text('别再用它建议'), findsOneWidget);
    expect(find.text('删除'), findsOneWidget);
  });

  testWidgets('M-10 copy: receipt memory row shows qualitative tier only',
      (tester) async {
    final service = _FakeReceiptApiService();
    await tester.pumpWidget(
      _buildChip(
        service: service,
        receipt: _receipt(),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(AuroraReceiptChip));
    await tester.pumpAndSettle();

    // 置信 0.4 → 「低置信」定性词；内部百分比参数不再出现在用户面。
    expect(find.textContaining('%'), findsNothing);
    expect(find.textContaining('低置信'), findsWidgets);
  });

  testWidgets('not_relevant action posts to receipt endpoint once',
      (tester) async {
    final service = _FakeReceiptApiService();
    String? selectedPrompt;

    await tester.pumpWidget(
      _buildChip(
        service: service,
        receipt: _receipt(),
        onActionSelected: (prompt) => selectedPrompt = prompt,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(AuroraReceiptChip));
    await tester.pumpAndSettle();
    await tester.tap(find.text('不相关'));
    await tester.pumpAndSettle();

    expect(service.respondCalls, 1);
    expect(service.lastAction, 'not_relevant');
    expect(service.lastId, 'mem-0');
    expect(service.lastResponseType, 'episodic');
    expect(selectedPrompt, isNotNull);
  });

  testWidgets('delete action posts delete verb', (tester) async {
    final service = _FakeReceiptApiService();
    await tester.pumpWidget(
      _buildChip(service: service, receipt: _receipt()),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(AuroraReceiptChip));
    await tester.pumpAndSettle();
    await tester.tap(find.text('删除'));
    await tester.pumpAndSettle();

    expect(service.respondCalls, 1);
    expect(service.lastAction, 'delete');
  });

  testWidgets('uncertainty line surfaces when receipt carries uncertainties',
      (tester) async {
    final service = _FakeReceiptApiService();
    await tester.pumpWidget(
      _buildChip(
        service: service,
        receipt: _receipt(
          uncertainties: [
            {'kind': 'unverified_inference', 'label': '这条理解我还不确定，没有向你确认过', 'count': 1},
          ],
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(AuroraReceiptChip));
    await tester.pumpAndSettle();

    expect(find.text('1 条我还不确定，你可以直接纠正'), findsOneWidget);
  });

  testWidgets('knowledge refs section lists real referenced materials',
      (tester) async {
    final service = _FakeReceiptApiService();
    await tester.pumpWidget(
      _buildChip(
        service: service,
        receipt: _receipt(knowledgeRefs: ['OS.pdf']),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(AuroraReceiptChip));
    await tester.pumpAndSettle();

    expect(find.text('参考材料'), findsOneWidget);
    expect(find.text('OS.pdf'), findsOneWidget);
  });
}
