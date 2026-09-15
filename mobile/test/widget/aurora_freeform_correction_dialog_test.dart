import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
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

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
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
}
