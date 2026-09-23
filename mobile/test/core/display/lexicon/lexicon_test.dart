import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/display/lexicon/criterion_lexicon.dart';
import 'package:sparkle/core/display/lexicon/date_formatting.dart';
import 'package:sparkle/core/display/lexicon/goal_status_lexicon.dart';
import 'package:sparkle/core/display/lexicon/lexicon.dart';
import 'package:sparkle/core/display/lexicon/memory_event_lexicon.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// B1-B / S2 数据词典测试（AUDIT S2 / SPEC DL §6.4）：
/// 断言 enum→人话、机话达标线兜底、事件动词翻译、时间格式化无毫秒。
void main() {
  final AppLocalizations zh = AppLocalizationsZh();
  final AppLocalizations en = AppLocalizationsEn();

  group('例3 goal status/priority 词典', () {
    test('goal.status active/normal 类枚举翻成中文', () {
      expect(goalStatusLabel(zh, 'active'), '进行中');
      expect(goalStatusLabel(zh, 'paused'), '已暂停');
      expect(goalStatusLabel(zh, 'completed'), '已完成');
      expect(goalStatusLabel(zh, 'draft'), '草稿');
      expect(goalStatusLabel(zh, 'archived'), '已归档');
      expect(goalStatusLabel(zh, 'cancelled'), '已取消');
    });

    test('goal.priority normal 翻成「普通」', () {
      expect(goalPriorityLabel(zh, 'normal'), '普通');
      expect(goalPriorityLabel(zh, 'high'), '高');
      expect(goalPriorityLabel(zh, 'low'), '低');
      expect(goalPriorityLabel(zh, 'critical'), '紧急');
    });

    test('en locale 输出英文人话', () {
      expect(goalStatusLabel(en, 'active'), 'Active');
      expect(goalPriorityLabel(en, 'normal'), 'Normal');
    });

    test('未收录枚举返回 null（调用方回退原值，不猜测语义）', () {
      expect(goalStatusLabel(zh, 'mystery'), isNull);
      expect(goalPriorityLabel(en, 'mystery'), isNull);
    });
  });

  group('例4 memory 记录状态词典', () {
    test('derive_status 全值域人话化', () {
      expect(memoryRecordStatusLabel(zh, 'active'), '生效中');
      expect(memoryRecordStatusLabel(zh, 'completed'), '已达成');
      expect(memoryRecordStatusLabel(zh, 'archived'), '已归档');
      expect(memoryRecordStatusLabel(zh, 'expired'), '已过期');
      expect(memoryRecordStatusLabel(zh, 'revoked'), '已删除');
      expect(memoryRecordStatusLabel(zh, 'superseded'), '已更新');
      expect(memoryRecordStatusLabel(zh, 'retracted'), '已撤回');
      expect(memoryRecordStatusLabel(zh, 'resolved'), '已解决');
    });

    test('未收录返回 null', () {
      expect(memoryRecordStatusLabel(zh, 'whatever'), isNull);
    });
  });

  group('例4 memory 事件动词词典', () {
    test('「completed X」翻成「已完成「X」」', () {
      expect(
        humanizeMemoryEvent('completed 剑桥真题一套', zh),
        '已完成「剑桥真题一套」',
      );
      expect(
        humanizeMemoryEvent('Finished chapter 3', en),
        'Finished "chapter 3"',
      );
    });

    test('reviewed/practiced/mastered 动词族', () {
      expect(humanizeMemoryEvent('reviewed 错题本', zh), '已复盘「错题本」');
      expect(humanizeMemoryEvent('practiced 听力', zh), '已练习「听力」');
      expect(humanizeMemoryEvent('mastered 图论', zh), '已掌握「图论」');
    });

    test('非事件文本原样返回（不破坏用户自己的内容）', () {
      expect(humanizeMemoryEvent('今天完成了三套真题', zh), '今天完成了三套真题');
      expect(humanizeMemoryEvent('a plain note', zh), 'a plain note');
    });
  });

  group('例1 达标线机话兜底词典', () {
    test('「X >= 1boolean」翻成整句达标话术（AUDIT S2 原始反例）', () {
      expect(
        humanizeCriterionLabel('图论概念梳理完成 >= 1boolean', zh),
        '完成「图论概念梳理完成」即达标',
      );
      expect(
        humanizeCriterionLabel('Graph review >= 1boolean', en),
        'Complete "Graph review" to meet the bar',
      );
    });

    test('数值 unit 兜底映射', () {
      expect(
        humanizeCriterionLabel('错题重做 >= 3count', zh),
        '错题重做 ≥ 3 次',
      );
      expect(
        humanizeCriterionLabel('连续打卡 >= 30days', zh),
        '连续打卡 ≥ 30 天',
      );
      expect(
        humanizeCriterionLabel('exam_score >= 90percent', zh),
        'exam_score ≥ 90%',
      );
    });

    test('未知 unit 不直出英文枚举', () {
      final out = humanizeCriterionLabel('练习 >= 1weird', zh);
      expect(out, '练习 ≥ 1');
      expect(out!.contains('weird'), isFalse);
    });

    test('非机器格式返回 null（保持原文）', () {
      expect(humanizeCriterionLabel('核心科目达到目标分数线', zh), isNull);
      expect(humanizeCriterionLabel('完成「X」即达标', zh), isNull);
    });
  });

  group('例2 时间格式化唯一入口', () {
    DateTime _daysFromNow(int days, {int hour = 15, int minute = 0}) {
      final now = DateTime.now();
      return DateTime(now.year, now.month, now.day + days, hour, minute);
    }

    test('禁毫秒：任何输出不含毫秒尾巴', () {
      final out = formatSparkleDateTime(
        DateTime.parse('2026-09-20 15:00:00.000'),
        zh,
      );
      expect(out.contains('.000'), isFalse);
      expect(out.contains('000Z'), isFalse);
    });

    test('相对优先：今天/明天/昨天', () {
      expect(formatSparkleDateTime(_daysFromNow(0), zh), '今天 15:00');
      expect(formatSparkleDateTime(_daysFromNow(1), zh), '明天 15:00');
      expect(formatSparkleDateTime(_daysFromNow(-1), zh), '昨天 15:00');
      expect(formatSparkleDateTime(_daysFromNow(0), en), 'Today 15:00');
    });

    test('7 天内相对，≥7 天落绝对', () {
      expect(formatSparkleDateTime(_daysFromNow(3), zh), '3天后 15:00');
      expect(formatSparkleDateTime(_daysFromNow(-6), zh), '6天前 15:00');
      final out = formatSparkleDateTime(
        _daysFromNow(-30, hour: 9, minute: 30),
        zh,
      );
      // ≥7 天落绝对：不再出现「天前/天后」相对词，钟点保留且无毫秒。
      expect(out.contains('天前'), isFalse);
      expect(out.endsWith('09:30'), isTrue);
      final absolute = formatSparkleDateTime(
        DateTime(2020, 1, 5, 15, 0),
        zh,
      );
      expect(absolute.contains('1月5日'), isTrue);
      final absoluteEn = formatSparkleDateTime(
        DateTime(2020, 1, 5, 15, 0),
        en,
      );
      expect(absoluteEn, '1/5 15:00');
    });

    test('同点起止 Range 折叠为单点（X8）', () {
      final start = _daysFromNow(0, hour: 13, minute: 59);
      final end = _daysFromNow(0, hour: 13, minute: 59);
      final out = formatSparkleSceneRange(start, end, zh);
      expect(out, '今天 13:59');
      expect('-'.allMatches(out), isEmpty);
    });

    test('同日不同点只标一次日期', () {
      final start = _daysFromNow(0, hour: 13, minute: 0);
      final end = _daysFromNow(0, hour: 15, minute: 0);
      expect(formatSparkleSceneRange(start, end, zh), '今天 13:00 - 15:00');
    });
  });

  group('PHOTON #7 日期分组头唯一入口 formatSparkleDayHeader', () {
    DateTime _daysFromNow(int days, {int hour = 15, int minute = 0}) {
      final now = DateTime.now();
      return DateTime(now.year, now.month, now.day + days, hour, minute);
    }

    test('今天/昨天/N天前（无时钟，纯日粒度）', () {
      expect(formatSparkleDayHeader(_daysFromNow(0), zh), '今天');
      expect(formatSparkleDayHeader(_daysFromNow(-1), zh), '昨天');
      expect(formatSparkleDayHeader(_daysFromNow(-2), zh), '2天前');
      expect(formatSparkleDayHeader(_daysFromNow(-6), zh), '6天前');
      expect(formatSparkleDayHeader(_daysFromNow(-1), en), 'Yesterday');
    });

    test('≥7 天落纯日期绝对格式（无时钟、无相对词）', () {
      final out = formatSparkleDayHeader(_daysFromNow(-30), zh);
      expect(out.contains('天前'), isFalse);
      expect(out.contains(':'), isFalse); // 分组头不带钟点
      expect(formatSparkleDayHeader(DateTime(2020, 1, 5), zh), '1月5日');
      expect(formatSparkleDayHeader(DateTime(2020, 1, 5), en), '1/5');
    });

    test('formatSparkleClock 零点填充无毫秒', () {
      expect(formatSparkleClock(DateTime(2026, 9, 22, 9, 5)), '09:05');
      expect(
        formatSparkleClock(DateTime.parse('2026-09-22 09:05:00.000')),
        '09:05',
      );
    });
  });

  group('§6.3 数字准入三档 band', () {
    test('场景质量与前瞻置信度走三档人话，不出小数', () {
      String sceneBand(double v) => bandLabel(
            v,
            zh,
            high: (l10n) => l10n.displaySceneQualityHigh,
            mid: (l10n) => l10n.displaySceneQualityMid,
            low: (l10n) => l10n.displaySceneQualityLow,
          );
      expect(sceneBand(0.85), '高质量');
      expect(sceneBand(0.60), '质量不错');
      expect(sceneBand(0.30), '还在积累');

      String foresightBand(double v) => bandLabel(
            v,
            zh,
            high: (l10n) => l10n.displayForesightConfident,
            mid: (l10n) => l10n.displayForesightVerifying,
            low: (l10n) => l10n.displayForesightUnsure,
          );
      expect(foresightBand(0.80), '比较有把握');
      expect(foresightBand(0.55), '还在确认，供你参考');
      expect(foresightBand(0.20), '这部分我不确定');
    });
  });
}
