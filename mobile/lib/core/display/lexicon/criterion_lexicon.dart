library;
import 'package:sparkle/l10n/app_localizations.dart';

/// 达标线（minimum acceptance criteria）机话兜底词典。
///
/// S2 例1：引擎 `experience_readouts._criterion_label` 修复后已直接产出
/// 人话整句；本词典兜底的是**存量/缓存里的旧机器拼接**（「X >= 1boolean」式），
/// 覆盖 TRIAGE §3#1 ②「mobile `_readableLine` 无 unit/type 词典兜底」缺失点。
///
/// unit 值域（全量核查）：boolean（goal_decomposition_service）、
/// percent/count/days/time（seed 脚本）；未知 unit 不猜测语义，仅剥掉
/// 机话比较符。

/// 匹配「{标题} >= {数字或时间}{unit 枚举}」的旧机话拼接。
/// threshold 允许整数/小数/时间（07:00）；unit 允许空或英文字母串。
final RegExp _machineCriterionPattern =
    RegExp(r'^(?<=^)(?<title>.+?)\s*>=\s*(?<threshold>[0-9]+(?:\.[0-9]+)?|[0-9]{1,2}:[0-9]{2})\s*(?<unit>[A-Za-z]*)(?=$)');

/// 尝试把旧机器拼接的达标线翻成人话；不是机器格式时返回 null（保持原文）。
String? humanizeCriterionLabel(String raw, AppLocalizations l10n) {
  final match = _machineCriterionPattern.firstMatch(raw.trim());
  if (match == null) {
    return null;
  }
  final title = match.namedGroup('title')!.trim();
  final threshold = match.namedGroup('threshold')!;
  final unit = (match.namedGroup('unit') ?? '').toLowerCase();
  if (title.isEmpty) {
    return null;
  }
  switch (unit) {
    case 'boolean':
      // 枚举型达标线：整句模板（与引擎侧模板对齐，SPEC DL §6.4）。
      return l10n.displayCriterionCompleteTemplate(title);
    case 'percent':
      // 「%」紧贴数字，走独立模板避免双空格。
      return l10n.displayCriterionAtLeastTemplate(title, '$threshold%');
    case 'count':
      return l10n.displayCriterionAtLeastUnitTemplate(
        title,
        threshold,
        l10n.displayUnitTimes,
      );
    case 'days':
      return l10n.displayCriterionAtLeastUnitTemplate(
        title,
        threshold,
        l10n.displayUnitDays,
      );
    case 'time':
    case '':
      // time 的 threshold 本身可读；空 unit 说明机器拼了个未知空枚举。
      return l10n.displayCriterionAtLeastTemplate(title, threshold);
    default:
      // 未知 unit 枚举不直出，但也不能凭空捏语义：只保留可读的数值部分。
      return l10n.displayCriterionAtLeastTemplate(title, threshold);
  }
}
