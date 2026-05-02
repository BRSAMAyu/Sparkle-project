import 'package:sparkle/l10n/app_localizations.dart';

extension GoalDetailLocalizations on AppLocalizations {
  bool get _isZh => localeName.toLowerCase().startsWith('zh');

  String get goalDetailTitle => _isZh ? '目标详情' : 'Goal detail';
  String get goalDetailProgress => _isZh ? '总体进度' : 'Overall progress';
  String get goalDetailMastery => _isZh ? '掌握度' : 'Mastery';
  String get goalDetailTargetDate => _isZh ? '目标日期' : 'Target date';
  String get goalDetailPriority => _isZh ? '优先级' : 'Priority';
  String get goalDetailNoTargetDate => _isZh ? '未设置日期' : 'No date set';
  String get goalDetailMinimumLine => _isZh ? '最低达标线' : 'Minimum bar';
  String get goalDetailSuggestedMinimum => _isZh
      ? '这是 Sparkle 为你建议的最低标准'
      : 'Sparkle suggested this minimum standard';
  String get goalDetailConfirmedMinimum =>
      _isZh ? '已确认的最低标准' : 'Confirmed minimum standard';
  String get goalDetailConfirm => _isZh ? '确认' : 'Confirm';
  String get goalDetailModify => _isZh ? '修改' : 'Modify';
  String get goalDetailUndo => _isZh ? '撤销' : 'Undo';
  String get goalDetailConfirmedSnack =>
      _isZh ? '已确认最低达标线' : 'Minimum bar confirmed';
  String get goalDetailModifySnack => _isZh
      ? '修改入口已保留给收口整合'
      : 'Edit entry is reserved for closeout integration';
  String get goalDetailNoCriteria => _isZh
      ? '还没有最低达标线，先从今天的最小一步开始。'
      : 'No minimum bar yet. Start with the smallest step for today.';
  String get goalDetailBottlenecks => _isZh ? '知识瓶颈' : 'Knowledge bottlenecks';
  String get goalDetailNoBottlenecks =>
      _isZh ? '暂时没有检测到瓶颈节点。' : 'No bottleneck nodes detected yet.';
  String get goalDetailOpenGalaxy => _isZh ? '打开星图' : 'Open galaxy';
  String goalDetailMasteryPercent(int percent) =>
      _isZh ? '掌握 $percent%' : '$percent% mastery';
  String get goalDetailTodayStep =>
      _isZh ? '今日最小下一步' : 'Today’s smallest next step';
  String get goalDetailNoTodayStep => _isZh
      ? '今天没有待执行任务，可以先复盘或补充计划。'
      : 'No task queued for today. Review or refine the plan first.';
  String get goalDetailStart => _isZh ? '开始' : 'Start';
  String get goalDetailComplete => _isZh ? '完成' : 'Complete';
  String get goalDetailStartedSnack =>
      _isZh ? '已开始今日最小一步' : 'Started today’s smallest step';
  String get goalDetailCompletedTitle =>
      _isZh ? '完成这一步？' : 'Complete this step?';
  String get goalDetailCompletedBody =>
      _isZh ? '完成后会刷新目标详情。' : 'The goal detail will refresh after completion.';
  String get goalDetailCancel => _isZh ? '取消' : 'Cancel';
  String get goalDetailPlanHealth => _isZh ? '计划健康状态' : 'Plan health';
  String get goalDetailPhaseHealth => _isZh ? '阶段健康' : 'Phase health';
  String get goalDetailTaskCompletion => _isZh ? '任务完成率' : 'Task completion';
  String get goalDetailCurrentPhase => _isZh ? '当前阶段' : 'Current phase';
  String get goalDetailAccountability => _isZh ? '社群问责' : 'Accountability';
  String goalDetailPartners(int count) =>
      _isZh ? '$count 位伙伴' : '$count partners';
  String goalDetailCommitments(int count) =>
      _isZh ? '$count 个活跃承诺' : '$count active commitments';
  String get goalDetailNoCheckin => _isZh ? '暂无打卡' : 'No check-in yet';
  String get goalDetailOpenCommunity =>
      _isZh ? '进入问责空间' : 'Open accountability';
  String get goalDetailRelatedSources => _isZh ? '相关资料来源' : 'Related sources';
  String get goalDetailNoSources =>
      _isZh ? '暂无关联资料。' : 'No related sources yet.';
  String goalDetailRelevance(int percent) =>
      _isZh ? '相关度 $percent%' : '$percent% relevant';
  String get goalDetailRefresh => _isZh ? '刷新目标详情' : 'Refresh goal detail';
  String get goalDetailLoadFailed =>
      _isZh ? '目标详情加载失败' : 'Goal detail failed to load';
  String get goalDetailRetry => _isZh ? '重试' : 'Retry';
  String get goalDetailBack => _isZh ? '返回' : 'Back';
  String get goalDetailStatus => _isZh ? '状态' : 'Status';
  String get goalDetailEstimated => _isZh ? '预计' : 'Estimated';
  String goalDetailMinutes(int minutes) =>
      _isZh ? '$minutes 分钟' : '$minutes min';
}
