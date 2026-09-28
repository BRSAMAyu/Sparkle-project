import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/presentation/widgets/assistant_lane_marker.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U07「首个有用内容与ack区分」：零模型快路应答的「即时回复」诚实标记。
///
/// 每面一正一反：
/// - 正：deterministic + 已知形态（greeting/acknowledgment/farewell）→
///   「即时回复 · 形态词」如实呈现；
/// - 反：未知形态/缺形态词 → 只显示「即时回复」本体，不臆造标签；
///   （模型面判据 isDeterministicLaneReply 由 chat_lane_semantics_test
///   钉死，此处钉呈现层不造第二判据。）
void main() {
  setUp(setUpI18nForTesting);

  Future<void> pumpMarker(WidgetTester tester, {String? kind}) async {
    await tester.pumpWidget(
      testMaterialApp(home: Scaffold(body: AssistantLaneMarker(kind: kind))),
    );
  }

  testWidgets('正：greeting 形态 → 「即时回复 · 问候」', (tester) async {
    await pumpMarker(tester, kind: 'greeting');
    expect(find.text('即时回复 · 问候'), findsOneWidget);
  });

  testWidgets('正：acknowledgment / farewell 形态如实翻译', (tester) async {
    await pumpMarker(tester, kind: 'acknowledgment');
    expect(find.text('即时回复 · 应答'), findsOneWidget);

    await pumpMarker(tester, kind: 'farewell');
    expect(find.text('即时回复 · 告别'), findsOneWidget);
  });

  testWidgets('反：缺形态词只显示「即时回复」本体（不臆造标签）', (tester) async {
    await pumpMarker(tester);
    expect(find.text('即时回复'), findsOneWidget);
    expect(find.textContaining('·'), findsNothing);
  });

  testWidgets('反：未知形态词不臆造翻译（只显示本体）', (tester) async {
    await pumpMarker(tester, kind: 'zen_mode');
    expect(find.text('即时回复'), findsOneWidget);
    expect(
      find.textContaining('zen_mode'),
      findsNothing,
      reason: '集合外语不透传成用户可见标签',
    );
    expect(find.textContaining('·'), findsNothing);
  });
}
