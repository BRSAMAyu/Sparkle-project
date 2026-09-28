// V4-F03 · 适配器决策 → F02 像素组件族绑定（视觉路径唯一性守卫）。
//
// 正例：
//   (a) 成功面孔决策渲染 PixelStateBadge(success) → 树中出现 PixelSuccessBadge
//       （F02 唯一庆祝载体，上升动效）；
//   (b) unknown 决策渲染「结果未知」语义（虚线问号徽章），断网态可查。
// 反例（可失败性控制组）：
//   (c) unknown / failed / memory 高亮决策的组件树中**不得**出现
//       PixelSuccessBadge（红线：非成功态绝不借成功视觉）；
//   (d) 语义标签可查询（unknown 态读屏口径 = 「结果未知」，非成功语气）。
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/experience/experience_feedback_adapter.dart';

Future<void> _pumpState(WidgetTester tester, PixelRunState state) async {
  SharedPreferences.setMockInitialValues({});
  final manager = ThemeManager();
  if (!manager.initialized) await manager.initialize();
  await manager.setPixelPreviewProfile(PixelPreviewProfile.paperDay);
  await tester.pumpWidget(
    MaterialApp(theme: AppThemes.lightTheme, home: Scaffold(body: Center(child: PixelStateBadge(state: state)))),
  );
  await tester.pump();
}

void main() {
  testWidgets('(a) 成功面孔 → PixelSuccessBadge 在树（唯一庆祝载体在位）', (tester) async {
    await _pumpState(tester, PixelRunState.success);
    expect(find.byType(PixelSuccessBadge), findsOneWidget);
    expect(find.bySemanticsLabel('已完成'), findsWidgets);
  });

  testWidgets('(b)(反c) unknown 决策 → 「结果未知」可查，树中无 PixelSuccessBadge', (tester) async {
    await _pumpState(tester, ExperienceFeedbackAdapter.resolveUnknownDisplayState());
    expect(find.bySemanticsLabel('结果未知'), findsOneWidget);
    expect(find.byType(PixelSuccessBadge), findsNothing,
        reason: '断网/未知态绝不渲染绿色成功（卡验收 3）',);
  });

  testWidgets('(反c) failed 决策 → 树中无 PixelSuccessBadge', (tester) async {
    await _pumpState(tester, PixelRunState.failed);
    expect(find.bySemanticsLabel('失败'), findsOneWidget);
    expect(find.byType(PixelSuccessBadge), findsNothing);
  });

  testWidgets('(反c) conflict 决策 → 树中无 PixelSuccessBadge', (tester) async {
    await _pumpState(tester, PixelRunState.conflict);
    expect(find.bySemanticsLabel('版本冲突'), findsOneWidget);
    expect(find.byType(PixelSuccessBadge), findsNothing);
  });
}
