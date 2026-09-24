import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';

/// A-3 (多端实测 android-round1 缺陷 #1) 客户端侧配合修复：
/// 建模聊天开场白失败曾被兜底成最笼统的 "Oops" 文案，真机实测拿不到任何
/// 根因线索（后端证据链又被日志轮转吃掉）。本批不改后端，先让兜底文案
/// 携带稳定的 `[ERR-*]` 类别码——下一轮实测截屏即可定位失败类别；原始
/// 异常在 debug 构建经 debugPrint 进入 logcat（release 静默）。
void main() {
  test('unclassified errors carry the ERR-UNKNOWN diagnostic code', () {
    final message =
        UserFacingError.from(Exception('mystery opening-line failure'));
    expect(message, contains('[ERR-UNKNOWN]'));
  });

  test('timeout errors carry the ERR-TIMEOUT diagnostic code', () {
    final message = UserFacingError.from(
        TimeoutException('no stream events', const Duration(seconds: 45)),);
    expect(message, contains('[ERR-TIMEOUT]'));
  });

  test('network errors carry the ERR-NET diagnostic code', () {
    final message =
        UserFacingError.from(Exception('SocketException: Connection refused'));
    expect(message, contains('[ERR-NET]'));
  });
}
