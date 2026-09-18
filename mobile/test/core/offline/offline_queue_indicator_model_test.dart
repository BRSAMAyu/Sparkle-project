import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/offline/offline_providers.dart';

/// N-1/N-3 排队横幅状态机红绿测试。
///
/// N-1（Android round-2 实测）：横幅计数用
/// `max(pendingCount, activeCount)`，activeCount 把永久失败的行也计入，
/// 消息出网后「正在发送 3 条…」永不递减。
/// 绿：计数只含未投递消息（pending + sent/in-flight），失败项不计入。
///
/// N-3：气泡「发送失败·重试」与全局「正在发送…」并存的语义矛盾。
/// 绿：只剩失败项时横幅隐藏，失败态由气泡自身承载。
void main() {
  test('离线且有 pending：queued，计数 = pending 数', () {
    final model = OfflineQueueIndicatorModel.resolve(
      pendingCount: 2,
      sendingCount: 0,
      failedCount: 0,
      wsConnected: false,
    );
    expect(model.phase, OfflineQueuePhase.queued);
    expect(model.count, 2);
  });

  test('已连接且在途：sending，计数 = pending + sent（N-1 核心断言）', () {
    final model = OfflineQueueIndicatorModel.resolve(
      pendingCount: 1,
      sendingCount: 2,
      failedCount: 0,
      wsConnected: true,
    );
    expect(model.phase, OfflineQueuePhase.sending);
    expect(model.count, 3);
  });

  test('混合态：失败项不计入计数，只报未投递数（N-1 红点）', () {
    // 现场实录：2 条已出网 + 1 条永久失败残留，旧逻辑恒显「3 条」。
    final model = OfflineQueueIndicatorModel.resolve(
      pendingCount: 0,
      sendingCount: 2,
      failedCount: 1,
      wsConnected: true,
    );
    expect(model.phase, OfflineQueuePhase.sending);
    expect(model.count, 2);
  });

  test('全部出网成功：隐藏（宿主负责短暂 complete 提示）', () {
    final model = OfflineQueueIndicatorModel.resolve(
      pendingCount: 0,
      sendingCount: 0,
      failedCount: 0,
      wsConnected: true,
    );
    expect(model.phase, OfflineQueuePhase.hidden);
    expect(model.count, 0);
  });

  test('只剩失败项：横幅隐藏，不与气泡「发送失败·重试」矛盾（N-3 红点）', () {
    final model = OfflineQueueIndicatorModel.resolve(
      pendingCount: 0,
      sendingCount: 0,
      failedCount: 3,
      wsConnected: true,
    );
    expect(model.phase, OfflineQueuePhase.hidden);
  });

  test('断网但在途（sent 未达 ACK）：仍算 sending（等重连接管）', () {
    final model = OfflineQueueIndicatorModel.resolve(
      pendingCount: 0,
      sendingCount: 1,
      failedCount: 0,
      wsConnected: false,
    );
    expect(model.phase, OfflineQueuePhase.sending);
    expect(model.count, 1);
  });
}
