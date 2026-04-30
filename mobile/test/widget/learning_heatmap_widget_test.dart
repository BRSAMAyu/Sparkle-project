import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/presentation/widgets/learning_heatmap_widget.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  group('LearningHeatmapWidget', () {
    testWidgets('shows guided empty state when all heatmap cells are zero', (
      tester,
    ) async {
      final data = _buildHeatmapData(days: 7);

      await tester.pumpWidget(_buildHarness(data: data, days: 7));
      await tester.pumpAndSettle();

      expect(find.text('学习热力图尚未开始'), findsOneWidget);
      expect(find.text('去创建今日任务'), findsOneWidget);
    });

    testWidgets('renders stronger color for 60 minutes than 10 minutes', (
      tester,
    ) async {
      final data = _buildHeatmapData(
        days: 7,
        overrides: {
          5: const HeatmapDay(
            date: '',
            minutes: 10.0,
            tasksCompleted: 1,
          ),
          6: const HeatmapDay(
            date: '',
            minutes: 60.0,
            tasksCompleted: 3,
          ),
        },
      );

      await tester.pumpWidget(_buildHarness(data: data, days: 7));
      await tester.pumpAndSettle();

      expect(find.text('学习热力图尚未开始'), findsNothing);

      final olderDay = data[data.length - 2];
      final latestDay = data.last;

      final lightColor = _cellColorForDate(tester, olderDay.date);
      final mediumColor = _cellColorForDate(tester, latestDay.date);

      expect(mediumColor.alpha, greaterThan(lightColor.alpha));
    });

    testWidgets('renders zero-minute day as gray', (tester) async {
      final data = _buildHeatmapData(
        days: 7,
        overrides: {
          5: const HeatmapDay(
            date: '',
            minutes: 10.0,
            tasksCompleted: 1,
          ),
          6: const HeatmapDay(
            date: '',
            minutes: 0.0,
            tasksCompleted: 0,
          ),
        },
      );

      await tester.pumpWidget(_buildHarness(data: data, days: 7));
      await tester.pumpAndSettle();

      final today = data.last;
      final color = _cellColorForDate(tester, today.date);
      final expected = LearningHeatmapColor.colorForMinutes(
        0,
        brightness: Brightness.light,
      );

      expect(color, expected);
    });

    testWidgets('shows tooltip after tapping a day cell', (tester) async {
      final data = _buildHeatmapData(
        days: 7,
        overrides: {
          6: const HeatmapDay(
            date: '',
            minutes: 60.0,
            tasksCompleted: 3,
          ),
        },
      );

      await tester.pumpWidget(_buildHarness(data: data, days: 7));
      await tester.pumpAndSettle();

      final today = data.last;

      await tester.tap(
        find.byKey(
          ValueKey('learning-heatmap-cell-${today.date}'),
          skipOffstage: false,
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.byKey(
          ValueKey('learning-heatmap-tooltip-${today.date}'),
          skipOffstage: false,
        ),
        findsOneWidget,
      );
    });
  });
}

Widget _buildHarness({
  required List<HeatmapDay> data,
  required int days,
}) {
  return ProviderScope(
    child: MaterialApp(
      locale: const Locale('zh'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: Center(
          child: SizedBox(
            width: 360,
            child: LearningHeatmapWidget(
              days: days,
              data: data,
            ),
          ),
        ),
      ),
    ),
  );
}

List<HeatmapDay> _buildHeatmapData({
  required int days,
  Map<int, HeatmapDay> overrides = const {},
}) {
  final today = DateTime.now();
  final start = DateTime(
    today.year,
    today.month,
    today.day,
  ).subtract(Duration(days: days - 1));

  return List.generate(days, (index) {
    final date = start.add(Duration(days: index));
    final key =
        '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    final override = overrides[index];
    if (override != null) {
      return HeatmapDay(
        date: key,
        minutes: override.minutes,
        tasksCompleted: override.tasksCompleted,
      );
    }
    return HeatmapDay(
      date: key,
      minutes: 0,
      tasksCompleted: 0,
    );
  });
}

Color _cellColorForDate(WidgetTester tester, String date) {
  final cellFinder = find.byKey(
    ValueKey('learning-heatmap-cell-$date'),
    skipOffstage: false,
  );
  final container = tester.widget<Container>(
    find.descendant(
      of: cellFinder,
      matching: find.byWidgetPredicate(
        (widget) => widget is Container && widget.decoration is BoxDecoration,
      ),
      skipOffstage: false,
    ),
  );
  final decoration = container.decoration! as BoxDecoration;
  return decoration.color!;
}
