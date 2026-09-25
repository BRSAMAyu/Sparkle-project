import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/unified_notification_card.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/l10n/app_localizations_zh.dart';
import '../../../../shared/i18n_test_helper.dart';

UnifiedNotification _suggestion() => UnifiedNotification.fromJson({
      'id': 'sugg-card-1',
      'source_type': 'system',
      'title': '你的学习计划状态',
      'content': '距离「计算机网络」目标截止还有 3 天。',
      'type': 'comeback_nudge',
      'priority': 'medium',
      'is_read': false,
      'created_at': DateTime(2026, 9, 25, 9).toIso8601String(),
      'metadata': {
        'suggestion_type': 'comeback_nudge',
        'why_now': '距离「计算机网络」目标截止还有 3 天；任务账本 1/4。',
        'suggested_action': '先开一个「30分钟保底版」，把「TCP 流量控制」推进到一个最小闭环。',
        'destination_route': '/goals/goal-9?source=comeback_nudge',
      },
    });

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('proactive suggestion card renders the four elements', (tester) async {
    var ignoreTapped = false;
    var muteTapped = false;

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: UnifiedNotificationCard(
              notification: _suggestion(),
              onRead: () {},
              onDelete: () {},
              onSuggestionIgnoreToday: () => ignoreTapped = true,
              onSuggestionMuteType: () => muteTapped = true,
            ),
          ),
        ),
      ),
    );

    // 要素 1：why now —— 标签 + 事实性解释文本。
    expect(find.text('为什么是现在'), findsOneWidget);
    expect(find.text('距离「计算机网络」目标截止还有 3 天；任务账本 1/4。'), findsOneWidget);

    // 要素 2：suggested action —— 标签 + 建议动作文本。
    expect(find.text('建议的一步'), findsOneWidget);
    expect(find.textContaining('30分钟保底版'), findsWidgets);

    // 要素 3/4：today ignore / mute this type 入口。
    expect(find.text('今天不再看'), findsOneWidget);
    expect(find.text('不再提醒此类建议'), findsOneWidget);

    await tester.tap(find.text('今天不再看'));
    await tester.pumpAndSettle();
    expect(ignoreTapped, isTrue);

    await tester.tap(find.text('不再提醒此类建议'));
    await tester.pumpAndSettle();
    expect(muteTapped, isTrue);
  });

  testWidgets('plain system notification does not grow suggestion entries',
      (tester) async {
    final plain = UnifiedNotification.fromJson({
      'id': 'sys-plain',
      'source_type': 'system',
      'title': '系统通知',
      'content': '设置已更新。',
      'type': 'settings_updated',
      'is_read': false,
      'created_at': DateTime(2026, 9, 25, 9).toIso8601String(),
    });

    await tester.pumpWidget(
      testMaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: UnifiedNotificationCard(
              notification: plain,
              onRead: () {},
              onDelete: () {},
            ),
          ),
        ),
      ),
    );

    expect(find.text('为什么是现在'), findsNothing);
    expect(find.text('今天不再看'), findsNothing);
    expect(find.text('不再提醒此类建议'), findsNothing);
  });

  test('P-03 suggestion copy is guilt-free in zh and en (PRODUCT_LANGUAGE 红线)', () {
    const zhGuiltTerms = [
      '懒', '落后', '拖后腿', '堕落', '荒废', '浪费', '太差', '失败',
      '你怎么', '辜负', '失望', '别人都', '羞耻', '丢人', '还来得及', '等你好久了',
    ];
    const enGuiltTerms = [
      'lazy', 'fall behind', 'failure', 'disappoint', 'ashamed',
      'blame you', 'guilt', 'shame', "you've been gone",
    ];

    void assertGuiltFree(String text, List<String> terms) {
      for (final term in terms) {
        expect(
          text.toLowerCase().contains(term.toLowerCase()),
          isFalse,
          reason: 'guilt term "$term" must not appear in suggestion copy: $text',
        );
      }
    }

    final zh = AppLocalizationsZh();
    final en = AppLocalizationsEn();

    for (final text in [
      zh.notificationSuggestionWhyNowTitle,
      zh.notificationSuggestionActionTitle,
      zh.notificationSuggestionIgnoreToday,
      zh.notificationSuggestionMuteType,
      zh.notificationSuggestionIgnoredToast,
      zh.notificationSuggestionMutedToast,
    ]) {
      assertGuiltFree(text, zhGuiltTerms);
    }

    for (final text in [
      en.notificationSuggestionWhyNowTitle,
      en.notificationSuggestionActionTitle,
      en.notificationSuggestionIgnoreToday,
      en.notificationSuggestionMuteType,
      en.notificationSuggestionIgnoredToast,
      en.notificationSuggestionMutedToast,
    ]) {
      assertGuiltFree(text, enGuiltTerms);
    }
  });
}
