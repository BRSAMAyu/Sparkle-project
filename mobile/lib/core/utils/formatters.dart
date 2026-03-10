import 'package:intl/intl.dart';
import '../services/i18n_service.dart';

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
    return DateFormat.Hm().format(dateTime);
  }

  /// Format relative time (e.g., "2 hours ago", "in 3 days")
  static String formatRelativeTime(DateTime dateTime) {
    final now = DateTime.now();
    final difference = now.difference(dateTime);
    final isFuture = dateTime.isAfter(now);

    if (difference.inDays > 365) {
      final years = (difference.inDays / 365).floor();
      return isFuture
          ? _plural('time.years.in', years)
          : _plural('time.years.ago', years);
    } else if (difference.inDays > 30) {
      final months = (difference.inDays / 30).floor();
      return isFuture
          ? _plural('time.months.in', months)
          : _plural('time.months.ago', months);
    } else if (difference.inDays > 0) {
      return isFuture
          ? _plural('time.days.in', difference.inDays)
          : _plural('time.days.ago', difference.inDays);
    } else if (difference.inHours > 0) {
      return isFuture
          ? _plural('time.hours.in', difference.inHours)
          : _plural('time.hours.ago', difference.inHours);
    } else if (difference.inMinutes > 0) {
      return isFuture
          ? _plural('time.minutes.in', difference.inMinutes)
          : _plural('time.minutes.ago', difference.inMinutes);
    } else {
      return I18nService.instance.isEnglish ? 'Just now' : '刚刚';
    }
  }

  // ============== Duration Formatters ==============

  /// Format duration in human-readable form
  /// e.g., "1h 30m" or "1小时30分钟"
  static String formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);

    if (hours > 0) {
      if (I18nService.instance.isChinese) {
        return '$hours小时${minutes > 0 ? '$minutes分钟' : ''}';
      }
      return '${hours}h ${minutes}m';
    } else if (minutes > 0) {
      if (I18nService.instance.isChinese) {
        return '$minutes分钟${seconds > 0 ? '$seconds秒' : ''}';
      }
      return '${minutes}m ${seconds}s';
    } else {
      if (I18nService.instance.isChinese) {
        return '$seconds秒';
      }
      return '${seconds}s';
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
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);

    if (I18nService.instance.isChinese) {
      if (hours > 0) {
        return '$hours小时$minutes分钟';
      }
      return '$minutes分钟';
    }
    if (hours > 0) {
      return '${hours}h ${minutes}m';
    }
    return '${minutes}m';
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

  // ============== Helper Methods ==============

  static String _plural(String key, int count) {
    // Simple plural handling - will be replaced by ARB ICU messages
    final isChinese = I18nService.instance.isChinese;
    switch (key) {
      case 'time.years.ago':
        return isChinese ? '$count年前' : '$count year${count != 1 ? 's' : ''} ago';
      case 'time.years.in':
        return isChinese ? '$count年后' : 'in $count year${count != 1 ? 's' : ''}';
      case 'time.months.ago':
        return isChinese ? '$count个月前' : '$count month${count != 1 ? 's' : ''} ago';
      case 'time.months.in':
        return isChinese ? '$count个月后' : 'in $count month${count != 1 ? 's' : ''}';
      case 'time.days.ago':
        return isChinese ? '$count天前' : '$count day${count != 1 ? 's' : ''} ago';
      case 'time.days.in':
        return isChinese ? '$count天后' : 'in $count day${count != 1 ? 's' : ''}';
      case 'time.hours.ago':
        return isChinese ? '$count小时前' : '$count hour${count != 1 ? 's' : ''} ago';
      case 'time.hours.in':
        return isChinese ? '$count小时后' : 'in $count hour${count != 1 ? 's' : ''}';
      case 'time.minutes.ago':
        return isChinese ? '$count分钟前' : '$count minute${count != 1 ? 's' : ''} ago';
      case 'time.minutes.in':
        return isChinese ? '$count分钟后' : 'in $count minute${count != 1 ? 's' : ''}';
      default:
        return '$count';
    }
  }
}
