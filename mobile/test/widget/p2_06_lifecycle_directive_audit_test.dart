import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/insights/data/models/directive_audit_entry.dart';
import 'package:sparkle/features/insights/presentation/screens/directive_audit_screen.dart';
import 'package:sparkle/features/task/presentation/widgets/source_lifecycle_badge.dart';
import 'package:sparkle/l10n/app_localizations_en.dart';
import 'package:sparkle/shared/entities/task_model.dart';

void main() {
  setUp(() {
    I18nService.instance.updateLocale(
      const Locale('en'),
      AppLocalizationsEn(),
    );
  });

  testWidgets('SourceLifecycleBadge renders revoked source and action',
      (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        theme: AppThemes.lightTheme,
        home: Scaffold(
          body: SourceLifecycleBadge(
            source: const SourceAssetBinding(
              id: 'src-1',
              title: 'Lecture PDF',
              lifecycleStatus: SourceLifecycleStatus.revoked,
            ),
            onReselectSource: () => tapped = true,
          ),
        ),
      ),
    );

    expect(find.text('Source Revoked'), findsOneWidget);
    expect(find.text('Lecture PDF'), findsOneWidget);
    expect(find.text('Choose Again'), findsOneWidget);

    await tester.tap(find.text('Choose Again'));
    expect(tapped, isTrue);
  });

  testWidgets('DirectiveAuditTimeline renders directive signal and policy',
      (tester) async {
    final entry = DirectiveAuditEntry(
      traceId: 'trace-1',
      directiveId: 'nd-1',
      directiveType: 'NotificationDirective',
      displayType: 'NotifyUser',
      createdAt: DateTime(2026, 5, 2, 9, 30),
      targetModule: 'notification_service',
      scope: 'today',
      userVisibleReason: 'First task has not started yet.',
      triggerSignal: const {
        'claim': 'morning task untouched',
      },
      policy: const {
        'primary_strategy': 'recover_execution_rhythm',
      },
      actualResult: const {
        'applied': true,
      },
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppThemes.lightTheme,
        home: Scaffold(
          body: SingleChildScrollView(
            child: DirectiveAuditTimeline(entries: [entry]),
          ),
        ),
      ),
    );

    expect(find.text('NotifyUser'), findsOneWidget);
    expect(find.text('First task has not started yet.'), findsOneWidget);
    expect(find.text('morning task untouched'), findsOneWidget);
    expect(find.text('recover_execution_rhythm'), findsOneWidget);
    expect(find.text('Applied'), findsOneWidget);
  });
}
