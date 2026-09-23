library;
import 'package:sparkle/l10n/app_localizations.dart';

/// 数据词典共享基础设施（SPEC DL-R3 §6.4「数据词典 schema」）。
///
/// S2 修复的立规点：任何后端原值（enum/事件名/类型字面量）直出给用户前，
/// 必须经 [Lexicon.lookup]（或各域词典的便捷函数）翻译成人类文案；
/// 未收录原值由调用方决定回退行为（通常回退原值，并应补录词条）。
///
/// 各域词典一域一文件：`goal_status_lexicon.dart`、`criterion_lexicon.dart`、
/// `memory_event_lexicon.dart`、`date_formatting.dart`、`error_lexicon.dart`
/// （N16 异常→人话映射单一 owner，类型化枚举为正解形制）。

/// arb 间接引用的标签解析器。
///
/// 词条文案必须走 arb key（labelZh/labelEn 经 [AppLocalizations] 间接引用），
/// 禁止在词典里散落硬编码字符串。
typedef LexiconLabel = String Function(AppLocalizations l10n);

/// 单条词典词条。
class LexiconEntry {
  const LexiconEntry({
    required this.domain,
    required this.raw,
    required this.label,
  });

  /// 数据域，如 `goal.status`、`goal.priority`、`memory.record`。
  final String domain;

  /// 后端原值（enum/事件名等），如 `"active"`。
  final String raw;

  /// 人话文案（经 arb 间接引用）。
  final LexiconLabel label;
}

/// 全 app 唯一的词典查询入口。
class Lexicon {
  const Lexicon._();

  static final Map<String, LexiconEntry> _entries =
      <String, LexiconEntry>{};

  /// 注册一批词条（各域词典文件在初始化时调用；重复注册以最后一次为准）。
  static void registerAll(Iterable<LexiconEntry> entries) {
    for (final entry in entries) {
      _entries['${entry.domain}.${entry.raw}'] = entry;
    }
  }

  /// 查词条文案；未收录返回 null（调用方自行回退原值）。
  static String? lookup(String domain, String? raw, AppLocalizations l10n) {
    if (raw == null || raw.isEmpty) {
      return null;
    }
    final entry = _entries['$domain.$raw'];
    return entry == null ? null : entry.label(l10n);
  }

  /// 是否已收录（测试与 ratchet 守卫用）。
  static bool has(String domain, String raw) =>
      _entries.containsKey('$domain.$raw');
}

/// §6.3 数字准入：连续量的三档人话（禁出两位小数裸数值）。
///
/// 阈值沿用 §6.3 三档表（≥0.75 / 0.50–0.75 / <0.50）。
String bandLabel(
  double value,
  AppLocalizations l10n, {
  required String Function(AppLocalizations) high,
  required String Function(AppLocalizations) mid,
  required String Function(AppLocalizations) low,
}) {
  if (value >= 0.75) {
    return high(l10n);
  }
  if (value >= 0.50) {
    return mid(l10n);
  }
  return low(l10n);
}
