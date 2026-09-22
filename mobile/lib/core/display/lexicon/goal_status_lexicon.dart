library;
import 'package:sparkle/core/display/lexicon/lexicon.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// goal 域状态/优先级与 memory 记录生命周期状态的词典。
///
/// S2 例3（AUDIT：goal 状态 chip 直出「active」「normal」）与 S2 例4
/// （memory 面板 subtitle 直出原始状态）的翻译层。
/// 值域依据引擎模型列注释：
/// - goal.status: draft | active | paused | completed | archived | cancelled
///   （backend/app/models/goal.py）
/// - goal.priority: critical | high | normal | low
/// - memory 记录状态: derive_status 产 active/superseded/retracted/archived/
///   expired/resolved/revoked；MemoryGoal.status 另见 completed/cancelled/paused
///   （INACTIVE_GOAL_STATUSES）。

/// 数据域常量。
const String kDomainGoalStatus = 'goal.status';
const String kDomainGoalPriority = 'goal.priority';
const String kDomainMemoryRecordStatus = 'memory.record';

final List<LexiconEntry> _goalStatusEntries = [
  LexiconEntry(
    domain: kDomainGoalStatus,
    raw: 'draft',
    label: (l10n) => l10n.goalStatusDraft,
  ),
  LexiconEntry(
    domain: kDomainGoalStatus,
    raw: 'active',
    label: (l10n) => l10n.goalStatusActive,
  ),
  LexiconEntry(
    domain: kDomainGoalStatus,
    raw: 'paused',
    label: (l10n) => l10n.goalStatusPaused,
  ),
  LexiconEntry(
    domain: kDomainGoalStatus,
    raw: 'completed',
    label: (l10n) => l10n.goalStatusCompleted,
  ),
  LexiconEntry(
    domain: kDomainGoalStatus,
    raw: 'archived',
    label: (l10n) => l10n.goalStatusArchived,
  ),
  LexiconEntry(
    domain: kDomainGoalStatus,
    raw: 'cancelled',
    label: (l10n) => l10n.goalStatusCancelled,
  ),
];

final List<LexiconEntry> _goalPriorityEntries = [
  LexiconEntry(
    domain: kDomainGoalPriority,
    raw: 'critical',
    label: (l10n) => l10n.goalPriorityCritical,
  ),
  LexiconEntry(
    domain: kDomainGoalPriority,
    raw: 'high',
    label: (l10n) => l10n.goalPriorityHigh,
  ),
  LexiconEntry(
    domain: kDomainGoalPriority,
    raw: 'normal',
    label: (l10n) => l10n.goalPriorityNormal,
  ),
  LexiconEntry(
    domain: kDomainGoalPriority,
    raw: 'low',
    label: (l10n) => l10n.goalPriorityLow,
  ),
];

final List<LexiconEntry> _memoryRecordStatusEntries = [
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'active',
    label: (l10n) => l10n.memoryRecordStatusActive,
  ),
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'resolved',
    label: (l10n) => l10n.memoryRecordStatusResolved,
  ),
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'archived',
    label: (l10n) => l10n.memoryRecordStatusArchived,
  ),
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'expired',
    label: (l10n) => l10n.memoryRecordStatusExpired,
  ),
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'revoked',
    label: (l10n) => l10n.memoryRecordStatusRevoked,
  ),
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'superseded',
    label: (l10n) => l10n.memoryRecordStatusSuperseded,
  ),
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'retracted',
    label: (l10n) => l10n.memoryRecordStatusRetracted,
  ),
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'completed',
    label: (l10n) => l10n.memoryRecordStatusCompleted,
  ),
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'cancelled',
    label: (l10n) => l10n.memoryRecordStatusCancelled,
  ),
  LexiconEntry(
    domain: kDomainMemoryRecordStatus,
    raw: 'paused',
    label: (l10n) => l10n.memoryRecordStatusPaused,
  ),
];

bool _registered = false;

void _ensureRegistered() {
  if (_registered) {
    return;
  }
  Lexicon.registerAll(_goalStatusEntries);
  Lexicon.registerAll(_goalPriorityEntries);
  Lexicon.registerAll(_memoryRecordStatusEntries);
  _registered = true;
}

/// goal 状态 → 人话；未收录返回 null（调用方回退原值）。
String? goalStatusLabel(AppLocalizations l10n, String? raw) {
  _ensureRegistered();
  return Lexicon.lookup(kDomainGoalStatus, raw, l10n);
}

/// goal 优先级 → 人话；未收录返回 null。
String? goalPriorityLabel(AppLocalizations l10n, String? raw) {
  _ensureRegistered();
  return Lexicon.lookup(kDomainGoalPriority, raw, l10n);
}

/// memory 记录状态 → 人话；未收录返回 null。
String? memoryRecordStatusLabel(AppLocalizations l10n, String? raw) {
  _ensureRegistered();
  return Lexicon.lookup(kDomainMemoryRecordStatus, raw, l10n);
}
