import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/app_permission_dialog.dart';
import 'package:sparkle/core/statistics/domain/entities/statistics_period.dart';
import 'package:sparkle/core/statistics/domain/services/statistics_export_service.dart';
import 'package:sparkle/core/statistics/presentation/widgets/common/statistics_overview_cards.dart';
import 'package:sparkle/core/statistics/presentation/widgets/common/statistics_period_toggle.dart';
import 'package:sparkle/core/statistics/presentation/widgets/export/statistics_export_bottom_sheet.dart';
import 'package:sparkle/features/community/data/models/community_models.dart';
import 'package:sparkle/features/community/presentation/widgets/feed_post_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_switch_confirmation_dialog.dart';
import 'package:sparkle/features/focus/presentation/widgets/exit_confirmation_dialog.dart';
import 'package:sparkle/features/home/presentation/widgets/thought_capsule_dialog.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/notification_filter_chip.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/unified_notification_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

void main() {
  group('overflow regression', () {
    testWidgets('permission dialog stays stable on a compact screen',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: Builder(
          builder: (context) => Center(
            child: ElevatedButton(
              onPressed: () => showAppPermissionDialog(
                context,
                permission: AppPermissionKind.photos,
              ),
              child: const Text('open'),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pumpAndSettle();

      expect(find.text('需要相册权限'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('plan switch dialog avoids overflow on compact width',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: const Center(
          child: PlanSwitchConfirmationDialog(
            targetPlanName: '一个很长很长很长的学习计划名称，用来验证紧凑宽度下的安全布局',
            unsavedMessageCount: 12,
            onConfirm: _noop,
            onCancel: _noop,
          ),
        ),
      );

      await tester.pump(const Duration(milliseconds: 500));

      expect(find.byType(PlanSwitchConfirmationDialog), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('thought capsule dialog remains scrollable and visible',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: const Center(child: ThoughtCapsuleDialog()),
      );

      await tester.pumpAndSettle();

      expect(find.byType(TextField), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('exit confirmation dialog stacks actions when space is tight',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: const ExitConfirmationDialog(
          elapsedMinutes: 128,
          onConfirmExit: _noop,
          onCancel: _noop,
        ),
      );

      await tester.pump(const Duration(milliseconds: 300));

      expect(find.byType(ExitConfirmationDialog), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('statistics export sheet keeps export button reachable',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: Builder(
          builder: (context) => Center(
            child: ElevatedButton(
              onPressed: () => StatisticsExportBottomSheet.show(
                context: context,
                availableFormats: const [
                  ExportFormat.json,
                  ExportFormat.csv,
                  ExportFormat.pngReport,
                  ExportFormat.pdfReport,
                ],
                onExport: (_) async {},
              ),
              child: const Text('open export'),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open export'));
      await tester.pumpAndSettle();

      expect(find.textContaining('导出为'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('statistics share sheet adapts dense options without overflow',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: SizedBox.expand(
          child: Align(
            alignment: Alignment.bottomCenter,
            child: SizedBox(
              width: double.infinity,
              child: StatisticsShareBottomSheet(
                options: [
                  for (var i = 0; i < 8; i++)
                    ShareOption(
                      id: 'option-$i',
                      label: '分享渠道 $i 超长标签',
                      icon: Icons.share_outlined,
                      color: Colors.blue,
                      action: () async {},
                    ),
                ],
                onShare: (_) async {},
              ),
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.textContaining('分享渠道 0'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('statistics overview cards handle long titles on compact width',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: StatisticsOverviewCards(
          cards: const [
            OverviewCardData(
              id: 'card-1',
              title: '超长统计标题用于验证紧凑布局下不会横向或纵向溢出',
              value: '12888',
              unit: '分钟',
              changePercentage: 18.6,
            ),
            OverviewCardData(
              id: 'card-2',
              title: '另一个超长标题用于验证自动换行和压缩策略',
              value: '999999',
              unit: '次',
              changePercentage: -7.5,
            ),
          ],
        ),
      );

      await tester.pumpAndSettle();

      expect(find.textContaining('超长统计标题'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('notification card keeps long content and badge stable',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: UnifiedNotificationCard(
          notification: UnifiedNotification(
            id: 'notif-1',
            sourceType: 'intervention',
            title: '一条非常长非常长的通知标题，用来验证通知卡在窄屏下不会横向挤爆布局',
            content: '这是更长的通知正文内容，用来确认卡片正文、时间和来源徽标同时存在时依然可以稳定布局显示。',
            priority: 'high',
            isRead: false,
            createdAt: DateTime(2026, 3, 26, 12),
            type: 'intervention_push',
            metadata: const {
              'intent_type': 'micro_restart',
              'suggested_step': '先把计时器开到 5 分钟',
            },
          ),
          onRead: _noop,
          onDelete: _noop,
          onAccept: _noop,
          onAct: _noop,
          onSnooze: _noop,
        ),
      );

      await tester.pumpAndSettle();

      expect(find.textContaining('通知标题'), findsOneWidget);
      expect(find.text('试试看'), findsOneWidget);
      expect(find.text('开始'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('community feed card handles long username and topic',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: FeedPostCard(
          post: Post(
            id: 'post-1',
            userId: 'user-1',
            content: '这是一条用于验证社区动态卡片布局稳定性的内容文本。',
            createdAt: DateTime(2026, 3, 26, 8),
            user: const PostUser(
              id: 'user-1',
              username: '超长超长超长用户名用于验证社区卡片头部不会被挤爆',
            ),
            topic: '一个非常长的话题标签用于验证底部操作区布局',
            likeCount: 128,
            isOptimistic: true,
          ),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));

      expect(find.textContaining('社区动态卡片'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('statistics period toggle wraps safely on compact width',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: StatisticsPeriodToggle(
          selectedPeriod: StatisticsPeriod.week,
          showCustomOption: true,
          onPeriodChanged: (_) {},
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('本周'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('notification filter chip handles very long label',
        (tester) async {
      await _setCompactSurface(tester);
      await _pumpApp(
        tester,
        child: const Align(
          alignment: Alignment.centerLeft,
          child: NotificationFilterChip(
            label: '一个非常长非常长非常长的通知筛选标签，用于验证 chip 不会横向溢出',
            isSelected: true,
            onTap: _noop,
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.textContaining('通知筛选标签'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}

Future<void> _pumpApp(
  WidgetTester tester, {
  required Widget child,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      child: MaterialApp(
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('zh'),
        home: Scaffold(body: child),
      ),
    ),
  );
}

Future<void> _setCompactSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(320, 560));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

void _noop() {}
