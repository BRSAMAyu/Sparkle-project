import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

void main() {
  testWidgets('preview card exposes launch prediction action', (tester) async {
    var launched = false;

    final node = GalaxyNodeModel(
      id: 'python-node',
      name: 'Python 编程',
      importance: 3,
      sector: SectorEnum.tech,
      isUnlocked: true,
      masteryScore: 68,
      description: '适合从语法、项目和生态三层逐步进入。',
    );

    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('zh'),
        localizationsDelegates: const <LocalizationsDelegate<dynamic>>[
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: Center(
            child: GalaxyNodePreviewCard(
              node: node,
              onFocus: () {},
              onInspectConnections: () {},
              onViewDetails: () {},
              onLaunchPrediction: () => launched = true,
            ),
          ),
        ),
      ),
    );

    expect(find.text('推演此节点'), findsOneWidget);

    await tester.tap(find.text('推演此节点'));
    await tester.pump();

    expect(launched, isTrue);
  });
}
