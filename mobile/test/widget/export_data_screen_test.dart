import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/user/presentation/screens/export_data_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('export data screen gives visible export affordance', (
    tester,
  ) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(
          home: ExportDataScreen(),
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          locale: Locale('zh'),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('导出我的数据'), findsWidgets);
    expect(find.text('准备你的 Sparkle 数据归档'), findsOneWidget);
    expect(find.text('尚未生成导出文件'), findsOneWidget);
  });
}
