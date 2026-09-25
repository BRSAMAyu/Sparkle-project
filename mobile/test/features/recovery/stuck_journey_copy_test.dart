import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';

/// J-05 ·「我卡住了」恢复旅程文案红线（PRODUCT_LANGUAGE）：
/// 全部新增 stuckJourney/stuckHelpJourneyCta 词条零 guilt/零诊断式表述。
/// 词表复用 P-03 红线口径（proactive_suggestion_card_test）并按恢复场景
/// 补压力话术（还来得及/等你好久了/收心/自律 等敦促族）。
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

  test('stuck journey copy is guilt-free in zh and en (PRODUCT_LANGUAGE 红线)',
      () {
    final zh = AppLocalizationsZh();
    final en = AppLocalizationsEn();

    final zhTexts = [
      zh.stuckJourneySheetTitle,
      zh.stuckJourneyQuestionHeader,
      zh.stuckJourneyInterventionHeader,
      zh.stuckJourneyUncertainHint,
      zh.stuckJourneyNotThisReason,
      zh.stuckJourneyTryIt,
      zh.stuckJourneyCorrectedAck,
      zh.stuckJourneyLoadFailed,
      zh.stuckJourneyRetry,
      zh.stuckJourneyChatPrompt('线代第三章', '把这一步拆成更小的几步'),
      zh.stuckJourneyContextTask('特征值练习'),
      zh.stuckJourneyContextGoal('线代一轮复习'),
      zh.stuckJourneyContextFailures(3),
      zh.stuckJourneyContextStalled(6),
      zh.stuckJourneyInterventionRescope,
      zh.stuckJourneyInterventionSplit,
      zh.stuckJourneyInterventionClarify,
      zh.stuckJourneyInterventionExplain,
      zh.stuckJourneyInterventionRetrieve,
      zh.stuckJourneyInterventionPractice,
      zh.stuckJourneyInterventionSchedule,
      zh.stuckJourneyInterventionPause,
      zh.stuckJourneyInterventionRemind,
      zh.stuckJourneyInterventionReflect,
      zh.stuckJourneyInterventionReview,
      zh.stuckJourneyInterventionConnectPeer,
      zh.stuckJourneyInterventionDelegate,
      zh.stuckJourneyInterventionCoExecute,
      zh.stuckHelpJourneyCta,
    ];

    final enTexts = [
      en.stuckJourneySheetTitle,
      en.stuckJourneyQuestionHeader,
      en.stuckJourneyInterventionHeader,
      en.stuckJourneyUncertainHint,
      en.stuckJourneyNotThisReason,
      en.stuckJourneyTryIt,
      en.stuckJourneyCorrectedAck,
      en.stuckJourneyLoadFailed,
      en.stuckJourneyRetry,
      en.stuckJourneyChatPrompt('Linear algebra ch.3', 'Break this step into smaller pieces'),
      en.stuckJourneyContextTask('Eigenvalue drills'),
      en.stuckJourneyContextGoal('Linear algebra review'),
      en.stuckJourneyContextFailures(3),
      en.stuckJourneyContextStalled(6),
      en.stuckJourneyInterventionRescope,
      en.stuckJourneyInterventionSplit,
      en.stuckJourneyInterventionClarify,
      en.stuckJourneyInterventionExplain,
      en.stuckJourneyInterventionRetrieve,
      en.stuckJourneyInterventionPractice,
      en.stuckJourneyInterventionSchedule,
      en.stuckJourneyInterventionPause,
      en.stuckJourneyInterventionRemind,
      en.stuckJourneyInterventionReflect,
      en.stuckJourneyInterventionReview,
      en.stuckJourneyInterventionConnectPeer,
      en.stuckJourneyInterventionDelegate,
      en.stuckJourneyInterventionCoExecute,
      en.stuckHelpJourneyCta,
    ];

    for (final text in zhTexts) {
      assertGuiltFree(text, zhGuiltTerms, 'zh');
    }
    for (final text in enTexts) {
      assertGuiltFree(text, enGuiltTerms, 'en');
    }
  });
}
