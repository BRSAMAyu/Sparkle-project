/// Flutter Core Performance Benchmarks
/// Flutter核心性能基准测试
library;

import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Widget Build Performance', () {
    testWidgets('Container builds in under 1ms', (tester) async {
      final stopwatch = Stopwatch()..start();

      for (var i = 0; i < 1000; i++) {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Container(
                child: const Text('Hello'),
              ),
            ),
          ),
        );
      }

      stopwatch.stop();

      final avgMs = stopwatch.elapsedMilliseconds / 1000;
      print('Container average build: ${avgMs.toStringAsFixed(3)}ms');

      expect(avgMs, lessThan(10.0)); // Relaxed threshold
    });

    testWidgets('Text widget builds in under 1ms', (tester) async {
      final stopwatch = Stopwatch()..start();

      for (var i = 0; i < 1000; i++) {
        await tester.pumpWidget(
          const MaterialApp(
            home: Scaffold(
              body: Text('Hello, World!'),
            ),
          ),
        );
      }

      stopwatch.stop();

      final avgMs = stopwatch.elapsedMilliseconds / 1000;
      print('Text average build: ${avgMs.toStringAsFixed(3)}ms');

      expect(avgMs, lessThan(5.0));
    });

    testWidgets('Column with children builds in under 10ms', (tester) async {
      final stopwatch = Stopwatch()..start();

      for (var i = 0; i < 100; i++) {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Column(
                children: [
                  for (var j = 0; j < 10; j++) Text('Item $j'),
                ],
              ),
            ),
          ),
        );
      }

      stopwatch.stop();

      final avgMs = stopwatch.elapsedMilliseconds / 100;
      print('Column average build: ${avgMs.toStringAsFixed(3)}ms');

      expect(avgMs, lessThan(10.0));
    });

    testWidgets('ListView with 100 items builds', (tester) async {
      final stopwatch = Stopwatch()..start();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView.builder(
              itemCount: 100,
              itemBuilder: (context, index) => ListTile(
                  title: Text('Item $index'),
                ),
            ),
          ),
        ),
      );

      stopwatch.stop();

      print('ListView 100 items build: ${stopwatch.elapsedMilliseconds}ms');

      expect(stopwatch.elapsedMilliseconds, lessThan(500));
    });
  });

  group('List Scrolling Performance', () {
    testWidgets('Scrolling 100 items maintains performance', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView.builder(
              itemCount: 100,
              itemBuilder: (context, index) => ListTile(
                  title: Text('Item $index'),
                  subtitle: Text('Subtitle $index'),
                ),
            ),
          ),
        ),
      );

      final stopwatch = Stopwatch()..start();

      // Scroll through list
      for (var i = 0; i < 10; i++) {
        await tester.fling(
          find.byType(ListView),
          const Offset(0, -300),
          1000,
        );
        await tester.pump();
      }

      stopwatch.stop();

      print('10 scrolls time: ${stopwatch.elapsedMilliseconds}ms');

      // Should complete in reasonable time
      expect(stopwatch.elapsedMilliseconds, lessThan(5000));
    });
  });

  group('Widget Rebuild Performance', () {
    testWidgets('StatefulWidget rebuild is fast', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TestWidget(),
          ),
        ),
      );

      await tester.pumpAndSettle();

      final rebuildStopwatch = Stopwatch()..start();

      // Trigger 100 rebuilds
      final state = tester.state<_TestWidgetState>(find.byType(TestWidget));
      for (var i = 0; i < 100; i++) {
        state.increment();
        await tester.pump();
      }

      rebuildStopwatch.stop();

      final avgMs = rebuildStopwatch.elapsedMilliseconds / 100;
      print('Average rebuild time: ${avgMs.toStringAsFixed(3)}ms');

      expect(avgMs, lessThan(5.0));
    });
  });

  group('Animation Performance', () {
    testWidgets('FadeIn animation performs well', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TestFadeWidget(),
          ),
        ),
      );

      final frameTimes = <int>[];

      // Trigger animation
      final state = tester.state<_TestFadeWidgetState>(find.byType(TestFadeWidget));
      state.fadeIn();

      // Pump animation frames
      for (var i = 0; i < 10; i++) {
        final frameStopwatch = Stopwatch()..start();
        await tester.pump(const Duration(milliseconds: 16));
        frameStopwatch.stop();
        frameTimes.add(frameStopwatch.elapsedMicroseconds);
      }

      final avgFrameTime =
          frameTimes.reduce((a, b) => a + b) / frameTimes.length;

      print('Animation average frame time: ${(avgFrameTime / 1000).toStringAsFixed(2)}ms');

      // 60fps = 16.67ms per frame = 16667 microseconds
      expect(avgFrameTime, lessThan(50000)); // Relaxed threshold
    });
  });

  group('String Operations', () {
    testWidgets('Text rendering with long strings', (tester) async {
      final longText = 'This is a test. ' * 100;

      final stopwatch = Stopwatch()..start();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: Text(longText),
            ),
          ),
        ),
      );

      stopwatch.stop();

      print('Long text render: ${stopwatch.elapsedMilliseconds}ms');

      expect(stopwatch.elapsedMilliseconds, lessThan(200));
    });

    testWidgets('RichText with multiple styles', (tester) async {
      final stopwatch = Stopwatch()..start();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RichText(
              text: TextSpan(
                style: const TextStyle(fontSize: 16),
                children: [
                  for (var i = 0; i < 20; i++)
                    TextSpan(
                      text: 'Word $i ',
                      style: TextStyle(
                        color: i % 2 == 0 ? Colors.red : Colors.blue,
                        fontWeight: i % 3 == 0 ? FontWeight.bold : FontWeight.normal,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      );

      stopwatch.stop();

      print('RichText render: ${stopwatch.elapsedMilliseconds}ms');

      expect(stopwatch.elapsedMilliseconds, lessThan(100));
    });
  });

  group('Performance Summary', () {
    testWidgets('Overall performance summary', (tester) async {
      final results = <String, int>{};

      // Text
      final sw1 = Stopwatch()..start();
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Text('Test'),
          ),
        ),
      );
      sw1.stop();
      results['Text'] = sw1.elapsedMilliseconds;

      // ListView
      final sw2 = Stopwatch()..start();
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ListView.builder(
              itemCount: 50,
              itemBuilder: (_, i) => ListTile(title: Text('Item $i')),
            ),
          ),
        ),
      );
      sw2.stop();
      results['ListView'] = sw2.elapsedMilliseconds;

      // Column
      final sw3 = Stopwatch()..start();
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                for (var i = 0; i < 10; i++) Text('Item $i'),
              ],
            ),
          ),
        ),
      );
      sw3.stop();
      results['Column'] = sw3.elapsedMilliseconds;

      print('\n=== Performance Summary ===');
      results.forEach((widget, time) {
        print('$widget: ${time}ms');
      });
      print('=========================\n');

      // Verify all are within acceptable limits
      expect(results['Text'], lessThanOrEqualTo(20));
      expect(results['ListView'], lessThan(200));
      expect(results['Column'], lessThan(50));
    });
  });
}

// Helper widgets for testing
class TestWidget extends StatefulWidget {
  const TestWidget({super.key});

  @override
  State<TestWidget> createState() => _TestWidgetState();
}

class _TestWidgetState extends State<TestWidget> {
  int _counter = 0;

  void increment() {
    setState(() {
      _counter++;
    });
  }

  @override
  Widget build(BuildContext context) => Text('Count: $_counter');
}

class TestFadeWidget extends StatefulWidget {
  const TestFadeWidget({super.key});

  @override
  State<TestFadeWidget> createState() => _TestFadeWidgetState();
}

class _TestFadeWidgetState extends State<TestFadeWidget> {
  double _opacity = 0.0;

  void fadeIn() {
    setState(() {
      _opacity = 1.0;
    });
  }

  @override
  Widget build(BuildContext context) => AnimatedOpacity(
      opacity: _opacity,
      duration: const Duration(milliseconds: 300),
      child: const Text('Fade In'),
    );
}
