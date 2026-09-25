import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/presentation/widgets/task_list_widget.dart';

import '../../../../shared/i18n_test_helper.dart';

/// 卡 R2-C（H4）红测：task_list 状态/类型 chip 归一化。
///
/// 后端格式真源 backend/app/tools/task_query_tool.py:141-143 经
/// `task.type.value` / `task.status.value` 原样下发大写枚举串
/// （backend/app/models/task.py:37-56），历史实现只匹配小写 case，
/// 大写输入全部落入 default（chip 显示原始大写串 + brandPrimary 色，
/// 图标落 task_alt），且 PAUSED/STUCK 即使小写也无 case。
///
/// 走 chip 回退行的确定性方式：`id: ''` 使 taskModelFromEntityPayload
/// 返回 null（entity_card_payloads.dart 空 id 早退），行渲染
/// _buildTaskIcon + _buildStatusChip。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  Future<void> pumpTaskList(
    WidgetTester tester,
    Map<String, dynamic> task,
  ) async {
    await tester.pumpWidget(
      // 行内 SparkleIconButton 是 ConsumerWidget（watch 主题令牌），
      // 没有 ProviderScope 直接 StateError——不是被测行为的一部分。
      ProviderScope(
        child: testMaterialApp(
          theme: AppThemes.lightTheme,
          home: Scaffold(
            body: SingleChildScrollView(
              child: TaskListWidget(tasks: [task]),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
  }

  Future<TextStyle?> chipTextStyle(WidgetTester tester, String label) async {
    final text = tester.widget<Text>(find.text(label));
    return text.style;
  }

  testWidgets(
    'uppercase COMPLETED/LEARNING hits completed style (success color + l10n text), not default',
    (tester) async {
      await pumpTaskList(tester, {
        'id': '',
        'title': '复习英语单词',
        'type': 'LEARNING',
        'status': 'COMPLETED',
      });

      // 类型图标命中 learning case（menu_book）而非 default 的 task_alt。
      expect(find.byIcon(Icons.menu_book), findsOneWidget);
      expect(find.byIcon(Icons.task_alt), findsNothing);

      // 状态 chip 命中 completed case：l10n 文案 + success 色，
      // 而非 default 的原始大写串 'COMPLETED' + brandPrimary。
      expect(find.text('COMPLETED'), findsNothing);
      final style = await chipTextStyle(tester, '已完成');
      expect(style?.color, DS.success);
    },
  );

  testWidgets(
    'uppercase PAUSED renders localized paused chip with warning color',
    (tester) async {
      await pumpTaskList(tester, {
        'id': '',
        'title': '等审阅反馈的作文任务',
        'type': 'REFLECTION',
        'status': 'PAUSED',
      });

      expect(find.text('PAUSED'), findsNothing);
      final style = await chipTextStyle(tester, '已暂停');
      expect(style?.color, DS.warning);
    },
  );

  testWidgets(
    'uppercase STUCK renders localized stuck chip with warning color',
    (tester) async {
      await pumpTaskList(tester, {
        'id': '',
        'title': '反复出错的数学题',
        'type': 'ERROR_FIX',
        'status': 'STUCK',
      });

      expect(find.text('STUCK'), findsNothing);
      final style = await chipTextStyle(tester, '卡住了');
      expect(style?.color, DS.warning);
    },
  );
}
