import 'dart:async';

import 'package:flutter/foundation.dart';

/// E-03 UI 去抖：aiStatus 的阶段级稳定窗（≥300ms）。
///
/// 问题面：引擎按真实边界下发 stage 事件（intake/context/retrieval/decision/
/// tool/waiting），映射到三段胶囊（检索/思考/生成）时若状态在类间快速回摆
/// （THINKING→SEARCHING→THINKING），段落高亮会闪烁。
///
/// 契约（卡片 work#3「同阶段重复事件不闪烁」）：
/// - 首个状态**立即**提交——首反馈不被去抖拖延（<500ms 端到端目标）；
/// - 与已提交状态**同类**且无跨类待决在途的更新立即提交（细节文案刷新
///   不构成闪段）；若跨类待决在途则视为**回摆**——取消待提交且不重发
///   已展示的段（回摆即吞）；
/// - **跨类**切换需稳定满 [window]（默认 300ms）才提交；窗口起点锚定
///   首次跨类偏离，待决类替换不重置窗口（高频 chatter 不会永不提交），
///   期满提交**最新**待决；
/// - [clear]（终帧/取消/新轮开始）立即丢弃待提交并复位——终态不拖尾。
///
/// 分类函数由调用方注入（chat 侧复用 resolveChatRunStage 的 aiStatus 划分，
/// 保持「稳定类 == 胶囊段」一一对应，不另立第二套分类真源）。
/// 提交动作以 [VoidCallback] 携带——status 与其展示文案成对原子生效。
class AiStageStabilizer {
  AiStageStabilizer({
    required this.classify,
    this.window = const Duration(milliseconds: 300),
  });

  /// 状态 → 稳定类（任意可比较值；同类不视为切换）。
  final Object Function(String? status) classify;

  /// 跨类切换的稳定窗时长。
  final Duration window;

  String? _committed;
  String? _pendingStatus;
  VoidCallback? _pendingApply;
  Timer? _timer;

  /// 最近一次已提交的状态（未提交过为 null）。
  String? get committed => _committed;

  /// 一个状态更新到达。[apply] 在该状态被提交时（同步或稳定期满）执行。
  /// 返回是否立即提交（false = 被稳定窗扣住或回摆吞掉）。
  bool offer(String status, {required VoidCallback apply}) {
    final committedClass = _committed == null ? null : classify(_committed);
    final incomingClass = classify(status);

    if (committedClass == null) {
      // 首个状态：首反馈不拖延（<500ms 端到端目标）。
      _cancelTimer();
      _committed = status;
      apply();
      return true;
    }

    if (committedClass == incomingClass) {
      final wasPending = _timer != null;
      _cancelTimer();
      if (wasPending) {
        // 回摆即吞：取消跨类待提交，但不重发同类已展示的段
        // （committed 内容不变，避免同段二次闪动）。
        return false;
      }
      // 同类细节刷新（无跨类待决在途）：立即提交。
      _committed = status;
      apply();
      return true;
    }

    if (_timer != null) {
      // 稳定窗起点锚定在首次跨类偏离：后续待决类替换不重置窗口
      // （高频 chatter 不会永不提交），期满提交最新待决。
      _pendingStatus = status;
      _pendingApply = apply;
      return false;
    }

    _pendingStatus = status;
    _pendingApply = apply;
    _timer = Timer(window, () {
      final settledApply = _pendingApply;
      final settledStatus = _pendingStatus;
      _pendingStatus = null;
      _pendingApply = null;
      _timer = null;
      if (settledStatus == null || settledApply == null) return;
      _committed = settledStatus;
      settledApply();
    });
    return false;
  }

  void _cancelTimer() {
    _timer?.cancel();
    _timer = null;
    _pendingStatus = null;
    _pendingApply = null;
  }

  /// 终态/新轮：丢弃待提交并复位（下一轮首个状态又立即生效）。
  void clear() {
    _cancelTimer();
    _committed = null;
  }

  void dispose() {
    _cancelTimer();
  }
}
