import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/presentation/widgets/seed_item_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

Widget _wrap(SeedItem item) => MaterialApp(
      locale: const Locale('zh'),
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: SeedItemCard(item: item),
      ),
    );

SeedItem _item({String? content, Map<String, dynamic>? contentData}) => SeedItem(
      id: 'item-1',
      libraryId: 'lib-1',
      itemType: ItemType.flashcard,
      isActive: true,
      createdAt: DateTime.fromMillisecondsSinceEpoch(0),
      updatedAt: DateTime.fromMillisecondsSinceEpoch(0),
      title: 'Python 列表推导式闪卡',
      content: content,
      contentData: contentData,
    );

void main() {
  testWidgets('空壳条目（content 为空）显示空态占位而非空白', (tester) async {
    await tester.pumpWidget(_wrap(_item()));
    await tester.pump();

    expect(find.text('暂无内容'), findsOneWidget);
  });

  testWidgets('空白字符串 content 同样触发空态占位', (tester) async {
    await tester.pumpWidget(_wrap(_item(content: '   ')));
    await tester.pump();

    expect(find.text('暂无内容'), findsOneWidget);
    expect(find.byType(SparkleMarkdown), findsNothing);
  });

  testWidgets('有正文的条目渲染 Markdown 且不显示空态占位', (tester) async {
    await tester.pumpWidget(
      _wrap(_item(content: '**答案：** squared = [x**2 for x in numbers]')),
    );
    await tester.pump();

    expect(find.byType(SparkleMarkdown), findsOneWidget);
    expect(find.text('暂无内容'), findsNothing);
  });
}
