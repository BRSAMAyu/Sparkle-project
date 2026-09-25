/// U-09 · 三端（Android / Web / macOS）共用的 canonical state 测试夹具。
///
/// 与 B-04 截图基线注册表（`scripts/devtools/visual_baseline/states.py`）
/// 同一对齐口径：同一 persona（demo_data 镜像）/goal/task 状态、同一组
/// 平台 viewport（v3/04_ux/MULTIPLATFORM.md 的采集口径），保证「headless
/// 契约测试」与「真机截图矩阵」驱动的是同一份 canonical state——三端
/// 渲染差异只在显式声明的差异点（[platformDivergences]）出现。
///
/// 分工边界（Forbidden：不重建真源）：
/// - canonical 状态的语义源仍是 U-06 `SurfacePhase`（STATE_MATRIX 1:1），
///   本夹具只提供「同一状态」的三端测试输入，零新状态语义；
/// - 视觉基线的采集/命名/manifest 仍是 B-04 visual_baseline harness，
///   本夹具不复制截图管理；
/// - goal/task 业务数据沿用 dashboard harness 的 canonical 样本
///   （task-1「Finalize dashboard narrative」/plan-1「Dashboard Polish」/
///   persona=Dashboard Test demo 账号），此处登记其身份供矩阵对照。
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/state/surface_state.dart';

/// canonical persona（B-04 demo_data 镜像；dashboard harness `_buildUser`）。
const String canonicalPersonaId = '00000000-0000-0000-0000-000000000001';
const String canonicalPersonaNickname = 'Dashboard Test';

/// canonical goal（dashboard harness plan-1，B-04 goal 库主视图样本）。
const String canonicalGoalId = 'plan-1';
const String canonicalGoalName = 'Dashboard Polish';

/// canonical task（dashboard harness task-1，B-04 任务库主视图样本）。
const String canonicalTaskId = 'task-1';
const String canonicalTaskTitle = 'Finalize dashboard narrative';

/// 三端采集 viewport（MULTIPLATFORM.md 口径，逻辑像素×DPR）。
///
/// - Android：1080×2400 @3（canonical 采集端）；
/// - Web：1280×720 桌面宽 + 360×720 mobile-like 宽（MULTIPLATFORM 要求双宽）；
/// - macOS：小窗 800×600 + 正常窗 1280×800（MULTIPLATFORM「小/正常窗口」）。
class CanonicalViewport {
  const CanonicalViewport({
    required this.platform,
    required this.logicalSize,
    required this.devicePixelRatio,
    required this.label,
  });

  final TargetPlatform platform;
  final Size logicalSize;
  final double devicePixelRatio;

  /// 人读标签（亦即 B-04 naming viewport 段的候选口径，宽x高@缩放）。
  final String label;

  @override
  String toString() => label;
}

/// 原生端 viewport（Android 手机 + macOS 小/正常窗）。
const List<CanonicalViewport> canonicalViewports = [
  CanonicalViewport(
    platform: TargetPlatform.android,
    logicalSize: Size(360, 800),
    devicePixelRatio: 3.0,
    label: 'android_phone_360x800@3.0',
  ),
  CanonicalViewport(
    platform: TargetPlatform.macOS,
    logicalSize: Size(800, 600),
    devicePixelRatio: 2.0,
    label: 'macos_small_800x600@2.0',
  ),
  CanonicalViewport(
    platform: TargetPlatform.macOS,
    logicalSize: Size(1280, 800),
    devicePixelRatio: 2.0,
    label: 'macos_normal_1280x800@2.0',
  ),
];

/// Web 双宽（1280×720 桌面 + 360×720 mobile-like）。
///
/// VM 测试无法翻转 `kIsWeb`（编译期常量），web 段以桌面目标平台 +
/// web viewport 几何近似（布局按宽度断言，kIsWeb 平台分支由「允许差异」
/// 显式声明），真机 web 采集交截图矩阵段（HUMAN_INBOX）。
const List<CanonicalViewport> webViewports = [
  CanonicalViewport(
    platform: TargetPlatform.macOS,
    logicalSize: Size(1280, 720),
    devicePixelRatio: 1.0,
    label: 'web_desktop_1280x720@1.0',
  ),
  CanonicalViewport(
    platform: TargetPlatform.macOS,
    logicalSize: Size(360, 720),
    devicePixelRatio: 1.0,
    label: 'web_mobile_like_360x720@1.0',
  ),
];

/// 契约测试遍历的 canonical 状态相位（STATE_MATRIX 代表面：
/// 等待族/失败族/非阻断降级/数据终态各取代表，全集语义由 U-06 覆盖测试钉住）。
const List<SurfacePhase> canonicalContractPhases = [
  SurfacePhase.loading,
  SurfacePhase.longRunning,
  SurfacePhase.offline,
  SurfacePhase.reconnecting,
  SurfacePhase.errorRecoverable,
  SurfacePhase.errorTerminal,
  SurfacePhase.authExpired,
  SurfacePhase.permissionDenied,
  SurfacePhase.conflict,
  SurfacePhase.awaitingUser,
  SurfacePhase.empty,
];

/// 允许差异登记（平台约定差异，显式声明 reason；契约测试不钉这些差异点）。
///
/// 每条 = 差异点 + reason。新增平台分支时必须在此登记，否则视为
/// 未声明差异（U-09 验收口径：允许差异必须有 reason）。
const List<PlatformDivergence> platformDivergences = [
  PlatformDivergence(
    point: 'design_system.dart pageTransitionsTheme.builders',
    platforms: 'iOS=Cupertino / 其余交付端=FadeForwards / fuchsia=框架默认',
    reason:
        '平台导航转场约定：iOS 边缘滑返手势语义是系统能力，'
        '不为一致而砍平台能力（保留 Cupertino）；fuchsia 非交付目标。',
  ),
  PlatformDivergence(
    point: 'sensory_feedback_service / bgm_service 触觉与音频后端',
    platforms: 'iOS/Android 启用；桌面与 web 静默降级',
    reason: '触觉反馈是移动硬件能力；桌面/web 无对应硬件约定。',
  ),
  PlatformDivergence(
    point: 'api_constants.dart baseUrl/wsBaseUrl 默认主机',
    platforms: 'android=10.0.2.2(模拟器宿主回环别名) / 其余端=localhost',
    reason:
        'Android 模拟器访问宿主机服务必须走 10.0.2.2 别名；'
        'iOS/桌面/web 与宿主同机。显式 dart-define 覆盖时三端一致。',
  ),
  PlatformDivergence(
    point: 'token_storage.dart 条件导入后端',
    platforms: 'io=Keystore/Keychain / web=localStorage(SharedPreferences)',
    reason:
        'web 无安全存储原语（web-round1 W-1/W-2 实证 secure storage '
        'web 并发写静默丢失）；竞赛口径 localStorage 可接受，'
        '生产升级路径已在 token_storage_web.dart 头登记。',
  ),
  PlatformDivergence(
    point: '键盘 IME action 按钮的视觉标签',
    platforms: 'Android/iOS=系统渲染动作按钮 / 桌面物理回车无按钮',
    reason:
        'IME 动作按钮由操作系统渲染，app 只钉 textInputAction 与 '
        'onSubmitted 行为契约（send 语义一致）。',
  ),
];

/// 允许差异登记表的结构化条目（契约测试断言逐条有 reason）。
class PlatformDivergence {
  const PlatformDivergence({
    required this.point,
    required this.platforms,
    required this.reason,
  });

  final String point;
  final String platforms;
  final String reason;
}

/// 在 [tester] 上以 canonical viewport 真实泵入 [build]。
///
/// 设置物理尺寸与 DPR，使实际布局约束与 MediaQuery 口径一致；
/// RenderFlex overflow 由框架在 pump 时直接抛错 → 契约即红。
Future<void> pumpOnViewport(
  WidgetTester tester,
  CanonicalViewport viewport,
  Widget Function() build,
) async {
  tester.view.physicalSize = Size(
    viewport.logicalSize.width * viewport.devicePixelRatio,
    viewport.logicalSize.height * viewport.devicePixelRatio,
  );
  tester.view.devicePixelRatio = viewport.devicePixelRatio;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(build());
  await tester.pumpAndSettle();
}
