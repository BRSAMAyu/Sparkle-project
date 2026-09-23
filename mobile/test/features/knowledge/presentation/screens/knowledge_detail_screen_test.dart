import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/knowledge/presentation/providers/knowledge_detail_provider.dart';
import 'package:sparkle/features/knowledge/presentation/screens/knowledge_detail_screen.dart';

import '../../../../shared/i18n_test_helper.dart';

/// A-SPEC3 改造 #2（N15/EE-G1/G3）：knowledge_detail_screen.dart:50 直出靶——
/// `Text('$error')` 已改经唯一映射 owner（UserFacingError.from）人话化。
/// 契约：Object/toString 产物不出现于 Text。
void main() {
  setUp(setUpI18nForTesting);

  testWidgets(
      'detail error view humanizes the raw exception — no toString leak',
      (tester) async {
    final boom = Exception('node detail blew up at /api/v1/knowledge');

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          knowledgeDetailProvider('node-err').overrideWith(
            (ref) async => throw boom,
          ),
        ],
        child: testMaterialApp(
          home: const KnowledgeDetailScreen(nodeId: 'node-err'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 标题仍是人话固定文案，异常细节不入 UI。
    expect(find.text('知识节点加载失败'), findsOneWidget);
    expect(find.textContaining('node detail blew up'), findsNothing);
    expect(find.textContaining('Exception'), findsNothing);
    // 经 owner 映射：默认桶人话 + 稳定追溯码。
    expect(find.textContaining('哎呀，出错了'), findsOneWidget);
    expect(find.textContaining('[ERR-UNKNOWN]'), findsOneWidget);
  });
}
