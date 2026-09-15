import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/widgets/sparkle_motion_primitives.dart';

void main() {
  testWidgets('SparkleAttentionPulse builds', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SparkleAttentionPulse(
            active: true,
            child: SizedBox(width: 100, height: 100),
          ),
        ),
      ),
    );
    expect(find.byType(SparkleAttentionPulse), findsOneWidget);
  });
}
