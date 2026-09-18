// A-5 regression test: the register form must not overflow on the field-test
// device geometry (1080x2400 @ 2.625dpr — the Medium Phone AVD), and the
// Register button plus the "Already have an account?" link must stay
// reachable while the whole form (incl. the password strength row) is filled.
//
// Field evidence (android-round1.md A-5, screenshot 08):
//   BOTTOM OVERFLOWED BY 14 PIXELS — the yellow/black stripes covered the
//   Register button and the "Already have an account?" link. Root cause:
//   ConstrainedBox+IntrinsicHeight+Spacer pinned the Column to an
//   under-reported intrinsic height (InputDecorator intrinsic heights), so
//   the SingleChildScrollView believed nothing needed scrolling.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/presentation/screens/register_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

Future<void> _pumpRegister(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(411.43, 914.29));
  addTearDown(() => tester.binding.setSurfaceSize(null));
  tester.view.devicePixelRatio = 2.625;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      child: MaterialApp(
        locale: const Locale('en'),
        supportedLocales: const [Locale('en'), Locale('zh')],
        localizationsDelegates: const [AppLocalizations.delegate],
        home: const RegisterScreen(),
      ),
    ),
  );
  // Let the staggered entrance animations settle.
  await tester.pump(const Duration(milliseconds: 800));
  await tester.pump(const Duration(milliseconds: 800));
}

void main() {
  setUpAll(() async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    await ViewStorageService.ensureInitialized();
  });

  testWidgets(
      'filled register form shows no RenderFlex overflow and keeps the '
      'Register / has-account actions reachable on the AVD geometry',
      (tester) async {
    await _pumpRegister(tester);

    // Fill every field; the password strength row appearing on input is the
    // exact trigger of the field-test 14px overflow.
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Username').first,
      'fieldtester3',
    );
    await tester.pump();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Email').first,
      'fieldtester3@gmail.com',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Password').first,
      'Sup3rSecret!42',
    );
    await tester.pump();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Confirm Password').first,
      'Sup3rSecret!42',
    );
    await tester.pump(const Duration(milliseconds: 300));

    // Any RenderFlex overflow above this point fails the test via the
    // framework exception handler — the assertions below pin the recovery
    // path as well.

    // The two consent checkboxes must be reachable by scrolling.
    final tosCheckbox = find.byType(CheckboxListTile).first;
    await tester.scrollUntilVisible(
      tosCheckbox,
      160,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pump(const Duration(milliseconds: 300));
    await tester.tap(tosCheckbox, warnIfMissed: false);
    await tester.pump(const Duration(milliseconds: 300));

    // The Register button must exist and be hittable after scrolling to it.
    final registerButton = find.text('Register').last;
    await tester.scrollUntilVisible(
      registerButton,
      160,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pump(const Duration(milliseconds: 300));
    expect(
      registerButton,
      findsOneWidget,
      reason: 'The primary Register button must remain in the tree and be '
          'scrollable into view (A-5: it was covered by overflow stripes)',
    );
    await tester.ensureVisible(registerButton);
    await tester.pump(const Duration(milliseconds: 300));

    // The "Already have an account?" link must also remain reachable — in the
    // field test it was the bottom-most casualty of the 14px overflow.
    await tester.scrollUntilVisible(
      find.text('Already have an account?'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('Already have an account?'), findsOneWidget);
  });
}
