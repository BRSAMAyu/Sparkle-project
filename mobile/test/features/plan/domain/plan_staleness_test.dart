import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/domain/plan_staleness.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// J-07 comeback：stale 判定边界测试。
///
/// 口径：N = kPlanComebackStaleDays = 3。整日数差（本地时区 date 截断），
/// N-1/N/N+1 天必须稳定分类；另覆盖卡面要求的 1/3/7/14 天测试时钟。
void main() {
  final now = DateTime(2026, 9, 22, 15, 30);

  TaskModel task({
    required String id,
    TaskStatus status = TaskStatus.pending,
    DateTime? updatedAt,
    String dayTag = 'day:1',
  }) {
    final at = updatedAt ?? now;
    return TaskModel(
      id: id,
      userId: 'user-1',
      planId: 'plan-1',
      title: '任务 $id',
      type: TaskType.learning,
      tags: [dayTag],
      estimatedMinutes: 30,
      difficulty: 2,
      energyCost: 1,
      status: status,
      priority: 1,
      orderIndex: 1000,
      createdAt: now.subtract(const Duration(days: 10)),
      updatedAt: at,
    );
  }

  PlanModel plan({
    DateTime? targetDate,
    DateTime? updatedAt,
    List<TaskModel> tasks = const [],
    bool isActive = true,
  }) =>
      PlanModel(
        id: 'plan-1',
        userId: 'user-1',
        name: '计算机网络冲刺',
        type: PlanType.sprint,
        dailyAvailableMinutes: 45,
        masteryLevel: 0.4,
        progress: 0.2,
        isActive: isActive,
        createdAt: now.subtract(const Duration(days: 10)),
        updatedAt: updatedAt ?? now.subtract(const Duration(days: 10)),
        targetDate: targetDate,
        tasks: tasks,
      );

  group('expired 判定（超期 N-1/N/N+1 边界，N=3）', () {
    test('超期 N-1=2 天：不判过期', () {
      final result = PlanStaleness.assess(
        plan: plan(
          targetDate: now.subtract(const Duration(days: 2)),
          tasks: [task(id: 't-1')],
        ),
        now: now,
      );
      expect(result.isExpired, isFalse);
    });

    test('超期 N=3 天：判过期，days=3', () {
      final result = PlanStaleness.assess(
        plan: plan(
          targetDate: now.subtract(const Duration(days: 3)),
          tasks: [task(id: 't-1')],
        ),
        now: now,
      );
      expect(result.kind, PlanStaleKind.expired);
      expect(result.days, 3);
      expect(result.isStale, isTrue);
    });

    test('超期 N+1=4 天：判过期，days=4', () {
      final result = PlanStaleness.assess(
        plan: plan(
          targetDate: now.subtract(const Duration(days: 4)),
          tasks: [task(id: 't-1')],
        ),
        now: now,
      );
      expect(result.kind, PlanStaleKind.expired);
      expect(result.days, 4);
    });

    test('targetDate 当天与未来：不过期', () {
      for (final offset in const [0, 1, 7]) {
        final result = PlanStaleness.assess(
          plan: plan(
            targetDate: now.add(Duration(days: offset)),
            updatedAt: now,
            tasks: [task(id: 't-1')],
          ),
          now: now,
        );
        expect(result.kind, PlanStaleKind.none, reason: 'offset=$offset');
      }
    });

    test('过期判定带 lastActivityAt 复合事实', () {
      final lastActive = now.subtract(const Duration(days: 6));
      final result = PlanStaleness.assess(
        plan: plan(
          targetDate: now.subtract(const Duration(days: 3)),
          updatedAt: lastActive,
          tasks: [task(id: 't-1', updatedAt: lastActive)],
        ),
        now: now,
      );
      expect(result.isExpired, isTrue);
      expect(result.lastActivityAt, lastActive);
    });
  });

  group('stalled 判定（断档 N-1/N 边界，活动信号=已完成任务与 plan.updatedAt 最大值）', () {
    test('活动停在 N-1=2 天前：不断档', () {
      final result = PlanStaleness.assess(
        plan: plan(
          updatedAt: now.subtract(const Duration(days: 2)),
          tasks: [task(id: 't-1')],
        ),
        now: now,
      );
      expect(result.kind, PlanStaleKind.none);
    });

    test('活动停在 N=3 天前：判断档，days=3', () {
      final away = now.subtract(const Duration(days: 3));
      final result = PlanStaleness.assess(
        plan: plan(
          updatedAt: away,
          tasks: [task(id: 't-1', updatedAt: away)],
        ),
        now: now,
      );
      expect(result.kind, PlanStaleKind.stalled);
      expect(result.days, 3);
    });

    test('已完成任务的 updatedAt 拉活：plan.updatedAt 旧但昨天完成过任务 → 不断档', () {
      final result = PlanStaleness.assess(
        plan: plan(
          updatedAt: now.subtract(const Duration(days: 9)),
          tasks: [
            task(id: 't-done', status: TaskStatus.completed),
            task(id: 't-pending'),
          ],
        ),
        now: now,
      );
      expect(result.kind, PlanStaleKind.none);
    });

    test('全部任务已完成：永不 stale（完成流接管）', () {
      final result = PlanStaleness.assess(
        plan: plan(
          targetDate: now.subtract(const Duration(days: 14)),
          updatedAt: now.subtract(const Duration(days: 14)),
          tasks: [
            task(id: 't-1', status: TaskStatus.completed),
            task(id: 't-2', status: TaskStatus.completed),
          ],
        ),
        now: now,
      );
      expect(result.kind, PlanStaleKind.none);
    });

    test('无任务的老活跃计划：按 plan.updatedAt 判断档', () {
      final result = PlanStaleness.assess(
        plan: plan(updatedAt: now.subtract(const Duration(days: 7))),
        now: now,
      );
      expect(result.kind, PlanStaleKind.stalled);
      expect(result.days, 7);
    });
  });

  group('守卫与非目标态', () {
    test('归档计划不判 stale', () {
      final result = PlanStaleness.assess(
        plan: plan(
          isActive: false,
          targetDate: now.subtract(const Duration(days: 14)),
          updatedAt: now.subtract(const Duration(days: 14)),
          tasks: [task(id: 't-1')],
        ),
        now: now,
      );
      expect(result.kind, PlanStaleKind.none);
    });

    test('thresholdDays 可覆盖（7 天口径：3 天不 stale、7 天 stale）', () {
      final threeDays = PlanStaleness.assess(
        plan: plan(
          targetDate: now.subtract(const Duration(days: 3)),
          updatedAt: now,
          tasks: [task(id: 't-1')],
        ),
        now: now,
        thresholdDays: 7,
      );
      expect(threeDays.isStale, isFalse);

      final sevenDays = PlanStaleness.assess(
        plan: plan(
          targetDate: now.subtract(const Duration(days: 7)),
          tasks: [task(id: 't-1')],
        ),
        now: now,
        thresholdDays: 7,
      );
      expect(sevenDays.kind, PlanStaleKind.expired);
      expect(sevenDays.days, 7);
    });

    test('1/3/7/14 天测试时钟：断档形态分类单调', () {
      final expectations = {
        1: PlanStaleKind.none,
        3: PlanStaleKind.stalled,
        7: PlanStaleKind.stalled,
        14: PlanStaleKind.stalled,
      };
      for (final entry in expectations.entries) {
        final away = now.subtract(Duration(days: entry.key));
        final result = PlanStaleness.assess(
          plan: plan(
            updatedAt: away,
            tasks: [task(id: 't-1', updatedAt: away)],
          ),
          now: now,
        );
        expect(result.kind, entry.value, reason: 'awayDays=${entry.key}');
      }
    });
    test('1/3/7/14 天测试时钟：超期形态分类单调', () {
      final expectations = {
        1: PlanStaleKind.none,
        3: PlanStaleKind.expired,
        7: PlanStaleKind.expired,
        14: PlanStaleKind.expired,
      };
      for (final entry in expectations.entries) {
        final result = PlanStaleness.assess(
          plan: plan(
            targetDate: now.subtract(Duration(days: entry.key)),
            // 钉住活动信号，隔离超期维度（否则默认 10 天前的
            // updatedAt 会先触发 stalled）。
            updatedAt: now,
            tasks: [task(id: 't-1')],
          ),
          now: now,
        );
        expect(result.kind, entry.value, reason: 'overdue=${entry.key}');
      }
    });

    test('fresh 单例与 assess 一致（新鲜计划返回 none）', () {
      final result = PlanStaleness.assess(
        plan: plan(
          targetDate: now.add(const Duration(days: 3)),
          updatedAt: now,
          tasks: [task(id: 't-1')],
        ),
        now: now,
      );
      expect(result.kind, PlanStaleKind.none);
      expect(result.days, 0);
      expect(result.isStale, isFalse);
    });
  });
}
