import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_card_carousel.dart';

void main() {
  test('dashboard defaults place insights before calendar and tools', () {
    final defaults = DashboardCardConfigState.defaults();

    expect(
      defaults.visibleOrderedCards.take(3).toList(),
      <String>[
        DashboardCardIds.insights,
        DashboardCardIds.calendar,
        DashboardCardIds.tools,
      ],
    );
  });

  testWidgets('dashboard carousel starts from preferred initial card',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            height: 240,
            child: DashboardCardCarousel(
              cards: <Widget>[
                Card(child: Center(child: Text('insights'))),
                Card(child: Center(child: Text('calendar'))),
                Card(child: Center(child: Text('tools'))),
              ],
              cardIds: <String>[
                DashboardCardIds.insights,
                DashboardCardIds.calendar,
                DashboardCardIds.tools,
              ],
              preferredInitialCardId: DashboardCardIds.calendar,
            ),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    final activeSize = tester.getSize(
      find.byKey(const ValueKey('dashboard-carousel-indicator-1')),
    );
    final inactiveSize = tester.getSize(
      find.byKey(const ValueKey('dashboard-carousel-indicator-0')),
    );

    expect(activeSize.width, greaterThan(inactiveSize.width));
  });
}
