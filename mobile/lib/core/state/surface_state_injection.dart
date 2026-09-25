import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/state/surface_state.dart';

/// U-06 状态注入——STATE_MATRIX「可注入 network/model/auth/permission/
/// conflict/partial/unknown states」的机制层。
///
/// 原则（Forbidden：不用 mock/seed 冒充真实行为）：
/// - 注入只发生在**渲染闸门**（`SurfaceStateGate`）：被注入的相位与真实
///   错误走**同一条渲染分支**（同一组件、同一文案、同一下一步动作），
///   不伪造数据、不旁路任何真实 provider——它是给表面「补齐状态分支并
///   验收」的探针，不是第二套数据真源；
/// - **release 构建零生效**：[surfaceStateOverridesProvider] 的读取点
///   全部经 [resolveInjectedSurfaceState] 的 kReleaseMode 守门，线上
///   行为与注入前逐字节一致；
/// - 注入面=[SurfaceFailureScenario.values]（14 类失败 ≥ 卡面 12 类下限），
///   与 [SurfaceStateMatrix.failurePhases] 同源。
///
/// 核心表面登记表 [coreSurfaceIds]：接了 `SurfaceStateGate` 的权威清单，
/// 矩阵覆盖率测试按此清单逐面 × 逐相位驱动（≥95% 验收口径）。
final surfaceStateOverridesProvider =
    StateProvider<Map<String, SurfaceState>>((ref) => const {});

/// debug 注入解析：有该表面的注入项且非 release 时返回，否则 null。
SurfaceState? resolveInjectedSurfaceState(
  Map<String, SurfaceState> overrides,
  String surfaceId,
) {
  if (kReleaseMode) return null;
  return overrides[surfaceId];
}

/// 核心表面登记表（权威清单，与代码接入点同步维护）。
///
/// 两级口径（与代码接入形态一一对应，覆盖率测试据此驱动）：
/// - [gateSurfaceIds]：以 `SurfaceStateGate` 为渲染闸门的面——注入探针
///   可整面驱动到任意矩阵相位；
/// - [stagedSeamIds]：以统一分阶加载/提示组件为接缝的面（骨架已自有，
///   >500ms 升格由 StagedSurfaceLoader/StagedStageHint 承担）。
const List<String> gateSurfaceIds = [
  'community.feed',
  'profile.context',
  'plan.diagnosticQuiz',
];

const List<String> stagedSeamIds = [
  'home.dashboard',
  'galaxy.nodeDetail.history',
  'shared.loadingState',
];

/// 兼容别名：核心面全集 = 闸门面 + 分阶接缝面。
const List<String> coreSurfaceIds = [...gateSurfaceIds, ...stagedSeamIds];

/// 可注入失败场景目录（network/model/auth/permission/conflict/partial/
/// unknown 全覆盖 + 矩阵其余失败族）。
enum SurfaceFailureScenario {
  networkError(SurfacePhase.errorRecoverable),
  offline(SurfacePhase.offline),
  reconnecting(SurfacePhase.reconnecting),
  authExpired(SurfacePhase.authExpired),
  permissionDenied(SurfacePhase.permissionDenied),
  modelUnavailable(SurfacePhase.modelUnavailable),
  toolUnavailable(SurfacePhase.toolUnavailable),
  conflict(SurfacePhase.conflict),
  partialData(SurfacePhase.partial),
  unknownOutcome(SurfacePhase.unknownOutcome),
  terminalError(SurfacePhase.errorTerminal),
  cancelled(SurfacePhase.cancelled),
  revoked(SurfacePhase.revoked),
  longRunningStage(SurfacePhase.longRunning);

  const SurfaceFailureScenario(this.phase);

  final SurfacePhase phase;

  SurfaceState toState() => SurfaceState(phase);
}

/// 注入助手（仅 debug 工具面调用；release 为无害空操作）。
abstract final class SurfaceStateInjector {
  /// 把某表面驱动到指定失败场景（走真实渲染分支，不造数据）。
  static Map<String, SurfaceState> inject(
    Map<String, SurfaceState> current,
    String surfaceId,
    SurfaceFailureScenario scenario,
  ) =>
      kReleaseMode
          ? current
          : {...current, surfaceId: scenario.toState()};

  /// 解除某表面注入。
  static Map<String, SurfaceState> clear(
    Map<String, SurfaceState> current,
    String surfaceId,
  ) {
    if (kReleaseMode) return current;
    return Map<String, SurfaceState>.from(current)..remove(surfaceId);
  }

  /// 全清。
  static Map<String, SurfaceState> clearAll(Map<String, SurfaceState> current) =>
      kReleaseMode ? current : const {};
}
