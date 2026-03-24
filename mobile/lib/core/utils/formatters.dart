import 'package:intl/intl.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// Localized formatters for dates, times, durations, and numbers.
///
/// All formatters respect the current locale settings.
class Formatters {
  Formatters._();

  // ============== Date Formatters ==============

  /// Format date as short format (e.g., "3/10/26" in EN, "2026/3/10" in ZH)
  static String formatDateShort(DateTime date) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return DateFormat.yMd(locale).format(date);
  }

  /// Format date as medium format (e.g., "Mar 10, 2026" in EN, "2026年3月10日" in ZH)
  static String formatDateMedium(DateTime date) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return DateFormat.yMMMd(locale).format(date);
  }

  /// Format date as long format with weekday
  static String formatDateLong(DateTime date) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return DateFormat.yMMMMEEEEd(locale).format(date);
  }

  /// Format date and time
  static String formatDateTime(DateTime dateTime) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return DateFormat.yMMMd(locale).add_Hm().format(dateTime);
  }

  /// Format time only (e.g., "3:30 PM" in EN, "15:30" in ZH)
  static String formatTime(DateTime dateTime) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return DateFormat.jm(locale).format(dateTime);
  }

  /// Format time in 24-hour format
  static String formatTime24(DateTime dateTime) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return DateFormat.Hm(locale).format(dateTime);
  }

  /// Format relative time (e.g., "2 hours ago", "in 3 days")
  static String formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final isFuture = dateTime.isAfter(now);
    final difference = isFuture ? dateTime.difference(now) : now.difference(dateTime);
    final l10n = I18nService.instance.l10n;

    if (difference.inDays > 365) {
      final years = (difference.inDays / 365).floor();
      return isFuture ? l10n.timeInYears(years) : l10n.timeYearsAgo(years);
    } else if (difference.inDays > 30) {
      final months = (difference.inDays / 30).floor();
      return isFuture ? l10n.timeInMonths(months) : l10n.timeMonthsAgo(months);
    } else if (difference.inDays > 0) {
      return isFuture ? l10n.timeInDays(difference.inDays) : l10n.timeDaysAgo(difference.inDays);
    } else if (difference.inHours > 0) {
      return isFuture ? l10n.timeInHours(difference.inHours) : l10n.timeHoursAgo(difference.inHours);
    } else if (difference.inMinutes > 0) {
      return isFuture
          ? l10n.timeInMinutes(difference.inMinutes)
          : l10n.timeMinutesAgo(difference.inMinutes);
    } else {
      return l10n.timeJustNow;
    }
  }

  // ============== Duration Formatters ==============

  /// Format duration in human-readable form
  /// e.g., "1h 30m" or "1小时30分钟"
  static String formatDuration(Duration duration) {
    final l10n = I18nService.instance.l10n;
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);
    String joinParts(String first, String second) =>
        I18nService.instance.isChinese ? '$first$second' : '$first $second';

    if (hours > 0) {
      final hourPart = l10n.durationHours(hours);
      if (minutes > 0) {
        final minutePart = l10n.durationMinutes(minutes);
        return joinParts(hourPart, minutePart);
      }
      return hourPart;
    } else if (minutes > 0) {
      final minutePart = l10n.durationMinutes(minutes);
      if (seconds > 0) {
        final secondPart = l10n.durationSeconds(seconds);
        return joinParts(minutePart, secondPart);
      }
      return minutePart;
    } else {
      return l10n.durationSeconds(seconds);
    }
  }

  /// Format duration as countdown (e.g., "05:30" for 5 min 30 sec)
  static String formatCountdown(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);

    if (hours > 0) {
      return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    }
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  /// Format duration in compact form for focus timer
  static String formatFocusDuration(Duration duration) {
    final l10n = I18nService.instance.l10n;
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    String joinParts(String first, String second) =>
        I18nService.instance.isChinese ? '$first$second' : '$first $second';

    if (hours > 0) {
      final hourPart = l10n.durationHours(hours);
      if (minutes > 0) {
        final minutePart = l10n.durationMinutes(minutes);
        return joinParts(hourPart, minutePart);
      }
      return hourPart;
    }
    return l10n.durationMinutes(minutes);
  }

  /// Format date as month/day (e.g., "Mar 10" in EN, "3月10日" in ZH)
  static String formatDateMonthDay(DateTime date) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return DateFormat.MMMd(locale).format(date);
  }

  // ============== Number Formatters ==============

  /// Format number with locale-specific grouping
  static String formatNumber(num number) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return NumberFormat.decimalPattern(locale).format(number);
  }

  /// Format number as percentage
  static String formatPercent(num value, {int decimalDigits = 0}) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return NumberFormat.percentPattern(locale)
        .format(value)
        .replaceAll('%', I18nService.instance.isChinese ? '%' : '%');
  }

  /// Format compact number (e.g., "1.2K", "1.2万")
  static String formatCompact(num number) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return NumberFormat.compact(locale: locale).format(number);
  }

  /// Format currency (generic)
  static String formatCurrency(num amount, {String symbol = '¥'}) {
    final locale = I18nService.instance.currentLocale.languageCode;
    return NumberFormat.currency(locale: locale, symbol: symbol).format(amount);
  }

}
