import 'package:sparkle/l10n/app_localizations.dart';

extension CommunityAccountabilityHubL10n on AppLocalizations {
  bool get _zh => localeName.startsWith('zh');

  String get cahTitle => _zh ? '责任伙伴空间' : 'Accountability Hub';
  String get cahSubtitle => _zh
      ? '承诺、伙伴进度和共同目标都在这里'
      : 'Commitments, partner progress, and shared goals in one place';
  String get cahMyCommitments => _zh ? '我的承诺' : 'My commitments';
  String get cahPartnerProgress => _zh ? '伙伴进度' : 'Partner progress';
  String get cahSharedGoals => _zh ? '共同目标' : 'Shared goals';
  String get cahNeedsAttention => _zh ? '需要关注' : 'Needs attention';
  String get cahHelpable => _zh ? '我可以帮助' : 'People I can help';
  String get cahFeedEntry => _zh ? '进入动态 Feed' : 'Open social feed';
  String get cahFeedEntryHint => _zh
      ? 'Feed 保留为二级入口，用来分享和浏览动态'
      : 'The feed stays one tap away for sharing and browsing posts';
  String get cahFriendsEntry => _zh ? '好友' : 'Friends';
  String get cahGroupsEntry => _zh ? '小组' : 'Groups';
  String get cahEmptyTitle =>
      _zh ? '还没有责任承诺' : 'No accountability commitments yet';
  String get cahEmptyBody => _zh
      ? '先邀请一位伙伴，或从 Feed 里找到同目标的人一起前进。'
      : 'Invite a partner or find people with similar goals from the feed.';
  String get cahRetry => _zh ? '重试' : 'Retry';
  String get cahAllowReminder => _zh ? '允许提醒' : 'Allow reminders';
  String get cahDoNotDisturb => _zh ? '暂时勿扰' : 'Do not disturb';
  String get cahSuccessCriteria => _zh ? '成功标准' : 'Success criteria';
  String get cahMilestones => _zh ? '里程碑' : 'Milestones';
  String get cahEvidence => _zh ? '证据链' : 'Evidence';
  String get cahNoEvidence => _zh ? '还没有证据' : 'No evidence yet';
  String get cahProgress => _zh ? '进度' : 'Progress';
  String get cahWitnesses => _zh ? '见证人' : 'Witnesses';
  String get cahDueSoon => _zh ? '即将到期' : 'Due soon';
  String get cahActive => _zh ? '进行中' : 'Active';
  String get cahCompleted => _zh ? '已完成' : 'Completed';
  String get cahViolated => _zh ? '已违反' : 'Violated';
  String get cahTogetherNotRanking =>
      _zh ? '不是排名，是一起往前走' : 'Not a ranking, just moving together';
  String get cahTodayDone => _zh ? '今日已同步' : 'Synced today';
  String get cahTodayWaiting => _zh ? '今日待同步' : 'Waiting today';
  String get cahAcceptReminder => _zh ? '接受提醒' : 'Accept';
  String get cahDeclineReminder => _zh ? '拒绝' : 'Decline';
  String get cahLaterReminder => _zh ? '稍后' : 'Later';
  String get cahTooFrequentReminder => _zh ? '太频繁' : 'Too frequent';
  String get cahReminderAccepted => _zh ? '已开启提醒' : 'Reminder enabled';
  String get cahReminderDeclined => _zh ? '已拒绝本次提醒' : 'Declined this reminder';
  String get cahReminderLater => _zh ? '稍后再提醒' : 'Reminder snoozed';
  String get cahReminderReduced =>
      _zh ? '已降低提醒频率' : 'Reminder frequency reduced';
  String get cahUndo => _zh ? '撤销' : 'Undo';
  String get cahBoundaryChanged =>
      _zh ? '提醒边界已更新' : 'Reminder boundary updated';
  String get cahLoadFailed =>
      _zh ? '责任伙伴空间加载失败' : 'Failed to load accountability hub';
  String cahDueDate(String value) => _zh ? '截止 $value' : 'Due $value';
  String cahPercent(int value) => _zh ? '$value%' : '$value%';
  String cahPartnerGoal(String name) => _zh ? '$name 的目标' : '$name goal';

  // Strategy section
  String get cahStrategies => _zh ? '社区策略推荐' : 'Strategy suggestions';
  String get cahStrategyCreateTitle => _zh ? '创建你的第一个承诺' : 'Create your first commitment';
  String get cahStrategyCreateDesc => _zh
      ? '公开承诺能有效提升执行力和责任感。设定一个明确的目标开始吧。'
      : 'Public commitments boost follow-through and accountability. Set a clear goal to start.';
  String get cahStrategyCreateAction => _zh ? '创建承诺' : 'Create commitment';
  String get cahStrategyPartnerTitle => _zh ? '寻找责任伙伴' : 'Find an accountability partner';
  String get cahStrategyPartnerDesc => _zh
      ? '有一位伙伴同行能让坚持变得更容易，互相监督和鼓励。'
      : 'A partner makes persistence easier with mutual check-ins and encouragement.';
  String get cahStrategyPartnerAction => _zh ? '寻找伙伴' : 'Find partners';
  String get cahStrategySharedGoalTitle => _zh ? '加入共同目标' : 'Join a shared goal';
  String get cahStrategySharedGoalDesc => _zh
      ? '和一群人追求相同目标，集体的力量会带来意想不到的动力。'
      : 'Pursue a goal with others — collective momentum brings unexpected motivation.';
  String get cahStrategySharedGoalAction => _zh ? '浏览目标' : 'Browse goals';
  String get cahStrategySquadRiskTitle => _zh ? '关注团队风险' : 'Squad risks need attention';
  String get cahStrategySquadRiskDesc => _zh
      ? '你的团队中有需要关注的风险项，及时处理可以避免更大的问题。'
      : 'Your squad has risks that need attention — addressing them early prevents bigger issues.';
  String get cahStrategySquadRiskAction => _zh ? '查看详情' : 'View details';

  // Empty state CTAs
  String get cahFindPartners => _zh ? '寻找伙伴' : 'Find partners';
  String get cahCreateCommitment => _zh ? '创建承诺' : 'Create commitment';
}
