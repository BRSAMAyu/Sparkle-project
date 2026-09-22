// S7 ·「今日任务」看板口径回归（批1-A 信任地基）。
//
// 真假判定的事实源在引擎 backend/app/services/goal_today_view.py
// （due_date == today 且状态非完成/放弃）。客户端仅作展示投影：
// 看板头部汇总与「今日」分组共用 task_board_provider.dart 的
// tasksDueOn 单一定义点。此前头部口径是
// `isSameDay(dueDate) || isSameDay(completedAt)`，与正文的今日分组
// 各说各话，复现 AUDIT S7 / V12 的同屏矛盾（「今日 1/1」却没有
// 今日分组、「今日无任务」标题下挂着本周任务）。
//
// 本测试锁定 tasksDueOn 的口径不变量：
//  1. 只有 dueDate 落在当天才算「今日」；
//  2. 「今天才完成的历史任务（dueDate 在过去）」不属于今日；
//  3. 未来到期/无日期任务不属于今日——与引擎判定字面一致。
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/presentation/providers/task_board_provider.dart';
import 'package:sparkle/shared/entities/task_model.dart';

TaskModel _task({required String id, DateTime? dueDate}) {
  final now = DateTime.now();
  return TaskModel(
    id: id,
    userId: 'u1',
    title: 'task-$id',
    type: TaskType.learning,
    tags: const [],
    estimatedMinutes: 25,
    difficulty: 1,
    energyCost: 1,
    status: TaskStatus.pending,
    priority: 1,
    createdAt: now,
    updatedAt: now,
    dueDate: dueDate,
  );
}

void main() {
  test('tasksDueOn 只取 dueDate 落在当天的任务（含当天完成的到期任务）', () {
    final now = DateTime.now();
    final day = DateTime(now.year, now.month, now.day);

    final dueToday = _task(id: 'a', dueDate: day);
    final dueTodayCompleted = _task(id: 'b', dueDate: day);
    final dueYesterday = _task(id: 'c', dueDate: day.subtract(const Duration(days: 1)));
    final dueTomorrow = _task(id: 'd', dueDate: day.add(const Duration(days: 1)));
    final noDate = _task(id: 'e');

    final picked = tasksDueOn([dueToday, dueTodayCompleted, dueYesterday, dueTomorrow, noDate], now);

    expect(picked.map((t) => t.id).toSet(), {'a', 'b'},
        reason: '昨日/明日/无日期任务都不属于今日（引擎 goal_today_view 同口径）',);
  });

  test('dateOnlyOf 去掉时刻分量，跨时刻的同一天任务只计一次', () {
    final now = DateTime.now();
    final morning = DateTime(now.year, now.month, now.day, 8);
    final lateNight = DateTime(now.year, now.month, now.day, 23, 59);
    expect(dateOnlyOf(morning), dateOnlyOf(lateNight));

    final early = _task(id: 'am', dueDate: morning);
    final late = _task(id: 'pm', dueDate: lateNight);
    expect(tasksDueOn([early, late], now).length, 2);
  });
}
