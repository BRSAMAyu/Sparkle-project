import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/utils/input_formatters.dart';

/// N26（A-SPEC5 v1.5）键盘+formatter 成对：digitsOnly 过滤器必须在
/// 输入层拦截一切非数字字符——含硬件键盘与粘贴穿透。
void main() {
  group('SparkleInputFormatters.digitsOnly', () {
    TextEditingValue apply(TextEditingValue value) {
      final formatter = SparkleInputFormatters.digitsOnly.first
          as FilteringTextInputFormatter;
      return formatter.formatEditUpdate(
        TextEditingValue.empty,
        value,
      );
    }

    test('纯数字原样放行', () {
      final out = apply(const TextEditingValue(
        text: '12345',
        selection: TextSelection.collapsed(offset: 5),
      ),);
      expect(out.text, '12345');
    });

    test('拦截字母（键盘穿透）', () {
      final out = apply(const TextEditingValue(
        text: '12ab',
        selection: TextSelection.collapsed(offset: 4),
      ),);
      expect(out.text, '12');
    });

    test('拦截粘贴内容中的符号与空白', () {
      final out = apply(const TextEditingValue(
        text: ' 1,200.50 元',
        selection: TextSelection.collapsed(offset: 10),
      ),);
      expect(out.text, '120050');
    });

    test('全非数字输入被拦为空', () {
      final out = apply(const TextEditingValue(
        text: 'abc',
        selection: TextSelection.collapsed(offset: 3),
      ),);
      expect(out.text, '');
    });
  });
}
