import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// wt422 l10n 收割 smoke：核心屏（home 仪表盘族 + 通知列表）42 个新键
/// 双语存在且非空。迁移源为手写 `zh ? '中文' : 'English'` 三元旁路，
/// 文案逐字保留（含占位串），arb 只尾追加不改既有行。
void main() {
  final zh = AppLocalizationsZh();
  final en = AppLocalizationsEn();

  void both(
    String Function(AppLocalizationsZh) zhPick,
    String Function(AppLocalizationsEn) enPick,
  ) {
    expect(zhPick(zh), isNotEmpty, reason: 'zh copy must be non-empty');
    expect(enPick(en), isNotEmpty, reason: 'en copy must be non-empty');
  }

  test('wt422 收割键：通知列表屏（3 键）', () {
    both((l) => l.notificationListEmptyTitle, (l) => l.notificationListEmptyTitle);
    both((l) => l.notificationListEmptySubtitle, (l) => l.notificationListEmptySubtitle);
    both((l) => l.notificationMarkAsReadFailed, (l) => l.notificationMarkAsReadFailed);
  });

  test('wt422 收割键：sprint_card（5 键）', () {
    both((l) => l.sprintCardTitle, (l) => l.sprintCardTitle);
    both((l) => l.sprintCardDayUnit, (l) => l.sprintCardDayUnit);
    both((l) => l.sprintCardPercentDone, (l) => l.sprintCardPercentDone);
    both((l) => l.sprintCardEmptyTitle, (l) => l.sprintCardEmptyTitle);
    both((l) => l.sprintCardEmptyAction, (l) => l.sprintCardEmptyAction);
  });

  test('wt422 收割键：today_growth_status_card（10 键，含占位串）', () {
    expect(zh.todayGrowthTaskProgress(1, 3), '今天 1/3 项任务');
    expect(en.todayGrowthTaskProgress(1, 3), 'Today 1/3 tasks');
    expect(zh.todayGrowthPlanHealth('●●○○○'), '计划健康度 ●●○○○');
    expect(en.todayGrowthPlanHealth('●●○○○'), 'Plan Health ●●○○○');
    expect(zh.todayGrowthStreakDays(7), '连续学习 7 天 🔥');
    expect(en.todayGrowthStreakDays(7), '7 day streak 🔥');
    expect(zh.todayGrowthFirstTaskMessage('复盘'), '今天的第一件事是复盘。');
    expect(en.todayGrowthFirstTaskMessage('Review'), 'First task today: Review.');
    both((l) => l.todayGrowthPhaseDefault, (l) => l.todayGrowthPhaseDefault);
    both((l) => l.todayGrowthCreateFirstPlan, (l) => l.todayGrowthCreateFirstPlan);
    both((l) => l.todayGrowthCreateFirstPlanSubtitle, (l) => l.todayGrowthCreateFirstPlanSubtitle);
    both((l) => l.todayGrowthDoneMessage, (l) => l.todayGrowthDoneMessage);
    both((l) => l.todayGrowthKeepRhythmMessage, (l) => l.todayGrowthKeepRhythmMessage);
    both((l) => l.todayGrowthPickLightTaskMessage, (l) => l.todayGrowthPickLightTaskMessage);
  });

  test('wt422 收割键：multi_goal_dashboard_card（12 键，含占位串）', () {
    expect(zh.multiGoalActiveGoalCount(3), '3 个活跃目标');
    expect(en.multiGoalActiveGoalCount(3), '3 active goals');
    expect(zh.multiGoalWeeklyConflicts(2), '本周冲突 2');
    expect(en.multiGoalWeeklyConflicts(2), '2 conflicts');
    expect(zh.multiGoalOverdueDays(4), '已逾期 4 天');
    expect(en.multiGoalOverdueDays(4), '4d overdue');
    expect(zh.multiGoalDaysLeft(5), '剩余 5 天');
    expect(en.multiGoalDaysLeft(5), '5d left');
    both((l) => l.multiGoalDashboardTitle, (l) => l.multiGoalDashboardTitle);
    both((l) => l.multiGoalExpandCollapse, (l) => l.multiGoalExpandCollapse);
    both((l) => l.multiGoalSuggestedFirst, (l) => l.multiGoalSuggestedFirst);
    both((l) => l.multiGoalUseSuggestion, (l) => l.multiGoalUseSuggestion);
    both((l) => l.multiGoalManualAdjust, (l) => l.multiGoalManualAdjust);
    both((l) => l.multiGoalPhaseInProgress, (l) => l.multiGoalPhaseInProgress);
    both((l) => l.multiGoalNoDeadline, (l) => l.multiGoalNoDeadline);
    both((l) => l.multiGoalDueToday, (l) => l.multiGoalDueToday);
  });

  test('wt422 收割键：task_preview_panel（12 键，含复数与占位串）', () {
    expect(zh.taskPreviewTaskCount(0), '0 个任务');
    expect(zh.taskPreviewTaskCount(2), '2 个任务');
    expect(en.taskPreviewTaskCount(1), '1 task');
    expect(en.taskPreviewTaskCount(2), '2 tasks');
    expect(zh.taskPreviewViewAllTasks(1), '查看全部 1 个任务');
    expect(zh.taskPreviewViewAllTasks(5), '查看全部 5 个任务');
    expect(en.taskPreviewViewAllTasks(1), 'View all 1 task');
    expect(en.taskPreviewViewAllTasks(5), 'View all 5 tasks');
    expect(zh.taskPreviewCheckedFromSource('sprint'), '来源：sprint');
    expect(en.taskPreviewCheckedFromSource('sprint'), 'From: sprint');
    both((l) => l.taskPreviewToday, (l) => l.taskPreviewToday);
    both((l) => l.taskPreviewNoTasks, (l) => l.taskPreviewNoTasks);
    both((l) => l.taskPreviewEnjoyFreeTime, (l) => l.taskPreviewEnjoyFreeTime);
    both((l) => l.taskPreviewCheckedLabel, (l) => l.taskPreviewCheckedLabel);
    both((l) => l.taskPreviewCheckedDoneSubtitle, (l) => l.taskPreviewCheckedDoneSubtitle);
    both((l) => l.taskPreviewProtectedLabel, (l) => l.taskPreviewProtectedLabel);
    both((l) => l.taskPreviewProtectedSubtitle, (l) => l.taskPreviewProtectedSubtitle);
    both((l) => l.taskPreviewMissedLabel, (l) => l.taskPreviewMissedLabel);
    both((l) => l.taskPreviewMissedSubtitle, (l) => l.taskPreviewMissedSubtitle);
  });
}
