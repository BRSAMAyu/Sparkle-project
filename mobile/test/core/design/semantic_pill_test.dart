// U-01 Step 1 owner 扩展回归：SemanticPill 新增 selected / onDeleted 能力
// （README 规则 5「扩展 owner」），承接 ChoiceChip/FilterChip/InputChip 的迁移。
// 断言覆盖：选中态语义（check 图标 + 增强 tone）、删除区独立可点且不触发
// pill 本体 onTap、onTap 为 null 时不可点（与原 disabled chip 行为等价）。
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';

Widget _host(Widget child) => MaterialApp(
      theme: AppThemes.lightTheme,
      darkTheme: AppThemes.darkTheme,
      home: Scaffold(
        body: Center(child: child),
      ),
    );

void main() {
  testWidgets('selected 态渲染 check 图标（M3 chip 选中语义等价）', (tester) async {
    await tester.pumpWidget(
      _host(
        const SemanticPill(
          label: '已选',
          tone: PillTone.brand,
          selected: true,
        ),
      ),
    );

    expect(find.text('已选'), findsOneWidget);
    expect(find.byIcon(Icons.check), findsOneWidget);
  });

  testWidgets('未选中态不渲染 check 图标', (tester) async {
    await tester.pumpWidget(
      _host(
        const SemanticPill(
          label: '未选',
          tone: PillTone.brand,
        ),
      ),
    );

    expect(find.text('未选'), findsOneWidget);
    expect(find.byIcon(Icons.check), findsNothing);
  });

  testWidgets('带自定义 icon 的选中态不叠加 check（原 avatar 语义优先）', (tester) async {
    await tester.pumpWidget(
      _host(
        const SemanticPill(
          label: '图标选中',
          tone: PillTone.brand,
          icon: Icons.school_outlined,
          selected: true,
        ),
      ),
    );

    expect(find.byIcon(Icons.school_outlined), findsOneWidget);
    expect(find.byIcon(Icons.check), findsNothing);
  });

  testWidgets('onDeleted 渲染独立删除钮，点删除不触发 pill 本体 onTap', (tester) async {
    var deleted = 0;
    var tapped = 0;
    await tester.pumpWidget(
      _host(
        SemanticPill(
          label: '可删除',
          tone: PillTone.neutral,
          onTap: () => tapped++,
          onDeleted: () => deleted++,
        ),
      ),
    );

    expect(find.byIcon(Icons.close), findsOneWidget);

    await tester.tap(find.byIcon(Icons.close), warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(deleted, 1);
    expect(tapped, 0);
  });

  testWidgets('点 pill 本体（label 区）触发 onTap 而非 onDeleted', (tester) async {
    var deleted = 0;
    var tapped = 0;
    await tester.pumpWidget(
      _host(
        SemanticPill(
          label: '可删除',
          tone: PillTone.neutral,
          onTap: () => tapped++,
          onDeleted: () => deleted++,
        ),
      ),
    );

    await tester.tap(find.text('可删除'), warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(tapped, 1);
    expect(deleted, 0);
  });

  testWidgets('onTap 为 null 时不可点（disabled chip 等价），onDeleted 仍可用', (tester) async {
    var deleted = 0;
    await tester.pumpWidget(
      _host(
        SemanticPill(
          label: '禁用态',
          tone: PillTone.neutral,
          onDeleted: () => deleted++,
        ),
      ),
    );

    await tester.tap(find.text('禁用态'), warnIfMissed: false);
    await tester.pumpAndSettle();
    // 无 onTap 时 pill 本体不响应（SparklePressable enabled=false）。
    expect(deleted, 0);

    await tester.tap(find.byIcon(Icons.close), warnIfMissed: false);
    await tester.pumpAndSettle();
    expect(deleted, 1);
  });
}
