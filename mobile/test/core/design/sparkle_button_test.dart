import 'dart:ui' show SemanticsFlag;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/design_system.dart';

Widget _host(Widget child) => MaterialApp(
      home: Scaffold(
        body: Center(child: child),
      ),
    );

void _noop() {}

void main() {
  group('SparkleButton 默认行为冻结（Step 4 扩展参数不得改变既有渲染）', () {
    testWidgets('默认 primary 变体：实心背景 + label 渲染 + 按钮语义', (tester) async {
      await tester.pumpWidget(_host(const SparkleButton(
        label: '确认',
        onPressed: _noop,
      ),),);
      final material = tester.widget<Material>(
        find.descendant(
          of: find.byType(SparkleButton),
          matching: find.byWidgetPredicate((w) => w is Material),
        ),
      );
      expect(material.color, isNotNull);
      expect(material.shape, isNull, reason: '默认无 borderSide 时保持 borderRadius 路径');
      expect(find.text('确认'), findsOneWidget);
      final sem = tester.getSemantics(find.text('确认'));
      expect(sem.hasFlag(SemanticsFlag.isButton), isTrue); // ignore: deprecated_member_use
    });

    testWidgets('默认不约束最小尺寸（minWidth/minHeight 未传时无约束路径）', (tester) async {
      await tester.pumpWidget(_host(const SparkleButton(
        label: 'X',
        onPressed: _noop,
      ),),);
      final size = tester.getSize(find.descendant(
        of: find.byType(SparkleButton),
        matching: find.byWidgetPredicate((w) => w is Material),
      ).first,);
      expect(size.height, 44, reason: '默认内容高 44（扩展前后一致，行为冻结）');
    });

    testWidgets('disabled: true → 点击不触发回调', (tester) async {
      var taps = 0;
      await tester.pumpWidget(_host(SparkleButton(
        label: '不可用',
        disabled: true,
        onPressed: () => taps++,
      ),),);
      await tester.tap(find.text('不可用'), warnIfMissed: false);
      await tester.pumpAndSettle();
      expect(taps, 0, reason: '禁用态吞掉点击');
    });

    testWidgets('backgroundGradient 渲染渐变且不影响默认 Material 路径', (tester) async {
      const grad = LinearGradient(colors: [Color(0xFF111111), Color(0xFF222222)]);
      await tester.pumpWidget(_host(const SparkleButton(
        label: '渐变',
        backgroundGradient: grad,
        onPressed: _noop,
      ),),);
      final box = tester.widget<DecoratedBox>(find.byType(DecoratedBox).last);
      expect((box.decoration as BoxDecoration).gradient, grad);
    });
  });

  group('Step 4 迁移用新参数', () {
    testWidgets('minWidth/minHeight 生成命中区下限（M3 按钮 64x40 等价）', (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: Scaffold(
          body: OverflowBar(
            children: [
              SparkleButton(
                label: 'OK',
                variant: ButtonVariant.text,
                size: ButtonSize.small,
                minWidth: 64,
                minHeight: 40,
                onPressed: _noop,
              ),
            ],
          ),
        ),
      ),);
      await tester.pumpAndSettle();
      final size = tester.getSize(find.byType(SparkleButton).first);
      expect(size.height, 40, reason: '内容不足时由 minHeight 托底到 M3 视觉高（命中区等价）');
      expect(size.width, greaterThanOrEqualTo(64));
    });

    testWidgets('borderSide 渲染描边（OutlinedButton 等价）', (tester) async {
      const side = BorderSide(color: Color(0xFF123456), width: 1.5);
      await tester.pumpWidget(_host(const SparkleButton(
        label: '描边',
        variant: ButtonVariant.outline,
        borderSide: side,
        onPressed: _noop,
      ),),);
      final material = tester.widget<Material>(
        find.descendant(
          of: find.byType(SparkleButton),
          matching: find.byWidgetPredicate((w) => w is Material),
        ),
      );
      final shape = material.shape! as RoundedRectangleBorder;
      expect(shape.side.color, side.color);
      expect(shape.side.width, side.width);
    });

    testWidgets('foregroundColor 覆盖前景色（语义色文字动作等价）', (tester) async {
      await tester.pumpWidget(_host(const SparkleButton(
        label: '断开',
        variant: ButtonVariant.text,
        foregroundColor: Color(0xFFABCDEF),
        onPressed: _noop,
      ),),);
      final text = tester.widget<Text>(find.text('断开'));
      expect(text.style?.color, const Color(0xFFABCDEF), reason: '前景覆盖经 TextStyle 透传');
    });
  });

  group('SparkleButton.text 变体（承接 M3 TextButton）', () {
    testWidgets('透明背景 + 无阴影 + 可点', (tester) async {
      var taps = 0;
      await tester.pumpWidget(_host(SparkleButton(
        label: '取消',
        variant: ButtonVariant.text,
        onPressed: () => taps++,
      ),),);
      final material = tester.widget<Material>(
        find.descendant(
          of: find.byType(SparkleButton),
          matching: find.byWidgetPredicate((w) => w is Material),
        ),
      );
      expect(material.elevation, 0, reason: 'text 变体无投影');
      await tester.tap(find.text('取消'));
      await tester.pumpAndSettle();
      expect(taps, 1);
    });
  });

  group('对话动作对迁移形态（关键屏可点性）', () {
    testWidgets('actions: [text 取消, primary 确认] 双按钮语义与命中', (tester) async {
      var cancelled = false;
      var confirmed = false;
      await tester.pumpWidget(_host(AlertDialog(
        title: const Text('标题'),
        actions: [
          SparkleButton(
            label: '取消',
            variant: ButtonVariant.text,
            size: ButtonSize.small,
            minWidth: 64,
            minHeight: 40,
            onPressed: () => cancelled = true,
          ),
          SparkleButton(
            label: '确认',
            minWidth: 64,
            minHeight: 40,
            onPressed: () => confirmed = true,
          ),
        ],
      ),),);
      await tester.pumpAndSettle();

      for (final label in ['取消', '确认']) {
        final sem = tester.getSemantics(find.text(label));
        // ignore: deprecated_member_use
        expect(sem.hasFlag(SemanticsFlag.isButton), isTrue, reason: '$label 保留按钮语义');
      }
      await tester.tap(find.text('取消'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('确认'));
      await tester.pumpAndSettle();
      expect(cancelled, isTrue);
      expect(confirmed, isTrue);
      expect(
        tester.getSize(find.descendant(
          of: find.byType(SparkleButton).first,
          matching: find.byWidgetPredicate((w) => w is Material),
        ).first,).height,
        40,
        reason: 'text 变体（small）按钮与 M3 TextButton 视觉高等价',
      );
    });
  });
}
