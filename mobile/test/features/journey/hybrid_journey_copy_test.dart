import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// J-06 · Hybrid 旗舰旅程文案红线（PRODUCT_LANGUAGE）：
/// 全部新增 hybridJourney 词条零 guilt/零诊断式表述。
/// 词表复用 P-03/J-05 红线口径（PRODUCT_LANGUAGE 零 guilt 家族）。
void main() {
  const zhGuiltTerms = [
    '懒', '落后', '拖后腿', '堕落', '荒废', '浪费', '太差', '失败',
    '你怎么', '辜负', '失望', '别人都', '羞耻', '丢人', '还来得及', '等你好久了',
    '收心', '自律', '该努力', '别再拖', '又卡', '总是卡', '诊断',
  ];
  const enGuiltTerms = [
    'lazy', 'fall behind', 'failure', 'disappoint', 'ashamed',
    'blame you', 'guilt', 'shame', "you've been gone", 'procrastinat',
    'discipline', 'you should', 'you still', 'diagnose',
  ];

  void assertGuiltFree(String text, List<String> terms, String locale) {
    for (final term in terms) {
      expect(
        text.toLowerCase().contains(term.toLowerCase()),
        isFalse,
        reason: 'guilt term "$term" must not appear in ($locale) journey copy: $text',
      );
    }
  }

  test('hybrid journey copy is guilt-free in zh and en (PRODUCT_LANGUAGE 红线)',
      () {
    final zh = AppLocalizationsZh();
    final en = AppLocalizationsEn();

    final zhTexts = [
      zh.hybridJourneySheetTitle,
      zh.hybridJourneyStagePrep,
      zh.hybridJourneyStageJudgment,
      zh.hybridJourneyStageExecuteCheck,
      zh.hybridJourneyStageOutcome,
      zh.hybridJourneyWhyHumanHeader,
      zh.hybridJourneyJudgmentWhyHuman,
      zh.hybridJourneySelectPrompt,
      zh.hybridJourneySubmitJudgment,
      zh.hybridJourneyFocusHint,
      zh.hybridJourneyCheckPassed(2),
      zh.hybridJourneyOutcomeHeader,
      zh.hybridJourneyDone(2),
      zh.hybridJourneyLoadFailed,
      zh.hybridJourneyRetry,
    ];
    final enTexts = [
      en.hybridJourneySheetTitle,
      en.hybridJourneyStagePrep,
      en.hybridJourneyStageJudgment,
      en.hybridJourneyStageExecuteCheck,
      en.hybridJourneyStageOutcome,
      en.hybridJourneyWhyHumanHeader,
      en.hybridJourneyJudgmentWhyHuman,
      en.hybridJourneySelectPrompt,
      en.hybridJourneySubmitJudgment,
      en.hybridJourneyFocusHint,
      en.hybridJourneyCheckPassed(2),
      en.hybridJourneyOutcomeHeader,
      en.hybridJourneyDone(2),
      en.hybridJourneyLoadFailed,
      en.hybridJourneyRetry,
    ];

    for (final text in zhTexts) {
      assertGuiltFree(text, zhGuiltTerms, 'zh');
    }
    for (final text in enTexts) {
      assertGuiltFree(text, enGuiltTerms, 'en');
    }
  });

  test('hybrid journey keys are bilingual and non-empty (l10n 双语零 guilt)',
      () {
    final zh = AppLocalizationsZh();
    final en = AppLocalizationsEn();

    final zhTexts = [
      zh.hybridJourneySheetTitle,
      zh.hybridJourneyJudgmentWhyHuman,
      zh.hybridJourneySelectPrompt,
      zh.hybridJourneySubmitJudgment,
    ];
    final enTexts = [
      en.hybridJourneySheetTitle,
      en.hybridJourneyJudgmentWhyHuman,
      en.hybridJourneySelectPrompt,
      en.hybridJourneySubmitJudgment,
    ];
    for (final text in zhTexts) {
      expect(text.trim(), isNotEmpty, reason: 'zh copy must exist');
    }
    for (final text in enTexts) {
      expect(text.trim(), isNotEmpty, reason: 'en copy must exist');
    }
  });
}
