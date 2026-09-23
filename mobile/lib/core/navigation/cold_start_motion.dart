import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';

/// N20（A-SPEC4 SPEC v1.4）· 冷启动表现层总账的令牌化分解。
///
/// 背景（IR-G1 审计 @7f855d70）：冷启动表现层三段动画无人总账——
/// 全壳 fade 320ms（app.dart `_ColdStartFade`）+ splash 四段 900ms +
/// 落地转场 400ms 串行叠加 ≈1.62s，且 splash 段被 auth 网络往返门控
/// （redirect 钉在 isLoading 上，900ms 只是下限）。
///
/// 收敛后的一段式冷启动（全部取 [AnimationSystem] 既有档位，禁字面量）：
/// - `_ColdStartFade` 删除：全壳 fade 并入 splash 首段（logo fade 即首帧渐显）；
/// - splash 四段并两段（logo 段 / 品牌文+指示器段），时长 [splash]（scene 档）；
/// - splash 不是闸门：认证判定与 splash 并行（auth stale-while-revalidate），
///   路由最早在 [brandWindow] 走完后放行落地段——认证结果既不延长也不缩短
///   品牌一瞬；
/// - 落地转场 [landing]（standard 档）与 splash 尾段交叠：放行时 splash
///   动画仍在播（品牌文/指示器在场），home 以 crossfade 盖入其上。
///
/// 表现层串行总账 = [brandWindow] + [landing] = 250 + 220 = 470ms ≤ 600ms 预算。
/// （splash 动画本体 400ms 被落地段交叠截断，不计入串行账。）
class ColdStartMotion {
  ColdStartMotion._();

  /// splash 品牌动画时长上限（scene 档；D-3 执行口径「splash ≤400ms 一轮」）。
  static const Duration splash = AnimationSystem.scene;

  /// splash 品牌窗：落地段最早放行点（normal 档）。认证判定在此窗内并行完成。
  static const Duration brandWindow = AnimationSystem.normal;

  /// splash→shell 落地转场时长（standard 档）。
  static const Duration landing = AnimationSystem.standard;

  /// 落地转场反向时长（quick 档；仅回退到 splash 时可见）。
  static const Duration landingReverse = AnimationSystem.quick;

  /// reduce-motion 下的落地转场（quick 档）。
  static const Duration landingReduceMotion = AnimationSystem.quick;

  /// reduce-motion 下的落地转场反向（micro 档）。
  static const Duration landingReverseReduceMotion = AnimationSystem.micro;

  /// 冷启动表现层串行总账（品牌窗 + 落地转场）。
  ///
  /// N20 验收数字：≤600ms。测试与守卫据此断言（改令牌先过此账）。
  static Duration get presentationLedger => brandWindow + landing;

  /// N20 预算上限（600ms）。
  static const Duration presentationBudget = Duration(milliseconds: 600);
}

/// splash 品牌窗控制器：窗未走完前为 false。
///
/// reduce-motion 用户零等待（窗即时走完，splash 动画由 splash 侧自降档）。
class ColdStartBrandWindowController extends StateNotifier<bool> {
  ColdStartBrandWindowController() : super(false) {
    final reduceMotion = WidgetsBinding
        .instance.platformDispatcher.accessibilityFeatures.disableAnimations;
    _timer = Timer(
      reduceMotion ? Duration.zero : ColdStartMotion.brandWindow,
      () {
        if (mounted) {
          state = true;
        }
      },
    );
  }

  Timer? _timer;

  @override
  void dispose() {
    _timer?.cancel();
    _timer = null;
    super.dispose();
  }
}

/// 冷启动 splash 品牌窗（N20）。
///
/// 路由 redirect 读它决定 splash 是否放行落地段；routerProvider 监听它
/// 在窗走完时触发重判。真值只翻转一次，冷启动结束后恒为 true。
final coldStartBrandWindowProvider =
    StateNotifierProvider<ColdStartBrandWindowController, bool>(
  (ref) => ColdStartBrandWindowController(),
);
