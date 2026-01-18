import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/offline/sync_center_provider.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/features/user/presentation/screens/sync_center_screen.dart';

void main() {
  testWidgets('SyncCenterScreen shows stats and retry button', (tester) async {
    final fakeStats = SyncCenterStats(
      pendingByTopic: {'cognitive': 2, 'knowledge': 1},
      totalPending: 3,
      lastSuccessAt: DateTime(2025, 1, 1, 12, 0, 0),
    );

    final streamController = StreamController<SyncCenterStats>()..add(fakeStats);
    final itemsController = StreamController<List<OutboxItem>>()
      ..add(<OutboxItem>[]);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          syncCenterStatsProvider.overrideWith((ref) => streamController.stream),
          syncCenterItemsProvider.overrideWith(
            (ref, query) => itemsController.stream,
          ),
        ],
        child: const MaterialApp(
          home: SyncCenterScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('待同步总数: 3'), findsOneWidget);
    expect(find.text('认知碎片'), findsOneWidget);
    expect(find.text('知识图谱'), findsOneWidget);
    expect(find.text('Retry failed'), findsOneWidget);

    await streamController.close();
    await itemsController.close();
  });
}
