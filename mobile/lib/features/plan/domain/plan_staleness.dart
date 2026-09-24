import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// J-07 comeback recovery：计划「断档回归」的显式 stale 判定（唯一判定点）。
///
/// 背景：用户离开数日回来，计划还在原地的两种腐烂形态——
/// - **expired（超期）**：targetDate 已过且超期 ≥ [kPlanComebackStaleDays] 天。
/// - **stalled（断档）**：计划仍活跃且有未完成任务，但最后一次活动信号
///   （已完成任务的 updatedAt 与 plan.updatedAt 取最大，兜底 createdAt）
///   距今 ≥ [kPlanComebackStaleDays] 天。
///
/// 边界语义一律按「整日数」（本地时区 date 截断后做差），N-1/N/N+1 天
/// 可稳定判定，1/3/7/14 天测试时钟见 plan_staleness_test。
///
/// 判定口径说明（诚实边界）：
/// - 只做呈现层判定，不改服务端真源（不重建 authority，J-07 Forbidden）。
/// - 引擎侧「Aurora rescope/自动重排」属跨层改造，不在本判定范围
///   （交接见 v3-output/wt303-j07-comeback/REPORT.md）。
/// - 未完成任务不做羞辱式累积：本判定只驱动「接上」呈现，不驱动任何
///   惩罚/衰减计数。
///
/// 阈值依据：回归者视角「离开数日」≈ 3 天（一个周末+周一）；常量收在
/// 本文件作为计划域 config，UI 不允许自算第二套口径。
const int kPlanComebackStaleDays = 3;

/// stale 形态。
enum PlanStaleKind {
  /// 新鲜：不触发任何回归呈现。
  none,

  /// 断档：计划未超期（或无 targetDate），但活动信号已停 ≥ N 天。
  stalled,

  /// 超期：targetDate 已过 ≥ N 天。
  expired,
}

/// 一次判定结果：形态 + 整日天数（stalled=离开天数，expired=超期天数）。
class PlanStaleness {
  const PlanStaleness._(this.kind, this.days, this.lastActivityAt);

  final PlanStaleKind kind;

  /// stalled：距最后活动信号的整日数；expired：超过 targetDate 的整日数；
  /// none：0。
  final int days;

  /// 判定依据里的最后活动信号时间（expired 时也可能有值，供呈现"断档
  /// +超期"复合事实）。
  final DateTime? lastActivityAt;

  bool get isStale => kind != PlanStaleKind.none;
  bool get isExpired => kind == PlanStaleKind.expired;
  bool get isStalled => kind == PlanStaleKind.stalled;

  /// 新鲜态单例（含 days=0），避免每次 new。
  static const PlanStaleness fresh = PlanStaleness._(
    PlanStaleKind.none,
    0,
    null,
  );

  /// 判定入口。纯函数，`now` 显式注入（可测性；调用方传 DateTime.now()）。
  ///
  /// 只对 `isActive` 且仍有未完成任务的计划判 stale：归档计划不回归、
  /// 已全部完成的计划走完成流（sprint completion 探针），都不是回归者
  /// 接住面。
  static PlanStaleness assess({
    required PlanModel plan,
    required DateTime now,
    int thresholdDays = kPlanComebackStaleDays,
  }) {
    if (!plan.isActive || thresholdDays < 1) return fresh;
    final tasks = plan.tasks ?? const <TaskModel>[];
    if (tasks.isNotEmpty &&
        tasks.every((task) => task.status == TaskStatus.completed)) {
      return fresh;
    }

    final today = _dateOf(now);
    final targetDate = plan.targetDate;
    if (targetDate != null) {
      final overdueDays =
          today.difference(_dateOf(targetDate)).inDays;
      if (overdueDays >= thresholdDays) {
        return PlanStaleness._(
          PlanStaleKind.expired,
          overdueDays,
          resolveLastActivityAt(plan),
        );
      }
    }

    final lastActivity = resolveLastActivityAt(plan);
    final awayDays = today.difference(_dateOf(lastActivity)).inDays;
    if (awayDays >= thresholdDays) {
      return PlanStaleness._(
        PlanStaleKind.stalled,
        awayDays,
        lastActivity,
      );
    }

    return fresh;
  }

  /// 最后活动信号：plan.updatedAt 与已完成任务的 updatedAt 取最大。
  /// 完成任务是客户端可得的唯一诚实"用户活动信号"（plan.updatedAt 可能
  /// 被服务端进度重算噪音提前，取最大值只放宽、不收紧——宁可少报
  /// stale，不误伤在学用户）。updatedAt 为必填字段，结果不会为 null。
  static DateTime resolveLastActivityAt(PlanModel plan) {
    var latest = plan.updatedAt;
    for (final task in plan.tasks ?? const <TaskModel>[]) {
      if (task.status != TaskStatus.completed) continue;
      final updated = task.updatedAt;
      if (updated.isAfter(latest)) latest = updated;
    }
    return latest;
  }
}

DateTime _dateOf(DateTime value) =>
    DateTime(value.year, value.month, value.day);
