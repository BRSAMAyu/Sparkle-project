library;
import 'package:sparkle/l10n/app_localizations.dart';

/// 时间格式化唯一入口（SPEC DL §6.4 时间格式规范）。
///
/// S2 例2：DateTime.toString() 直出毫秒时间戳（「2026-09-20 15:00:00.000」）
/// 的翻译层。规则：
/// - 相对优先（「今天 15:00」「3天后 15:00」「昨天 15:00」）；
/// - ≥7 天落绝对（「9月20日 15:00」/「9/20 15:00」）；
/// - 禁毫秒；同日起止 Range 折叠为单点（X8）。

/// 当天零点（用于日历差计算，避免时分秒干扰）。
DateTime _dateOnly(DateTime value) => DateTime(value.year, value.month, value.day);

/// HH:mm（禁毫秒）。
String formatSparkleClock(DateTime value) {
  final local = value.toLocal();
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return '$hour:$minute';
}

/// 相对优先的日期时间人话格式。
String formatSparkleDateTime(DateTime value, AppLocalizations l10n) {
  final local = value.toLocal();
  final now = DateTime.now();
  final clock = formatSparkleClock(local);
  final dayDelta = _dateOnly(local).difference(_dateOnly(now)).inDays;
  if (dayDelta == 0) {
    return l10n.displayDateToday(clock);
  }
  if (dayDelta == 1) {
    return l10n.displayDateTomorrow(clock);
  }
  if (dayDelta == -1) {
    return l10n.displayDateYesterday(clock);
  }
  if (dayDelta > 1 && dayDelta < 7) {
    return l10n.displayDateInDays(dayDelta, clock);
  }
  if (dayDelta < -1 && dayDelta > -7) {
    return l10n.displayDateDaysAgo(-dayDelta, clock);
  }
  return l10n.displayDateAbsolute(local.month, local.day, clock);
}

/// 纯日期（无时钟）的绝对格式，用于截止日等只看日不看时的展示位。
String formatSparkleDateOnly(DateTime value, AppLocalizations l10n) {
  final local = value.toLocal();
  return l10n.displayDateOnly(local.month, local.day);
}

/// 日期分组头（流水/记录类列表按日分组的标题行）：今天/昨天/N天前，
/// ≥7 天落纯日期绝对格式（无时钟）。原 photon 流水页自算实现（PHOTON 卡
/// #7，A-SPEC2 PH-G6）收编入唯一入口；相对窗口与 [formatSparkleDateTime]
/// 同为 7 天。
String formatSparkleDayHeader(DateTime value, AppLocalizations l10n) {
  final dayDelta =
      _dateOnly(value.toLocal()).difference(_dateOnly(DateTime.now())).inDays;
  if (dayDelta == 0) {
    return l10n.timeToday;
  }
  if (dayDelta == -1) {
    return l10n.timeYesterday;
  }
  if (dayDelta < -1 && dayDelta > -7) {
    return l10n.displayDateDaysAgoOnly(-dayDelta);
  }
  final local = value.toLocal();
  return l10n.displayDateOnly(local.month, local.day);
}

/// 起止时间的 Range 格式；起止相同（同点/同分钟）折叠为单点（X8）。
String formatSparkleSceneRange(
  DateTime start,
  DateTime end,
  AppLocalizations l10n,
) {
  final a = start.toLocal();
  final b = end.toLocal();
  final startLabel = formatSparkleDateTime(a, l10n);
  if (_dateOnly(a) == _dateOnly(b) &&
      a.hour == b.hour &&
      a.minute == b.minute) {
    return startLabel;
  }
  final endLabel = formatSparkleDateTime(b, l10n);
  if (_dateOnly(a) == _dateOnly(b)) {
    // 同日：日期只标一次（「今天 13:00 - 15:00」式）。
    final prefix = startLabel.substring(0, startLabel.length - 5);
    return '$prefix${formatSparkleClock(a)} - ${formatSparkleClock(b)}';
  }
  return '$startLabel - $endLabel';
}
