// V3-FIX-354 退役守卫：UserAnalyticsEvent Isar 死集合不得复活。
//
// 背景（wt651-D04 审计 P5）：UserAnalyticsEvent（Isar 集合 uae_815 +
// 双索引 i_uae_et_106/i_uae_ts_1220）注册进 LocalDatabase schema，
// 但全 app 零写零读（analyticsEvents 仅 getter 定义、userAnalyticsEvents
// 仅 clearUserScopedData 清场引用）；真实客户端遥测由
// ClientObservabilityService（SharedPreferences 离线队列 → POST
// /client-telemetry/events[/batch]）承担，本集合是被绕开的死设计。
// 裁决=删除死集合与 schema 注册（Isar 3 移除已登记集合对存量安装安全：
// 不再打开该集合、旧数据原地孤儿化、无迁移错误）。
//
// 守卫方式：Flutter 测试工作目录为包根，直接断言源文件面——
// local_database.dart 不得再出现 UserAnalyticsEvent 任何引用，
// 模型与生成文件不得存在。修前红（引用在），修后绿。
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('V3-FIX-354: local_database 不得再注册/引用 UserAnalyticsEvent 死集合', () {
    final source = File('lib/core/offline/local_database.dart').readAsStringSync();
    expect(
      source.contains('UserAnalyticsEvent'),
      isFalse,
      reason: 'UserAnalyticsEvent 为零写零读死集合（真遥测由 '
          'ClientObservabilityService→/client-telemetry 承担），'
          '不得再进 Isar schema/清场/getter',
    );
  });

  test('V3-FIX-354: UserAnalyticsEvent 模型与生成文件已删除', () {
    expect(
      File('lib/core/analytics/models/user_analytics_event.dart').existsSync(),
      isFalse,
      reason: '死集合模型文件应已删除',
    );
    expect(
      File('lib/core/analytics/models/user_analytics_event.g.dart').existsSync(),
      isFalse,
      reason: '死集合生成文件应已删除',
    );
  });
}
