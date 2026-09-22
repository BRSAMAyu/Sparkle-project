library;
import 'package:sparkle/l10n/app_localizations.dart';

/// memory 事件名 → 人话动词词典（SPEC DL §6.4「事件名→人话」）。
///
/// S2 例4：情景记忆标题直出「completed …」原始英文事件名（AUDIT V20）。
/// 引擎写入的 summary 是自由文本，这里只对**已知事件动词前缀**做整句翻译，
/// 未命中的一律原样返回（不猜测语义、不破坏用户自己的内容）。

class _EventVerbRule {
  const _EventVerbRule(this.pattern, this.template);
  final RegExp pattern;
  /// (l10n, title) → 人话整句。
  final String Function(AppLocalizations l10n, String title) template;
}

final List<_EventVerbRule> _eventVerbRules = [
  _EventVerbRule(
    RegExp(r'^completed\s+(?<title>.+)$', caseSensitive: false),
    (l10n, title) => l10n.memoryEventCompleted(title),
  ),
  _EventVerbRule(
    RegExp(r'^finished\s+(?<title>.+)$', caseSensitive: false),
    (l10n, title) => l10n.memoryEventFinished(title),
  ),
  _EventVerbRule(
    RegExp(r'^reviewed\s+(?<title>.+)$', caseSensitive: false),
    (l10n, title) => l10n.memoryEventReviewed(title),
  ),
  _EventVerbRule(
    RegExp(r'^practiced\s+(?<title>.+)$', caseSensitive: false),
    (l10n, title) => l10n.memoryEventPracticed(title),
  ),
  _EventVerbRule(
    RegExp(r'^mastered\s+(?<title>.+)$', caseSensitive: false),
    (l10n, title) => l10n.memoryEventMastered(title),
  ),
];

/// 把「completed X」类英文事件名翻成「已完成「X」」；未命中返回原文。
String humanizeMemoryEvent(String raw, AppLocalizations l10n) {
  final text = raw.trim();
  if (text.isEmpty || !_containsAsciiLetter(text)) {
    return raw;
  }
  for (final rule in _eventVerbRules) {
    final match = rule.pattern.firstMatch(text);
    if (match != null) {
      final title = match.namedGroup('title')?.trim() ?? '';
      if (title.isNotEmpty) {
        return rule.template(l10n, title);
      }
    }
  }
  return raw;
}

bool _containsAsciiLetter(String text) {
  for (final code in text.codeUnits) {
    if ((code >= 0x41 && code <= 0x5A) || (code >= 0x61 && code <= 0x7A)) {
      return true;
    }
  }
  return false;
}
