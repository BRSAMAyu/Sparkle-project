import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';

void main() {
  setUp(() {
    I18nService.instance.updateLocale(const Locale('en'), AppLocalizationsEn());
  });

  tearDown(I18nService.instance.reset);

  testWidgets('cancel returns null even after the user typed text', (
    tester,
  ) async {
    String? result = 'not-opened';

    await tester
        .pumpWidget(_DialogHarness(onResult: (value) => result = value));

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'This should not be sent');
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();

    expect(result, isNull);
  });

  testWidgets('submit returns trimmed freeform text', (tester) async {
    String? result;

    await tester
        .pumpWidget(_DialogHarness(onResult: (value) => result = value));

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), '  I was sick today  ');
    await tester.tap(find.text('Send'));
    await tester.pumpAndSettle();

    expect(result, 'I was sick today');
  });
}

class _DialogHarness extends StatelessWidget {
  const _DialogHarness({required this.onResult});

  final ValueChanged<String?> onResult;

  // U-03 harness repair：挂 l10n delegates——对话框源码用
  // AppLocalizations.of(context)!，无 delegates 时构建即空指针。
  @override
  Widget build(BuildContext context) => MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (context) => Scaffold(
            body: Center(
              child: ElevatedButton(
                onPressed: () async {
                  final result =
                      await showAuroraFreeformCorrectionInputDialog(context);
                  onResult(result);
                },
                child: const Text('Open'),
              ),
            ),
          ),
        ),
      );
}
