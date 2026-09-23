import 'package:flutter/services.dart';

/// N26（A-SPEC5 v1.5）输入防错基线：键盘与 formatter 成对。
///
/// `keyboardType` 只是「建议」——硬件键盘与粘贴都会穿透数字键盘；
/// `inputFormatters` 才是「拦截」。凡数字/积分/金融语义域的输入框，
/// 两者必须成对配置（存量靶：光子转账、openclaw 预算/轮询间隔、
/// 成就契约数值、小队打卡时长）。
///
/// 用法：
/// ```dart
/// TextFormField(
///   keyboardType: TextInputType.number,
///   inputFormatters: SparkleInputFormatters.digitsOnly,
/// )
/// ```
abstract final class SparkleInputFormatters {
  /// 纯数字过滤：拒绝一切非数字字符（含粘贴进来的字母/符号/空白）。
  ///
  /// 配 `TextInputType.number` 成对使用；空输入保持为空，
  /// 由 validator 决定必填语义。
  static List<TextInputFormatter> get digitsOnly =>
      <TextInputFormatter>[FilteringTextInputFormatter.digitsOnly];
}
