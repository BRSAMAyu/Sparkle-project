import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/features/error_book/data/models/error_record.dart';
import 'package:sparkle/features/error_book/presentation/widgets/error_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('ErrorCard galaxy echo', () {
    testWidgets('shows affected knowledge tag and mastery drop hint',
        (tester) async {
      await tester.pumpWidget(
        _TestHarness(
          child: ErrorCard(
            error: _buildErrorRecord(
              affectedNodeId: 'node-thermo-1',
              masteryDelta: -0.2,
              knowledgeLinks: const [
                KnowledgeLink(
                  nodeId: 'node-thermo-1',
                  nodeName: '热力学第一定律',
                  isPrimary: true,
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('热力学第一定律'), findsOneWidget);
      expect(find.byIcon(Icons.hub_outlined), findsOneWidget);
      expect(find.byIcon(Icons.trending_down_rounded), findsOneWidget);
      expect(find.text('-0.2'), findsOneWidget);
    });

    testWidgets('invokes knowledge node callback with focused node id',
        (tester) async {
      String? tappedNodeId;
      double? tappedDelta;

      await tester.pumpWidget(
        _TestHarness(
          child: ErrorCard(
            error: _buildErrorRecord(
              affectedNodeId: 'node-thermo-1',
              masteryDelta: -0.3,
              knowledgeLinks: const [
                KnowledgeLink(
                  nodeId: 'node-thermo-1',
                  nodeName: '热力学第一定律',
                  isPrimary: true,
                ),
              ],
            ),
            onKnowledgeNodeTap: (nodeId, masteryDelta) {
              tappedNodeId = nodeId;
              tappedDelta = masteryDelta;
            },
          ),
        ),
      );

      await tester.tap(find.text('热力学第一定律'));
      await tester.pump();

      expect(tappedNodeId, 'node-thermo-1');
      expect(tappedDelta, -0.3);
    });

    testWidgets(
        'falls back to primary knowledge link when affected node is null',
        (tester) async {
      await tester.pumpWidget(
        _TestHarness(
          child: ErrorCard(
            error: _buildErrorRecord(
              knowledgeLinks: const [
                KnowledgeLink(
                  nodeId: 'node-thermo-1',
                  nodeName: '热力学第一定律',
                  isPrimary: true,
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('热力学第一定律'), findsOneWidget);
    });

    testWidgets('silently hides the tag when no linked knowledge exists',
        (tester) async {
      await tester.pumpWidget(
        _TestHarness(
          child: ErrorCard(
            error: _buildErrorRecord(),
          ),
        ),
      );

      expect(find.byIcon(Icons.hub_outlined), findsNothing);
      expect(find.text('知识节点'), findsNothing);
    });
  });
}

class _TestHarness extends StatelessWidget {
  const _TestHarness({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Scaffold(
          body: Center(
            child: SizedBox(
              width: 420,
              child: child,
            ),
          ),
        ),
      );
}

ErrorRecord _buildErrorRecord({
  String? affectedNodeId,
  double? masteryDelta,
  List<KnowledgeLink> knowledgeLinks = const [],
}) {
  final now = DateTime(2026, 4, 25, 12);
  return ErrorRecord(
    id: 'error-1',
    questionText: '某系统吸收热量后内能增加多少？',
    userAnswer: '0',
    correctAnswer: '根据做功情况计算',
    subject: 'physics',
    masteryLevel: 0.42,
    reviewCount: 3,
    createdAt: now,
    updatedAt: now,
    chapter: '热学',
    affectedNodeId: affectedNodeId,
    masteryDelta: masteryDelta,
    knowledgeLinks: knowledgeLinks,
  );
}
