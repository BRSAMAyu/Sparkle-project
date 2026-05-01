import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/attachment_picker_sheet.dart';
import 'package:sparkle/features/chat/presentation/widgets/plan_switch_confirmation_dialog.dart';

import '../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('representative chat surfaces render in dark theme', (
    tester,
  ) async {
    await tester.pumpWidget(
      testMaterialApp(
        theme: AppThemes.darkTheme,
        home: Scaffold(
          body: AttachmentPickerSheet(
            onDirectUpload: () {},
            onDocumentClean: () {},
          ),
        ),
      ),
    );

    expect(find.byType(AttachmentPickerSheet), findsOneWidget);
    expect(find.byType(Container), findsWidgets);

    await tester.pumpWidget(
      testMaterialApp(
        theme: AppThemes.darkTheme,
        home: PlanSwitchConfirmationDialog(
          targetPlanName: 'Sprint',
          unsavedMessageCount: 1,
          onConfirm: () {},
          onCancel: () {},
        ),
      ),
    );

    expect(find.byType(PlanSwitchConfirmationDialog), findsOneWidget);
  });

  test('chat feature avoids raw black and white color tokens', () {
    final chatDir = Directory('lib/features/chat');
    final offenders = <String>[];
    final rawColorPattern = RegExp(r'Colors\.(white|black)(?![A-Za-z0-9_])');

    for (final entity in chatDir.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) {
        continue;
      }
      final lines = entity.readAsLinesSync();
      for (var index = 0; index < lines.length; index++) {
        if (rawColorPattern.hasMatch(lines[index])) {
          offenders.add('${entity.path}:${index + 1}: ${lines[index].trim()}');
        }
      }
    }

    expect(
      offenders,
      isEmpty,
      reason:
          'Use DS surface/text/shadow tokens instead:\n${offenders.join('\n')}',
    );
  });
}
