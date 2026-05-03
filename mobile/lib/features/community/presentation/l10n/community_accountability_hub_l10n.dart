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
}
