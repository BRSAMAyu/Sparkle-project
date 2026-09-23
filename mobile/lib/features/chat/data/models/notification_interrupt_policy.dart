/// N22（A-SPEC4 v1.4 §7.3）· WS 通知打断三档分级 · 常量映射表（单一事实源）。
///
/// 分级哲学（HIG 通知分级 / Linear inbox 集中制的 app 内版）：
/// **通知中心是全量落点，toast 是特权**——等级由内容声明、入口单点执行
/// （`ChatNotifierActions._handleNotificationEvent`，IR-G3 原双写直通处）。
///
/// 引擎侧已实证的 priority 词汇（只读走查 @wt245 基线）：
/// - `notification_service.py`：`"priority": priority`，取值 `low|normal|high`，
///   缺省 `normal`；
/// - `state_notification_service.py`：plan_archived/plan_deleted=`medium`、
///   plan_restored/settings/memory_cleanup=`low`；
/// - `notification_center_service.py`：intervention 按 requested_level
///   modal/card 映射为 high，否则 medium。
enum NotificationInterruptTier {
  /// 即时档：toast + 进中心。时间敏感/被@/小队事件，需要用户立刻知道。
  immediate,

  /// 摘要档：仅进中心 + 中心红点（未读数），用户下次到中心时可见。
  /// （今日中心未读数即红点承载；「首页摘要」类外显机制后接时只消费本档。）
  digest,

  /// 静默档：仅进中心，不参与任何外显摘要（与 digest 的差异在语义钉位，
  /// 供后续外显摘要机制消费；当前行为同为只入中心）。
  silent,
}

/// priority / 通知类型 → 打断三档 的常量判定表。
///
/// 保守条款（N22 明文）：**intervention 与 aurora_confirm 两类一律按
/// immediate 处理**（宁多一次 toast，不可漏干预）——类型白名单优先于
/// priority 字段；其余类按 priority 字段执行。
class NotificationInterruptPolicy {
  const NotificationInterruptPolicy._();

  /// 强制即时档的 source 通道（notificationType，保守条款 N22）。
  static const Set<String> forcedImmediateSourceTypes = <String>{
    'intervention',
    'intervention_push',
    'aurora_confirm',
  };

  /// 强制即时档的内容类型白名单（被@/小队事件等高优，卡片口径）。
  /// 命中即 toast+进中心，不看 priority 字段。
  static const Set<String> forcedImmediateContentTypes = <String>{
    'mention',
    'squad_event',
    'squad_invite',
    'squad_mention',
    'squad_join',
    'accountability_struggle_alert',

    /// 时间敏感例外（HIG time-sensitive tier）：截止提醒即时间敏感。
    'task_reminder',
  };

  /// priority 字段 → 三档：
  /// - `high` → immediate；
  /// - `normal`（引擎缺省值）/`medium` → digest（普通通知只进中心）；
  /// - `low` → silent；
  /// - 未知值保守归 digest（普通档，白名单已兜住高优）。
  static NotificationInterruptTier tierForPriority(String? priority) {
    switch (priority?.trim().toLowerCase()) {
      case 'high':
        return NotificationInterruptTier.immediate;
      case 'low':
        return NotificationInterruptTier.silent;
      case 'normal':
      case 'medium':
      default:
        return NotificationInterruptTier.digest;
    }
  }

  /// 单点分流判定（类型白名单优先于 priority 字段）。
  ///
  /// [sourceType]：WS 事件通道（`NotificationEvent.notificationType`，
  /// 'system' | 'intervention'）；[contentType]：内容类型
  /// （`NotificationEvent.type`，如 plan_archived/task_reminder）。
  static NotificationInterruptTier resolve({
    required String sourceType,
    required String contentType,
    String? priority,
  }) {
    final source = sourceType.trim().toLowerCase();
    final type = contentType.trim().toLowerCase();
    if (forcedImmediateSourceTypes.contains(source) ||
        forcedImmediateContentTypes.contains(type)) {
      return NotificationInterruptTier.immediate;
    }
    return tierForPriority(priority);
  }
}
