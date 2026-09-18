import 'package:flutter_test/flutter_test.dart';
// ignore: implementation_imports
import 'package:fluwx/src/method_channel/fluwx_platform_interface.dart';
import 'package:sparkle/core/services/social_auth_service.dart';

// N-3（web-round2）红绿测试：升级账户页红屏
// `UnimplementedError: responseEventHandler has not been implemented.`
//
// 根因链：
// 1. web 构建注册 vendored fluwx 的 `FluwxWeb` 为平台实现，但修复前它
//    **零重写** —— 与本文件底部的 `_BareFluwxPlatform` 形状完全一致；
// 2. `Fluwx()` 构造函数第一时间监听
//    `FluwxPlatform.instance.responseEventHandler` → 命中基类
//    `throw UnimplementedError('responseEventHandler has not been implemented.')`
//    （web-round2 事件留档 `UnimplementedError: respon…`）；
// 3. `SocialAuthService` 是懒初始化单例，web 旅程中首个触碰它的页面是
//    GuestUpgradeScreen.build() 的 `isWeChatAvailable`（登录页只在社交
//    按钮 onTap 里才触碰）→ build 期抛异常 → 红屏，2/2 复现。
//
// 修复分两层：
// - vendored fluwx：FluwxWeb 补齐全部平台方法（优雅降级）；
// - SocialAuthService：Fluwx 构造失败降级为 null，微信能力视为不可用。
//
// 红（修复前）：本测试构造 SocialAuthService 直接抛 UnimplementedError。
// 绿（修复后）：构造安全、能力查询降级、微信路径走 UnsupportedError。
// （FluwxWeb 本体依赖 flutter_web_plugins，VM 测试无法编译，由
// `dart analyze`（third_party_plugins/fluwx）与 web 构建覆盖。）
void main() {
  test('平台实现残缺（旧 FluwxWeb 形状）时 SocialAuthService 优雅降级，不再红屏', () async {
    // 模拟 web 构建注册零重写的 FluwxWeb 后的平台实例状态。
    FluwxPlatform.instance = _BareFluwxPlatform();

    // 升级账户页 build() 中触发的正是这条链：SocialAuthService 懒单例
    // → 字段初始化 Fluwx() → 订阅 responseEventHandler。
    // 修复前这里抛 UnimplementedError('responseEventHandler has not been
    // implemented.')；修复后降级为 null，构造安全。
    expect(SocialAuthService.new, returnsNormally);
    expect(SocialAuthService().isWeChatAvailable, isFalse);

    // 微信路径必须降级为既有的 UnsupportedError 提示，而不是平台级
    // UnimplementedError 红屏。
    await expectLater(
      SocialAuthService().signInWithWeChat(),
      throwsUnsupportedError,
    );
  });
}

/// 与修复前的 FluwxWeb 同形状：零重写的平台实现。
class _BareFluwxPlatform extends FluwxPlatform {}
